"""
Conteneur 3 : Recommandation
Système de recommandation et tests avec traitement distribué PySpark.

Optimisations scalabilité (Priorité 1 & 2) :
- Spark MLlib RandomForestClassifier (entraînement distribué) au lieu de sklearn.
- Génération des paires (user, image) via `flatMap` Spark (zéro RAM driver).
- Broadcast variables pour labels/profils/favoris/probas.
- `repartition` explicite pour un parallélisme maîtrisé.
- SparkConf paramétrable via variables d'environnement.
"""

import os
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Tuple

from pyspark import SparkContext
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, when, udf
from pyspark.sql.types import DoubleType
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
# la plus large (ici `primary_tag` peut atteindre ~100+ valeurs sur 120 images,
# et beaucoup plus à grande échelle). 256 est un compromis sûr.
RF_MAX_BINS = int(os.getenv("RF_MAX_BINS", "256"))


def validate_environment() -> None:
    """
    Valide la présence des fichiers produits par les conteneurs précédents.
    """
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


def build_features_dataframe(spark: SparkSession, labels: Dict, metadata: Dict):
    """
    Construit le DataFrame Spark des caractéristiques pour MLlib.

    Étapes :
    1. Création de lignes [filename, features brutes (numériques + catégorielles)].
    2. Pipeline d'encodage : StringIndexer pour les colonnes catégorielles
       (équivalent distribué de sklearn LabelEncoder), puis VectorAssembler
       pour produire la colonne `features` consommée par RandomForestClassifier.
    3. `cache()` : on réutilise ce DataFrame pour chaque utilisateur.

    Args:
        spark: SparkSession active
        labels: dict {filename: label_data}
        metadata: dict {filename: meta_data}

    Returns:
        DataFrame Spark avec colonnes ['filename', 'features']
    """
    rows = []
    for filename in labels.keys():
        l = labels[filename]
        m = metadata[filename]
        rows.append({
            'filename': filename,
            'orientation': l['orientation'],
            'size_category': l['size_category'],
            'width': float(m['width']),
            'height': float(m['height']),
            'file_size_kb': float(m['file_size_kb']),
            'aspect_ratio': float(m['width']) / float(m['height']),
            'color_1': l['color_names'][0] if l['color_names'] else 'inconnu',
            'color_2': l['color_names'][1] if len(l['color_names']) > 1 else 'inconnu',
            'color_3': l['color_names'][2] if len(l['color_names']) > 2 else 'inconnu',
            'n_unique_colors': float(len(set(l['color_names']))),
            'n_tags': float(len(l['tags'])),
            'primary_tag': l['tags'][0] if l['tags'] else 'inconnu',
        })

    df = spark.createDataFrame(rows)

    # Repartitionnement pour exploiter le parallélisme
    n_part = compute_partitions(len(rows), items_per_partition=20)
    df = df.repartition(n_part)

    cat_cols = ['orientation', 'size_category', 'color_1', 'color_2', 'color_3', 'primary_tag']
    num_cols = ['width', 'height', 'file_size_kb', 'aspect_ratio', 'n_unique_colors', 'n_tags']

    indexers = [
        StringIndexer(inputCol=c, outputCol=f"{c}_idx", handleInvalid="keep")
        for c in cat_cols
    ]
    assembler = VectorAssembler(
        inputCols=num_cols + [f"{c}_idx" for c in cat_cols],
        outputCol="features",
    )

    pipeline = Pipeline(stages=indexers + [assembler])
    df_features = (
        pipeline.fit(df)
        .transform(df)
        .select("filename", "features")
        .cache()
    )

    # Force la matérialisation du cache
    df_features.count()

    return df_features


def train_user_model_mllib(user_id: str, favorites_set: set, df_features) -> Tuple:
    """
    Entraîne un Random Forest distribué via Spark MLlib pour un utilisateur.

    Le `fit()` est distribué sur les workers Spark (vs sklearn qui était mono-thread).
    Pour 100k+ images par utilisateur, c'est le bon compromis.

    Note pédagogique : à 1M+ utilisateurs, l'idéal serait UN seul modèle global
    avec features (user × image) en input — ici on garde un modèle par user
    pour rester dans l'esprit de la consigne (filtrage basé sur le contenu).

    Args:
        user_id: identifiant utilisateur
        favorites_set: ensemble des filenames favoris
        df_features: DataFrame Spark mis en cache

    Returns:
        (modèle_entraîné, accuracy_test)
    """
    favorites_list = list(favorites_set)

    # Ajouter colonne `label` (1 si favori, 0 sinon) — `isin` accepte une liste
    df_labeled = df_features.withColumn(
        "label",
        when(col("filename").isin(favorites_list), 1).otherwise(0),
    )

    # Split train/test stratifié approximatif
    train_df, test_df = df_labeled.randomSplit([0.7, 0.3], seed=42)
    train_df = train_df.cache()

    rf = SparkRF(
        featuresCol="features",
        labelCol="label",
        numTrees=RF_NUM_TREES,
        maxDepth=RF_MAX_DEPTH,
        maxBins=RF_MAX_BINS,
        seed=42,
    )
    model = rf.fit(train_df)

    # Évaluation
    predictions = model.transform(test_df)
    evaluator = MulticlassClassificationEvaluator(
        labelCol="label",
        predictionCol="prediction",
        metricName="accuracy",
    )
    accuracy = evaluator.evaluate(predictions)

    train_df.unpersist()

    return model, accuracy


