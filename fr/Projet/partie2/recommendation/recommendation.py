"""
Conteneur 4 : Recommandation
Système de recommandation et tests avec traitement distribué PySpark.

Architecture (Option A — modèle global, scalable à 1M+ utilisateurs) :
- UN SEUL Random Forest global sur (user × image) → favori
  (vs N modèles par user dans la version précédente).
- Cross-join Spark distribué pour générer les paires (user, image).
- Negative sampling pour équilibrer les classes (favoris rares).
- 1 seul model.fit() puis 1 seul model.transform() global.
- Broadcast variables pour favoris/labels/profils.
- SparkConf paramétrable via variables d'environnement.

Avantages scalabilité 1M+ utilisateurs :
- Temps d'entraînement : O(N_interactions) au lieu de O(N_users × N_images).
- 1 seul modèle en mémoire (vs N_users modèles).
- Apprend les patterns inter-utilisateurs ("qui aime bleu+nature aime aussi...").
"""

import os
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Tuple

from pyspark import SparkContext
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql.functions import col, udf, avg
from pyspark.sql.types import DoubleType, IntegerType, BooleanType
from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, VectorAssembler
from pyspark.ml.classification import RandomForestClassifier as SparkRF
from pyspark.ml.evaluation import MulticlassClassificationEvaluator


# === Configuration du logger ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [recommendation] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# === Configuration des chemins ===
INPUT_DIR = Path(os.getenv("INPUT_DIR", "/shared_data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/shared_data"))
METADATA_FILE = INPUT_DIR / "images_metadata.json"
LABELS_FILE = INPUT_DIR / "images_labels.json"
USERS_FILE = INPUT_DIR / "users.json"
RECOMMENDATIONS_FILE = OUTPUT_DIR / "recommendations.json"

# === Configuration Spark (paramétrable) ===
SPARK_PARALLELISM = int(os.getenv("SPARK_PARALLELISM", "200"))
SPARK_DRIVER_MEMORY = os.getenv("SPARK_DRIVER_MEMORY", "2g")
SPARK_EXECUTOR_MEMORY = os.getenv("SPARK_EXECUTOR_MEMORY", "2g")

# Hyperparamètres MLlib RandomForest
RF_NUM_TREES = int(os.getenv("RF_NUM_TREES", "100"))
RF_MAX_DEPTH = int(os.getenv("RF_MAX_DEPTH", "10"))
# maxBins doit être >= au nombre de valeurs uniques de la feature catégorielle
# la plus large. Avec ~100 tags primaires sur 120 images (et bien plus à grande
# échelle), 256 est un compromis sûr.
RF_MAX_BINS = int(os.getenv("RF_MAX_BINS", "256"))

# Negative sampling : ratio négatifs/positifs visé pour l'entraînement.
# Les favoris sont rares (~10 % des paires), il faut équilibrer pour éviter
# qu'un modèle qui prédit toujours "non favori" obtienne 90 % d'accuracy.
NEG_POS_RATIO = int(os.getenv("NEG_POS_RATIO", "3"))


def validate_environment() -> None:
    """Valide la présence des fichiers produits par les conteneurs précédents."""
    required_files = {
        "métadonnées": METADATA_FILE,
        "labels": LABELS_FILE,
        "utilisateurs": USERS_FILE,
    }
    for label, path in required_files.items():
        if not path.exists():
            raise RuntimeError(
                f"❌ Fichier {label} manquant : {path}. "
                "Le conteneur 'analysis' a-t-il bien terminé avec succès ?"
            )
    logger.info("✅ Variables d'environnement validées")


# Validation au démarrage
validate_environment()

logger.info(f"📁 Dossier données : {INPUT_DIR}")
logger.info(f"📁 Fichier recommandations : {RECOMMENDATIONS_FILE}")


