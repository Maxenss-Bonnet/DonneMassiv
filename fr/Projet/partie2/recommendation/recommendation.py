"""
Conteneur 3 : Recommandation
Système de recommandation et tests avec traitement distribué PySpark.
"""

import os
import json
import logging
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple
from pyspark import SparkContext, SparkConf
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score


# === Configuration du logger ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [recommendation] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Configuration
INPUT_DIR = Path(os.getenv("INPUT_DIR", "/shared_data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/shared_data"))
METADATA_FILE = INPUT_DIR / "images_metadata.json"
LABELS_FILE = INPUT_DIR / "images_labels.json"
USERS_FILE = INPUT_DIR / "users.json"
RECOMMENDATIONS_FILE = OUTPUT_DIR / "recommendations.json"


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


def prepare_features(labels: Dict, metadata: Dict) -> pd.DataFrame:
    """
    Prépare les caractéristiques pour l'apprentissage automatique.
    """
    features = []
    
    for filename in labels.keys():
        label_data = labels[filename]
        meta_data = metadata[filename]
        
        feature_dict = {
            'filename': filename,
            'orientation': label_data['orientation'],
            'size_category': label_data['size_category'],
            'width': meta_data['width'],
            'height': meta_data['height'],
            'file_size_kb': meta_data['file_size_kb'],
            'aspect_ratio': meta_data['width'] / meta_data['height'],
            'color_1': label_data['color_names'][0] if len(label_data['color_names']) > 0 else 'inconnu',
            'color_2': label_data['color_names'][1] if len(label_data['color_names']) > 1 else 'inconnu',
            'color_3': label_data['color_names'][2] if len(label_data['color_names']) > 2 else 'inconnu',
            'n_unique_colors': len(set(label_data['color_names'])),
            'n_tags': len(label_data['tags']),
            'primary_tag': label_data['tags'][0] if label_data['tags'] else 'inconnu'
        }
        
        features.append(feature_dict)
    
    return pd.DataFrame(features)


def encode_features(df: pd.DataFrame) -> Tuple[np.ndarray, Dict, List]:
    """
    Encode les caractéristiques catégorielles en nombres.
    """
    df_encoded = df.copy()
    encoders = {}
    
    categorical_cols = ['orientation', 'size_category', 'color_1', 'color_2', 'color_3', 'primary_tag']
    
    for col in categorical_cols:
        le = LabelEncoder()
        df_encoded[col] = le.fit_transform(df_encoded[col])
        encoders[col] = le
    
    feature_cols = [c for c in df_encoded.columns if c != 'filename']
    X = df_encoded[feature_cols].values
    
    return X, encoders, feature_cols


def train_user_model(user_id: str, users: Dict, df_features: pd.DataFrame, 
                    X_all: np.ndarray) -> Tuple:
    """
    Entraîne un modèle de recommandation pour un utilisateur.
    """
    user = users[user_id]
    favorites = set(user['favorite_images'])
    
    # Créer les labels (1 = favori, 0 = non favori)
    y = df_features['filename'].apply(lambda x: 1 if x in favorites else 0).values
    
    # Split train/test
    X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
        X_all, y, np.arange(len(y)), test_size=0.3, random_state=42, stratify=y
    )
    
    # Entraîner le modèle (Random Forest)
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    model.fit(X_train, y_train)
    
    # Évaluer
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    return model, y, idx_test, accuracy