def extract_proba_class_1(probability_vector) -> float:
    """UDF Spark : extrait la probabilité de la classe 1 (favori) du vecteur MLlib."""
    if probability_vector is None:
        return 0.0
    try:
        return float(probability_vector[1])
    except (IndexError, TypeError):
        return 0.0


def collect_user_probas(model, df_features) -> Dict[str, float]:
    """
    Applique le modèle sur TOUTES les images et renvoie {filename: proba_classe_1}.
    Le `transform` est distribué sur les workers Spark.
    """
    extract_udf = udf(extract_proba_class_1, DoubleType())

    predictions = (
        model.transform(df_features)
        .select("filename", extract_udf(col("probability")).alias("proba"))
    )

    return {row["filename"]: float(row["proba"]) for row in predictions.collect()}


def compute_recommendation_score(item: tuple, labels: Dict, profiles: Dict,
                                 favorites_by_user: Dict) -> tuple:
    """
    Calcule le score de recommandation pour une paire (utilisateur, image).
    Fonction exécutée en parallèle par les workers Spark.
    Les données volumineuses (labels, profils, favoris) sont passées via
    variables broadcast pour éviter la duplication sur chaque worker.

    Args:
        item: tuple (user_id, filename, proba)
        labels: dict labels (broadcast)
        profiles: dict profils utilisateurs (broadcast)
        favorites_by_user: dict user_id -> set(favoris) (broadcast)

    Returns:
        tuple (user_id, filename, score, reason) ou None si image déjà en favoris
    """
    user_id, filename, proba = item

    # Exclure les favoris
    if filename in favorites_by_user[user_id]:
        return None

    # Générer une raison
    img_labels = labels[filename]
    user_profile = profiles[user_id]
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

    return (user_id, filename, float(proba), reason)