def compute_partitions(n_items: int, items_per_partition: int = 10) -> int:
    """Nombre de partitions équilibré (jamais < 4, jamais > SPARK_PARALLELISM)."""
    return max(4, min(SPARK_PARALLELISM, max(1, n_items // items_per_partition)))


# ==============================================================================
# Construction des DataFrames de features
# ==============================================================================

# Colonnes du modèle (préfixées img_ et usr_ pour éviter les collisions au crossJoin)
CAT_COLS_USER = [
    'usr_color_1', 'usr_color_2', 'usr_color_3',
    'usr_orientation', 'usr_size',
    'usr_tag_1', 'usr_tag_2',
]
CAT_COLS_IMAGE = [
    'img_orientation', 'img_size_category',
    'img_color_1', 'img_color_2', 'img_color_3',
    'img_primary_tag',
]
NUM_COLS_IMAGE = [
    'img_width', 'img_height', 'img_file_size_kb',
    'img_aspect_ratio', 'img_n_unique_colors', 'img_n_tags',
]


def build_image_features_df(spark: SparkSession, labels: Dict, metadata: Dict) -> DataFrame:
    """DataFrame des features image (1 ligne par image, sans label/user)."""
    rows = []
    for filename in labels.keys():
        l = labels[filename]
        m = metadata[filename]
        rows.append({
            'filename': filename,
            'img_orientation': l['orientation'],
            'img_size_category': l['size_category'],
            'img_width': float(m['width']),
            'img_height': float(m['height']),
            'img_file_size_kb': float(m['file_size_kb']),
            'img_aspect_ratio': float(m['width']) / max(float(m['height']), 1.0),
            'img_color_1': l['color_names'][0] if l['color_names'] else 'inconnu',
            'img_color_2': l['color_names'][1] if len(l['color_names']) > 1 else 'inconnu',
            'img_color_3': l['color_names'][2] if len(l['color_names']) > 2 else 'inconnu',
            'img_n_unique_colors': float(len(set(l['color_names']))),
            'img_n_tags': float(len(l['tags'])),
            'img_primary_tag': l['tags'][0] if l['tags'] else 'inconnu',
        })
    return spark.createDataFrame(rows)


def build_user_features_df(spark: SparkSession, users: Dict) -> DataFrame:
    """DataFrame des features utilisateur (1 ligne par user)."""
    rows = []
    for user_id, profile in users.items():
        rows.append({
            'user_id': user_id,
            'usr_color_1': profile['favorite_colors'][0] if profile['favorite_colors'] else 'inconnu',
            'usr_color_2': profile['favorite_colors'][1] if len(profile['favorite_colors']) > 1 else 'inconnu',
            'usr_color_3': profile['favorite_colors'][2] if len(profile['favorite_colors']) > 2 else 'inconnu',
            'usr_orientation': profile['favorite_orientation'],
            'usr_size': profile['favorite_size'],
            'usr_tag_1': profile['favorite_tags'][0] if profile['favorite_tags'] else 'inconnu',
            'usr_tag_2': profile['favorite_tags'][1] if len(profile['favorite_tags']) > 1 else 'inconnu',
        })
    return spark.createDataFrame(rows)


def build_training_dataset(spark: SparkSession, users_df: DataFrame, images_df: DataFrame,
                           users: Dict, neg_pos_ratio: int = 3) -> DataFrame:
    """
    Construit le dataset d'entraînement global avec negative sampling distribué.

    Pipeline :
    1. Cross-join Spark : génération distribuée de toutes les paires (user, image)
       — équivalent DataFrame du flatMap RDD, mais optimisé par Catalyst.
    2. Labellisation distribuée via UDF : 1 si l'image est dans les favoris du
       user, 0 sinon (favoris diffusés en broadcast pour éviter la duplication).
    3. Negative sampling : downsample des négatifs pour équilibrer les classes
       (sinon le modèle "tout-zéro" obtient ~90 % d'accuracy mais 0 % de rappel).

    Returns:
        DataFrame avec colonnes user_features + image_features + label
    """
    sc = spark.sparkContext

    # 1. Cross-join distribué (Catalyst optimise selon la taille des deux côtés)
    all_pairs = users_df.crossJoin(images_df)

    # 2. Labellisation via UDF + broadcast des favoris
    favorites_by_user = {uid: list(u['favorite_images']) for uid, u in users.items()}
    favorites_bc = sc.broadcast(favorites_by_user)

    label_udf = udf(
        lambda uid, fn: 1 if fn in favorites_bc.value.get(uid, []) else 0,
        IntegerType(),
    )
    labeled = all_pairs.withColumn('label', label_udf(col('user_id'), col('filename')))

    # 3. Negative sampling (downsample des négatifs)
    pos_df = labeled.filter(col('label') == 1).cache()
    neg_df = labeled.filter(col('label') == 0)

    n_pos = pos_df.count()
    n_neg = neg_df.count()

    if n_pos == 0:
        raise RuntimeError(
            "❌ Aucun favori trouvé dans les utilisateurs : "
            "impossible d'entraîner le modèle global."
        )

    sample_ratio = min(1.0, (n_pos * neg_pos_ratio) / max(n_neg, 1))
    neg_sampled = neg_df.sample(withReplacement=False, fraction=sample_ratio, seed=42)

    training_df = pos_df.union(neg_sampled)
    n_total = training_df.count()

    logger.info(
        f"📊 Training : {n_pos} positifs + ~{int(sample_ratio * n_neg)} négatifs "
        f"≈ {n_total} lignes (ratio neg/pos visé = {neg_pos_ratio})"
    )

    pos_df.unpersist()
    favorites_bc.unpersist()

    return training_df


# ==============================================================================
# Modèle global MLlib
# ==============================================================================

def train_global_model_mllib(training_df: DataFrame) -> Tuple:
    """
    Entraîne UN SEUL Random Forest global sur les paires (user × image) → favori.

    Pipeline MLlib :
        StringIndexer (×N pour chaque colonne catégorielle)
            → VectorAssembler (concat features numériques + indexées)
            → RandomForestClassifier

    Avantages vs un modèle par user :
    - 1 seul fit() au lieu de N → scaling linéaire en lignes, pas en utilisateurs
    - Apprend les patterns inter-utilisateurs (collaborative-flavored)
    - Mémoire : 1 modèle au lieu de N modèles

    Returns:
        (PipelineModel entraîné, accuracy globale, dict accuracy par user)
    """
    cat_cols = CAT_COLS_USER + CAT_COLS_IMAGE
    num_cols = NUM_COLS_IMAGE

    indexers = [
        StringIndexer(inputCol=c, outputCol=f"{c}_idx", handleInvalid="keep")
        for c in cat_cols
    ]
    assembler = VectorAssembler(
        inputCols=num_cols + [f"{c}_idx" for c in cat_cols],
        outputCol="features",
    )
    rf = SparkRF(
        featuresCol="features", labelCol="label",
        numTrees=RF_NUM_TREES, maxDepth=RF_MAX_DEPTH, maxBins=RF_MAX_BINS,
        seed=42,
    )
    pipeline = Pipeline(stages=indexers + [assembler, rf])

    train_df, test_df = training_df.randomSplit([0.7, 0.3], seed=42)
    train_df = train_df.cache()

    logger.info(
        f"🧠 Entraînement modèle GLOBAL (1 seul fit, "
        f"numTrees={RF_NUM_TREES}, maxDepth={RF_MAX_DEPTH})..."
    )
    model = pipeline.fit(train_df)

    predictions = model.transform(test_df).cache()

    # Accuracy globale
    evaluator = MulticlassClassificationEvaluator(
        labelCol="label", predictionCol="prediction", metricName="accuracy",
    )
    global_accuracy = evaluator.evaluate(predictions)

    # Accuracy par user (groupBy distribué)
    per_user_acc_df = (
        predictions
        .withColumn('correct', (col('label') == col('prediction')).cast('double'))
        .groupBy('user_id')
        .agg(avg('correct').alias('accuracy'))
    )
    per_user_accuracy = {
        row['user_id']: float(row['accuracy'])
        for row in per_user_acc_df.collect()
    }

    train_df.unpersist()
    predictions.unpersist()

    return model, global_accuracy, per_user_accuracy


# ==============================================================================
# Inférence : 1 seul transform global
# ==============================================================================

def extract_proba_class_1(probability_vector) -> float:
    """UDF Spark : extrait la probabilité de la classe 1 (favori) du vecteur MLlib."""
    if probability_vector is None:
        return 0.0
    try:
        return float(probability_vector[1])
    except (IndexError, TypeError):
        return 0.0


def recommend_all_users_global(spark: SparkSession, model, users_df: DataFrame,
                               images_df: DataFrame, users: Dict, labels: Dict,
                               n_recommendations: int = 5) -> Dict:
    """
    Inférence distribuée : 1 SEUL transform global pour TOUS les utilisateurs.

    Pipeline :
    1. Cross-join (user × image) → toutes les paires candidates.
    2. Filter distribué : exclusion des favoris (broadcast).
    3. model.transform() distribué → probabilité par paire.
    4. Construction des raisons sur les workers (broadcast labels + profils).
    5. groupByKey + mapValues → top-N par utilisateur.
    """
    sc = spark.sparkContext

    # === 1. Cross-join distribué ===
    all_pairs = users_df.crossJoin(images_df)

    # === 2. Exclusion des favoris (broadcast) ===
    favorites_by_user = {uid: list(u['favorite_images']) for uid, u in users.items()}
    favorites_bc = sc.broadcast(favorites_by_user)

    not_fav_udf = udf(
        lambda uid, fn: fn not in favorites_bc.value.get(uid, []),
        BooleanType(),
    )
    candidates_df = all_pairs.filter(not_fav_udf(col('user_id'), col('filename')))

    n_candidates = candidates_df.count()
    n_part = compute_partitions(n_candidates, items_per_partition=500)
    candidates_df = candidates_df.repartition(n_part)
    logger.info(f"⚖️ {n_candidates} paires candidates sur {n_part} partitions Spark")

    # === 3. transform() global distribué (UN SEUL appel pour TOUS les users) ===
    logger.info("🚀 Inférence : 1 seul model.transform() sur toutes les paires...")
    predictions = model.transform(candidates_df)

    extract_udf = udf(extract_proba_class_1, DoubleType())
    scored_df = predictions.select(
        col('user_id'),
        col('filename'),
        extract_udf(col('probability')).alias('score'),
    )

    # === 4. Construction des raisons sur les workers (broadcast) ===
    labels_bc = sc.broadcast(labels)
    profiles_bc = sc.broadcast(dict(users))

    def build_recommendation(row):
        user_id = row['user_id']
        filename = row['filename']
        score = float(row['score'])
        img_labels = labels_bc.value[filename]
        user_profile = profiles_bc.value[user_id]
        reasons = []

        matching_colors = set(img_labels['color_names']) & set(user_profile['favorite_colors'])
        if matching_colors:
            reasons.append(f"couleurs {', '.join(matching_colors)}")

        if img_labels['orientation'] == user_profile['favorite_orientation']:
            reasons.append(f"orientation {img_labels['orientation']}")

        matching_tags = set(img_labels['tags']) & set(user_profile['favorite_tags'])
        if matching_tags:
            reasons.append(f"tags {', '.join(list(matching_tags)[:2])}")

        if not reasons:
            reasons.append("profil général")

        reason = f"Correspond à vos préférences : {' + '.join(reasons)}"
        return (user_id, (filename, score, reason))

    # === 5. groupByKey + mapValues → top-N par utilisateur ===
    pair_rdd = scored_df.rdd.map(build_recommendation)
    top_n_rdd = (
        pair_rdd
        .groupByKey()
        .mapValues(
            lambda recs: sorted(recs, key=lambda r: r[1], reverse=True)[:n_recommendations]
        )
    )
    recommendations_by_user = top_n_rdd.collectAsMap()

    favorites_bc.unpersist()
    labels_bc.unpersist()
    profiles_bc.unpersist()

    # Convertir les valeurs en list (collectAsMap renvoie des objets ResultIterable)
    return {uid: list(recs) for uid, recs in recommendations_by_user.items()}


# ==============================================================================
# Tests (Tâche 6)
# ==============================================================================

def _is_metadata_invalid(item: tuple) -> bool:
    """Prédicat exécuté en parallèle par les workers Spark (validation distribuée)."""
    _, meta = item
    return (
        meta.get('width', 0) <= 0
        or meta.get('height', 0) <= 0
        or meta.get('file_size_kb', 0) <= 0
        or not meta.get('filename')
        or not meta.get('format')
    )


def _is_label_invalid(item: tuple) -> bool:
    """Prédicat exécuté en parallèle par les workers Spark (validation distribuée)."""
    _, label = item
    return (
        not label.get('predominant_colors')
        or not label.get('color_names')
        or not label.get('orientation')
        or not label.get('size_category')
    )


def test_data_integrity(metadata: Dict, labels: Dict, sc: SparkContext) -> bool:
    """
    Teste l'intégrité des données via validation distribuée PySpark
    sur TOUTES les images.
    """
    logger.info("📝 Test 1 : Intégrité des données (validation distribuée Spark)")

    try:
        assert len(metadata) >= 100, f"❌ Pas assez d'images : {len(metadata)} < 100"
        logger.info(f"   ✅ Nombre d'images suffisant : {len(metadata)} images")

        assert len(metadata) == len(labels), (
            f"❌ Incohérence : {len(metadata)} métadonnées vs {len(labels)} labels"
        )
        logger.info(f"   ✅ Correspondance métadonnées/labels : {len(metadata)} entrées chacun")

        n_part = compute_partitions(len(metadata), items_per_partition=50)

        metadata_rdd = sc.parallelize(list(metadata.items()), numSlices=n_part)
        invalid_meta_count = metadata_rdd.filter(_is_metadata_invalid).count()
        assert invalid_meta_count == 0, (
            f"❌ {invalid_meta_count} métadonnée(s) invalide(s) détectée(s) par Spark"
        )
        logger.info(f"   ✅ {len(metadata)} métadonnées validées par Spark (0 invalide)")

        labels_rdd = sc.parallelize(list(labels.items()), numSlices=n_part)
        invalid_labels_count = labels_rdd.filter(_is_label_invalid).count()
        assert invalid_labels_count == 0, (
            f"❌ {invalid_labels_count} label(s) invalide(s) détecté(s) par Spark"
        )
        logger.info(f"   ✅ {len(labels)} labels validés par Spark (0 invalide)")

        meta_keys_rdd = sc.parallelize(list(metadata.keys()), numSlices=n_part)
        labels_keys = set(labels.keys())
        labels_keys_bc = sc.broadcast(labels_keys)
        orphan_count = meta_keys_rdd.filter(
            lambda k: k not in labels_keys_bc.value
        ).count()
        labels_keys_bc.unpersist()
        assert orphan_count == 0, f"❌ {orphan_count} image(s) sans label correspondant"
        logger.info(f"   ✅ Toutes les images ont un label correspondant (vérifié par Spark)")

        logger.info("✅ Test 1 : RÉUSSI")
        return True

    except AssertionError as e:
        logger.error(f"❌ Test 1 : ÉCHEC - {e}")
        return False


def test_recommendation_quality(recommendations: List[Tuple], user_id: str,
                                users: Dict, labels: Dict) -> bool:
    """Teste la qualité des recommandations."""
    logger.info("📝 Test 2 : Qualité des recommandations")

    try:
        assert len(recommendations) == 5, f"❌ Nombre incorrect : {len(recommendations)}"
        logger.info("   ✅ Retourne le bon nombre de recommandations : 5")

        user_favorites = set(users[user_id]['favorite_images'])
        recommended_images = [rec[0] for rec in recommendations]

        overlap = set(recommended_images) & user_favorites
        assert len(overlap) == 0, f"❌ Favoris recommandés : {overlap}"
        logger.info("   ✅ Aucune image déjà favorite n'est recommandée")

        scores = [rec[1] for rec in recommendations]
        assert scores == sorted(scores, reverse=True), "❌ Scores non triés"
        logger.info("   ✅ Recommandations triées par score")

        user_profile = users[user_id]
        relevance_count = 0

        for filename, score, reason in recommendations:
            img_labels = labels[filename]

            color_match = bool(set(img_labels['color_names']) & set(user_profile['favorite_colors']))
            orientation_match = img_labels['orientation'] == user_profile['favorite_orientation']
            tag_match = bool(set(img_labels['tags']) & set(user_profile['favorite_tags']))

            if color_match or orientation_match or tag_match:
                relevance_count += 1

        relevance_ratio = relevance_count / len(recommendations)
        logger.info(f"   ✅ Pertinence : {relevance_ratio:.1%} des recommandations correspondent au profil")

        assert relevance_ratio >= 0.4, f"❌ Recommandations peu pertinentes : {relevance_ratio:.1%}"

        logger.info("✅ Test 2 : RÉUSSI")
        return True

    except AssertionError as e:
        logger.error(f"❌ Test 2 : ÉCHEC - {e}")
        return False


# ==============================================================================
# Main
# ==============================================================================

def main():
    """Point d'entrée principal : modèle global PySpark + MLlib."""
    logger.info("🚀 Début des recommandations avec modèle GLOBAL PySpark + MLlib...")

    # === SparkSession (nécessaire pour DataFrames + MLlib) ===
    spark = (
        SparkSession.builder
        .appName("ImageRecommendationGlobal")
        .master("local[*]")
        .config("spark.driver.memory", SPARK_DRIVER_MEMORY)
        .config("spark.executor.memory", SPARK_EXECUTOR_MEMORY)
        .config("spark.default.parallelism", str(SPARK_PARALLELISM))
        .config("spark.sql.shuffle.partitions", str(SPARK_PARALLELISM))
        .getOrCreate()
    )
    sc = spark.sparkContext
    sc.setLogLevel("WARN")
    logger.info(
        f"⚙️ Spark : driver={SPARK_DRIVER_MEMORY}, executor={SPARK_EXECUTOR_MEMORY}, "
        f"parallelism={SPARK_PARALLELISM} | RF: trees={RF_NUM_TREES}, "
        f"depth={RF_MAX_DEPTH}, maxBins={RF_MAX_BINS}, neg/pos={NEG_POS_RATIO}"
    )

    try:
        # === Chargement des données ===
        logger.info("📥 Chargement des données...")

        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        with open(LABELS_FILE, "r", encoding="utf-8") as f:
            labels = json.load(f)
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)

        logger.info(f"✅ {len(metadata)} images chargées")
        logger.info(f"✅ {len(users)} utilisateurs chargés")

        # === Tâche 5 : Système de Recommandation (modèle global) ===
        logger.info("🤖 TÂCHE 5 : SYSTÈME DE RECOMMANDATION (modèle GLOBAL Spark MLlib)")

        # Construction des features (1 ligne par image, 1 ligne par user)
        logger.info("🔧 Construction des DataFrames de features (image + utilisateur)...")
        images_df = build_image_features_df(spark, labels, metadata).cache()
        users_df = build_user_features_df(spark, users).cache()
        n_images = images_df.count()
        n_users = users_df.count()
        logger.info(
            f"✅ {n_images} images × {n_users} users = {n_images * n_users} paires possibles"
        )

        # Construction du dataset d'entraînement (cross-join + neg sampling distribué)
        logger.info("📦 Construction du dataset d'entraînement (cross-join + neg sampling)...")
        training_df = build_training_dataset(
            spark, users_df, images_df, users, neg_pos_ratio=NEG_POS_RATIO
        )
        training_df = training_df.cache()

        # Entraînement du modèle global (1 seul fit pour TOUS les users)
        model, global_acc, per_user_acc = train_global_model_mllib(training_df)
        logger.info(f"✅ Modèle global entraîné — accuracy globale : {global_acc:.2%}")
        for uid, acc in sorted(per_user_acc.items()):
            logger.info(f"   👤 {uid} : accuracy {acc:.2%}")

        # Inférence (1 seul model.transform global pour TOUS les users)
        logger.info("=" * 80)
        logger.info("🎯 GÉNÉRATION DES RECOMMANDATIONS (modèle GLOBAL + crossJoin distribué)")
        logger.info("=" * 80)

        recommendations_by_user = recommend_all_users_global(
            spark=spark, model=model,
            users_df=users_df, images_df=images_df,
            users=users, labels=labels,
            n_recommendations=5,
        )

        # Convertir en format JSON-serializable et afficher
        all_recommendations = {}
        for user_id in users.keys():
            user_recs = recommendations_by_user.get(user_id, [])
            user_name = users[user_id]['name']

            logger.info(f"👤 Utilisateur : {user_name} ({user_id})")
            logger.info(f"   Profil : Aime {', '.join(users[user_id]['favorite_colors'][:3])}")
            logger.info(f"   Tags favoris : {', '.join(users[user_id]['favorite_tags'][:3])}")
            logger.info(f"   Accuracy MLlib : {per_user_acc.get(user_id, 0):.2%}")

            all_recommendations[user_id] = [
                {"filename": filename, "score": score, "reason": reason}
                for filename, score, reason in user_recs
            ]

            logger.info("   📌 Recommandations :")
            for i, (filename, score, reason) in enumerate(user_recs, 1):
                logger.info(f"      {i}. {filename} (score: {score:.3f})")
                logger.info(f"         → {reason}")

            logger.info("-" * 80)

        # Sauvegarder
        with open(RECOMMENDATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(all_recommendations, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ Recommandations générées pour {len(all_recommendations)} utilisateurs")
        logger.info(f"💾 Recommandations sauvegardées : {RECOMMENDATIONS_FILE}")

        # === Tâche 6 : Tests ===
        logger.info("=" * 80)
        logger.info("🧪 TÂCHE 6 : TESTS")
        logger.info("=" * 80)

        test_results = []

        test_results.append(test_data_integrity(metadata, labels, sc))

        test_user = list(users.keys())[0]
        test_recs = [(r["filename"], r["score"], r["reason"])
                     for r in all_recommendations[test_user]]
        test_results.append(test_recommendation_quality(test_recs, test_user, users, labels))

        # Résumé
        logger.info("=" * 80)
        if all(test_results):
            logger.info("🎉 TOUS LES TESTS RÉUSSIS !")
        else:
            logger.warning("⚠️ CERTAINS TESTS ONT ÉCHOUÉ")
        logger.info("=" * 80)

        # Cleanup
        training_df.unpersist()
        images_df.unpersist()
        users_df.unpersist()

        logger.info("✅ Traitement complet terminé !")

    finally:
        spark.stop()
        logger.info("🛑 SparkSession arrêtée")


if __name__ == "__main__":
    main()