def compute_recommendation_score(item: tuple, labels: Dict, profiles: Dict,
                                 favorites_by_user: Dict) -> tuple:
    """
    Calcule le score de recommandation pour une paire (utilisateur, image).
    Fonction exécutée en parallèle par les workers Spark.
    Les données volumineuses (labels, profils, favoris) sont passées via
    variables broadcast pour éviter la duplication sur chaque worker.

    Args:
        item: tuple (user_id, filename, proba)
        labels: Dictionnaire des labels (broadcast)
        profiles: Dictionnaire des profils utilisateurs (broadcast)
        favorites_by_user: Dictionnaire user_id -> set(favoris) (broadcast)

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

    # Vérifier les couleurs
    matching_colors = set(img_labels['color_names']) & set(user_profile['favorite_colors'])
    if matching_colors:
        reasons.append(f"couleurs {', '.join(matching_colors)}")

    # Vérifier l'orientation
    if img_labels['orientation'] == user_profile['favorite_orientation']:
        reasons.append(f"orientation {img_labels['orientation']}")

    # Vérifier les tags
    matching_tags = set(img_labels['tags']) & set(user_profile['favorite_tags'])
    if matching_tags:
        reasons.append(f"tags {', '.join(list(matching_tags)[:2])}")

    if not reasons:
        reasons.append("profil général")

    reason = f"Correspond à vos préférences : {' + '.join(reasons)}"

    return (user_id, filename, float(proba), reason)


def recommend_all_users_spark(users: Dict, df_features: pd.DataFrame,
                              X_all: np.ndarray, labels: Dict, sc: SparkContext,
                              n_recommendations: int = 5) -> Dict[str, List[Tuple]]:
    """
    Génère les recommandations pour TOUS les utilisateurs en parallèle via PySpark.

    Stratégie :
    1. Les modèles sklearn sont entraînés séquentiellement (pas distribuable simplement).
    2. Les probabilités de toutes les paires (user, image) sont collectées dans un RDD.
    3. Les données volumineuses (labels, profils, favoris) sont partagées via broadcast.
    4. Le scoring + génération de raisons se fait en parallèle pour TOUTES les paires
       en une seule passe Spark, puis groupe par utilisateur.

    Args:
        users: Dictionnaire des utilisateurs
        df_features: DataFrame des caractéristiques
        X_all: Array encodé de toutes les features
        labels: Dictionnaire des labels
        sc: SparkContext
        n_recommendations: Nombre de recommandations par utilisateur

    Returns:
        Dictionnaire user_id -> liste de tuples (filename, score, raison)
    """
    # === Étape 1 : Entraînement des modèles (séquentiel, sklearn non distribué) ===
    logger.info("🧠 Entraînement des modèles par utilisateur...")
    all_items = []
    favorites_by_user = {}
    accuracies = {}

    filenames = df_features['filename'].tolist()

    for user_id in users.keys():
        model, _, _, accuracy = train_user_model(user_id, users, df_features, X_all)
        accuracies[user_id] = accuracy
        favorites_by_user[user_id] = set(users[user_id]['favorite_images'])

        # Prédire les probabilités pour TOUTES les images
        probas = model.predict_proba(X_all)[:, 1]

        # Construire les items (user_id, filename, proba)
        for filename, proba in zip(filenames, probas):
            all_items.append((user_id, filename, float(proba)))

        logger.info(f"   ✅ {user_id} : précision {accuracy:.2%}")

    # === Étape 2 : Broadcast des structures partagées ===
    # Évite de dupliquer labels/profils/favoris sur chaque worker Spark
    logger.info("📡 Broadcast des données partagées sur les workers Spark...")
    labels_bc = sc.broadcast(labels)
    profiles_bc = sc.broadcast(dict(users))
    favorites_bc = sc.broadcast(favorites_by_user)

    # === Étape 3 : Scoring distribué sur TOUTES les paires (user, image) ===
    logger.info(f"🚀 Scoring distribué de {len(all_items)} paires (user, image) avec PySpark...")

    items_rdd = sc.parallelize(all_items)

    # Map : calculer score + raison en parallèle (lambda utilise les broadcasts)
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

    return recommendations_by_user, accuracies


def _is_metadata_invalid(item: tuple) -> bool:
    """
    Prédicat exécuté en parallèle par les workers Spark.
    Retourne True si la métadonnée est invalide.
    """
    _, meta = item
    return (
        meta.get('width', 0) <= 0
        or meta.get('height', 0) <= 0
        or meta.get('file_size_kb', 0) <= 0
        or not meta.get('filename')
        or not meta.get('format')
    )


def _is_label_invalid(item: tuple) -> bool:
    """
    Prédicat exécuté en parallèle par les workers Spark.
    Retourne True si le label est invalide.
    """
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
    sur TOUTES les images (plus d'échantillonnage).
    """
    logger.info("📝 Test 1 : Intégrité des données (validation distribuée Spark)")

    try:
        # Test 1.1 : Au moins 100 images
        assert len(metadata) >= 100, f"❌ Pas assez d'images : {len(metadata)} < 100"
        logger.info(f"   ✅ Nombre d'images suffisant : {len(metadata)} images")

        # Test 1.2 : Toutes les images ont des labels
        assert len(metadata) == len(labels), (
            f"❌ Incohérence : {len(metadata)} métadonnées vs {len(labels)} labels"
        )
        logger.info(f"   ✅ Correspondance métadonnées/labels : {len(metadata)} entrées chacun")

        # Test 1.3 : Validation distribuée Spark de TOUTES les métadonnées
        metadata_rdd = sc.parallelize(list(metadata.items()))
        invalid_meta_count = metadata_rdd.filter(_is_metadata_invalid).count()
        assert invalid_meta_count == 0, (
            f"❌ {invalid_meta_count} métadonnée(s) invalide(s) détectée(s) par Spark"
        )
        logger.info(f"   ✅ {len(metadata)} métadonnées validées par Spark (0 invalide)")

        # Test 1.4 : Validation distribuée Spark de TOUS les labels
        labels_rdd = sc.parallelize(list(labels.items()))
        invalid_labels_count = labels_rdd.filter(_is_label_invalid).count()
        assert invalid_labels_count == 0, (
            f"❌ {invalid_labels_count} label(s) invalide(s) détecté(s) par Spark"
        )
        logger.info(f"   ✅ {len(labels)} labels validés par Spark (0 invalide)")

        # Test 1.5 : Toutes les clés métadonnées == clés labels (map + reduce)
        meta_keys_rdd = sc.parallelize(list(metadata.keys()))
        labels_keys = set(labels.keys())
        orphan_count = meta_keys_rdd.filter(lambda k: k not in labels_keys).count()
        assert orphan_count == 0, f"❌ {orphan_count} image(s) sans label correspondant"
        logger.info(f"   ✅ Toutes les images ont un label correspondant (vérifié par Spark)")

        logger.info("✅ Test 1 : RÉUSSI")
        return True

    except AssertionError as e:
        logger.error(f"❌ Test 1 : ÉCHEC - {e}")
        return False