def recommend_all_users_spark(users: Dict, df_features, labels: Dict,
                              spark: SparkSession,
                              n_recommendations: int = 5) -> Tuple[Dict, Dict]:
    """
    Génère les recommandations pour TOUS les utilisateurs avec PySpark + MLlib.

    Pipeline scalable :
    1. Pour chaque user : entraînement MLlib RF distribué + collecte probas.
    2. Broadcast des structures partagées (labels, profils, favoris, probas).
    3. flatMap Spark : génération des paires (user, image, proba) côté workers
       (PRIORITÉ 1 - point 2 : la RAM driver ne stocke jamais N_users × N_images).
    4. repartition explicite pour bon parallélisme du scoring.
    5. Scoring distribué + groupByKey + top N par utilisateur.

    Args:
        users: dict utilisateurs
        df_features: DataFrame Spark des features (cache déjà actif)
        labels: dict labels
        spark: SparkSession active
        n_recommendations: nombre de recommandations par utilisateur

    Returns:
        (recommendations_by_user, accuracies)
    """
    sc = spark.sparkContext

    # === Étape 1 : Entraînement MLlib + probas par utilisateur ===
    logger.info("🧠 Entraînement des modèles MLlib (RandomForest distribué)...")
    probas_by_user: Dict[str, Dict[str, float]] = {}
    accuracies: Dict[str, float] = {}
    favorites_by_user: Dict[str, set] = {}

    # Liste ordonnée des filenames (collectée 1 fois)
    filenames = [r["filename"] for r in df_features.select("filename").collect()]

    for user_id in users.keys():
        favorites_set = set(users[user_id]['favorite_images'])
        favorites_by_user[user_id] = favorites_set

        model, accuracy = train_user_model_mllib(user_id, favorites_set, df_features)
        accuracies[user_id] = accuracy

        probas_by_user[user_id] = collect_user_probas(model, df_features)

        logger.info(f"   ✅ {user_id} : précision MLlib {accuracy:.2%}")

    # === Étape 2 : Broadcast des structures partagées ===
    logger.info("📡 Broadcast des données partagées sur les workers Spark...")
    labels_bc = sc.broadcast(labels)
    profiles_bc = sc.broadcast(dict(users))
    favorites_bc = sc.broadcast(favorites_by_user)
    filenames_bc = sc.broadcast(filenames)
    probas_bc = sc.broadcast(probas_by_user)

    # === Étape 3 : Génération des paires via flatMap (PRIORITÉ 1 - point 2) ===
    # Au lieu de construire `all_items` en Python (RAM driver = N_users × N_images),
    # on parallélise sur les user_ids et chaque worker génère ses propres paires.
    logger.info("🚀 Génération distribuée des paires (user, image) via flatMap...")
    n_part_users = compute_partitions(len(users), items_per_partition=1)
    users_rdd = sc.parallelize(list(users.keys()), numSlices=n_part_users)

    items_rdd = users_rdd.flatMap(
        lambda uid: [
            (uid, fn, probas_bc.value[uid].get(fn, 0.0))
            for fn in filenames_bc.value
        ]
    )

    # === Étape 4 : Repartition pour scoring équilibré ===
    n_pairs_estimate = len(users) * len(filenames)
    n_part_scoring = compute_partitions(n_pairs_estimate, items_per_partition=1000)
    items_rdd = items_rdd.repartition(n_part_scoring)
    logger.info(
        f"⚖️ Scoring de ~{n_pairs_estimate} paires sur {n_part_scoring} partitions Spark"
    )

    # === Étape 5 : Scoring distribué ===
    scored_rdd = items_rdd.map(
        lambda item: compute_recommendation_score(
            item, labels_bc.value, profiles_bc.value, favorites_bc.value
        )
    )

    # Filter : retirer les favoris (None)
    valid_rdd = scored_rdd.filter(lambda x: x is not None)

    # Map vers PairRDD (user_id, (filename, score, reason)) puis groupByKey
    pair_rdd = valid_rdd.map(lambda x: (x[0], (x[1], x[2], x[3])))
    grouped_rdd = pair_rdd.groupByKey()

    # Pour chaque utilisateur : trier par score décroissant et prendre les N meilleures
    top_n_rdd = grouped_rdd.mapValues(
        lambda recs: sorted(recs, key=lambda r: r[1], reverse=True)[:n_recommendations]
    )

    # collectAsMap : récupérer en dict {user_id: [(filename, score, reason), ...]}
    recommendations_by_user = top_n_rdd.collectAsMap()

    # Libérer les broadcasts
    labels_bc.unpersist()
    profiles_bc.unpersist()
    favorites_bc.unpersist()
    filenames_bc.unpersist()
    probas_bc.unpersist()

    return recommendations_by_user, accuracies


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


def main():
    """Point d'entrée principal avec traitement PySpark + MLlib distribué."""
    logger.info("🚀 Début des recommandations avec PySpark + MLlib...")

    # === SparkSession (nécessaire pour DataFrames + MLlib) ===
    spark = (
        SparkSession.builder
        .appName("ImageRecommendation")
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
        f"depth={RF_MAX_DEPTH}, maxBins={RF_MAX_BINS}"
    )

    try:
        # Charger les données
        logger.info("📥 Chargement des données...")

        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        with open(LABELS_FILE, "r", encoding="utf-8") as f:
            labels = json.load(f)

        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)

        logger.info(f"✅ {len(metadata)} images chargées")
        logger.info(f"✅ {len(users)} utilisateurs chargés")

        # === Tâche 5 : Système de Recommandation ===
        logger.info("🤖 TÂCHE 5 : SYSTÈME DE RECOMMANDATION (Spark MLlib)")

        # Préparer le DataFrame Spark des features (encoding distribué)
        logger.info("🔧 Préparation des caractéristiques (Pipeline MLlib)...")
        df_features = build_features_dataframe(spark, labels, metadata)
        logger.info(f"✅ DataFrame Spark prêt avec {df_features.count()} images en cache")

        # Générer recommandations EN PARALLÈLE via Spark + MLlib
        logger.info("=" * 80)
        logger.info("🎯 GÉNÉRATION DES RECOMMANDATIONS (SPARK MLlib + flatMap distribué)")
        logger.info("=" * 80)

        recommendations_by_user, accuracies = recommend_all_users_spark(
            users=users,
            df_features=df_features,
            labels=labels,
            spark=spark,
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
            logger.info(f"   Précision MLlib : {accuracies.get(user_id, 0):.2%}")

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

        # Libérer le cache du DataFrame
        df_features.unpersist()

        logger.info("✅ Traitement complet terminé !")

    finally:
        spark.stop()
        logger.info("🛑 SparkSession arrêtée")


if __name__ == "__main__":
    main()