def test_recommendation_quality(recommendations: List[Tuple], user_id: str, 
                               users: Dict, labels: Dict) -> bool:
    """
    Teste la qualité des recommandations.
    """
    logger.info("📝 Test 2 : Qualité des recommandations")

    try:
        # Test 2.1 : Nombre correct
        assert len(recommendations) == 5, f"❌ Nombre incorrect : {len(recommendations)}"
        logger.info("   ✅ Retourne le bon nombre de recommandations : 5")

        # Test 2.2 : Pas de favoris
        user_favorites = set(users[user_id]['favorite_images'])
        recommended_images = [rec[0] for rec in recommendations]

        overlap = set(recommended_images) & user_favorites
        assert len(overlap) == 0, f"❌ Favoris recommandés : {overlap}"
        logger.info("   ✅ Aucune image déjà favorite n'est recommandée")

        # Test 2.3 : Scores décroissants
        scores = [rec[1] for rec in recommendations]
        assert scores == sorted(scores, reverse=True), "❌ Scores non triés"
        logger.info("   ✅ Recommandations triées par score")

        # Test 2.4 : Pertinence
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
    """
    Point d'entrée principal avec traitement PySpark distribué.
    """
    logger.info("🚀 Début des recommandations avec PySpark...")

    # Configuration Spark
    conf = SparkConf().setAppName("ImageRecommendation").setMaster("local[*]")
    sc = SparkContext(conf=conf)

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
        logger.info("🤖 TÂCHE 5 : SYSTÈME DE RECOMMANDATION")

        # Préparer les features
        logger.info("🔧 Préparation des caractéristiques...")
        df_features = prepare_features(labels, metadata)
        X_all, encoders, feature_cols = encode_features(df_features)

        logger.info(f"✅ {len(df_features)} images avec {len(feature_cols)} caractéristiques")

        # Générer recommandations pour tous les utilisateurs EN PARALLÈLE via Spark
        logger.info("=" * 80)
        logger.info("🎯 GÉNÉRATION DES RECOMMANDATIONS (SPARK DISTRIBUÉ MULTI-UTILISATEURS)")
        logger.info("=" * 80)

        recommendations_by_user, accuracies = recommend_all_users_spark(
            users=users,
            df_features=df_features,
            X_all=X_all,
            labels=labels,
            sc=sc,
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
            logger.info(f"   Précision du modèle : {accuracies.get(user_id, 0):.2%}")

            all_recommendations[user_id] = [
                {"filename": filename, "score": score, "reason": reason}
                for filename, score, reason in user_recs
            ]

            logger.info("   📌 Recommandations :")
            for i, (filename, score, reason) in enumerate(user_recs, 1):
                logger.info(f"      {i}. {filename} (score: {score:.3f})")
                logger.info(f"         → {reason}")

            logger.info("-" * 80)

        # Sauvegarder les recommandations
        with open(RECOMMENDATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(all_recommendations, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ Recommandations générées pour {len(all_recommendations)} utilisateurs")
        logger.info(f"💾 Recommandations sauvegardées : {RECOMMENDATIONS_FILE}")

        # === Tâche 6 : Tests ===
        logger.info("=" * 80)
        logger.info("🧪 TÂCHE 6 : TESTS")
        logger.info("=" * 80)

        test_results = []

        # Test 1 : Intégrité des données (validation distribuée Spark sur TOUTES les images)
        test_results.append(test_data_integrity(metadata, labels, sc))

        # Test 2 : Qualité des recommandations (pour un utilisateur test)
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

        logger.info("✅ Traitement complet terminé !")

    finally:
        sc.stop()
        logger.info("🛑 SparkContext arrêté")


if __name__ == "__main__":
    main()
