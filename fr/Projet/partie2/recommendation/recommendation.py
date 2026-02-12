"""
Conteneur 3 : Recommandation
Système de recommandation et tests avec traitement distribué PySpark.
"""

import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple
from collections import Counter
from pyspark import SparkContext, SparkConf
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Configuration
INPUT_DIR = Path(os.getenv("INPUT_DIR", "/shared_data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/shared_data"))
METADATA_FILE = INPUT_DIR / "images_metadata.json"
LABELS_FILE = INPUT_DIR / "images_labels.json"
USERS_FILE = INPUT_DIR / "users.json"
RECOMMENDATIONS_FILE = OUTPUT_DIR / "recommendations.json"

print(f"📁 Dossier données : {INPUT_DIR}")
print(f"📁 Fichier recommandations : {RECOMMENDATIONS_FILE}")


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


def compute_recommendation_score(item: tuple) -> tuple:
    """
    Calcule le score de recommandation pour une image.
    Fonction exécutée en parallèle par les workers Spark.
    
    Args:
        item: tuple (filename, proba, idx, favorites, labels, user_profile)
    
    Returns:
        tuple (filename, score, reason) ou None si image déjà en favoris
    """
    filename, proba, idx, favorites, labels, user_profile = item
    
    # Exclure les favoris
    if filename in favorites:
        return None
    
    # Générer une raison
    img_labels = labels[filename]
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
    
    return (filename, float(proba), reason)


def recommend_images_spark(user_id: str, users: Dict, df_features: pd.DataFrame, 
                          X_all: np.ndarray, labels: Dict, sc: SparkContext,
                          n_recommendations: int = 5) -> List[Tuple]:
    """
    Recommande des images pour un utilisateur avec PySpark.
    
    Args:
        user_id: ID de l'utilisateur
        users: Dictionnaire des utilisateurs
        df_features: DataFrame des caractéristiques
        X_all: Array encodé de toutes les features
        labels: Dictionnaire des labels
        sc: SparkContext
        n_recommendations: Nombre de recommandations
    
    Returns:
        Liste de tuples (filename, score, raison)
    """
    # Entraîner le modèle
    model, y, idx_test, accuracy = train_user_model(user_id, users, df_features, X_all)
    
    print(f"\n🎯 Modèle pour {user_id} :")
    print(f"   - Précision : {accuracy:.2%}")
    
    # Obtenir les favoris et le profil
    favorites = set(users[user_id]['favorite_images'])
    user_profile = users[user_id]
    
    # Prédire les probabilités pour TOUTES les images
    probas = model.predict_proba(X_all)[:, 1]
    
    # Créer une liste d'items à traiter
    items = []
    for idx, (filename, proba) in enumerate(zip(df_features['filename'], probas)):
        items.append((filename, proba, idx, favorites, labels, user_profile))
    
    # Distribuer le calcul des scores avec PySpark
    # Map : calculer le score et la raison pour chaque image en parallèle
    items_rdd = sc.parallelize(items)
    scores_rdd = items_rdd.map(compute_recommendation_score)
    
    # Filter : retirer les None (favoris exclus)
    valid_scores_rdd = scores_rdd.filter(lambda x: x is not None)
    
    # SortBy : trier par score décroissant
    sorted_scores_rdd = valid_scores_rdd.sortBy(lambda x: x[1], ascending=False)
    
    # Take : prendre les top N recommandations
    recommendations = sorted_scores_rdd.take(n_recommendations)
    
    return recommendations


def test_data_integrity(metadata: Dict, labels: Dict) -> bool:
    """
    Teste l'intégrité des données.
    """
    print("\n📝 Test 1 : Intégrité des données\n")
    
    try:
        # Test 1.1 : Au moins 100 images
        assert len(metadata) >= 100, f"❌ Pas assez d'images : {len(metadata)} < 100"
        print(f"   ✅ Nombre d'images suffisant : {len(metadata)} images")
        
        # Test 1.2 : Toutes les images ont des labels
        assert len(metadata) == len(labels), f"❌ Nombre de labels incorrect"
        print(f"   ✅ Toutes les images ont des labels")
        
        # Test 1.3 : Métadonnées valides
        for filename, meta in list(metadata.items())[:10]:  # Vérifier échantillon
            assert meta['width'] > 0, f"❌ Largeur invalide pour {filename}"
            assert meta['height'] > 0, f"❌ Hauteur invalide pour {filename}"
            assert meta['file_size_kb'] > 0, f"❌ Taille invalide pour {filename}"
        
        print(f"   ✅ Métadonnées valides (échantillon)")
        
        print(f"\n✅ Test 1 : RÉUSSI\n")
        return True
    
    except AssertionError as e:
        print(f"\n❌ Test 1 : ÉCHEC - {e}\n")
        return False


def test_recommendation_quality(recommendations: List[Tuple], user_id: str, 
                               users: Dict, labels: Dict) -> bool:
    """
    Teste la qualité des recommandations.
    """
    print("\n📝 Test 2 : Qualité des recommandations\n")
    
    try:
        # Test 2.1 : Nombre correct
        assert len(recommendations) == 5, f"❌ Nombre incorrect : {len(recommendations)}"
        print(f"   ✅ Retourne le bon nombre de recommandations : 5")
        
        # Test 2.2 : Pas de favoris
        user_favorites = set(users[user_id]['favorite_images'])
        recommended_images = [rec[0] for rec in recommendations]
        
        overlap = set(recommended_images) & user_favorites
        assert len(overlap) == 0, f"❌ Favoris recommandés : {overlap}"
        print(f"   ✅ Aucune image déjà favorite n'est recommandée")
        
        # Test 2.3 : Scores décroissants
        scores = [rec[1] for rec in recommendations]
        assert scores == sorted(scores, reverse=True), "❌ Scores non triés"
        print(f"   ✅ Recommandations triées par score")
        
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
        print(f"   ✅ Pertinence : {relevance_ratio:.1%} des recommandations correspondent au profil")
        
        assert relevance_ratio >= 0.4, f"❌ Recommandations peu pertinentes : {relevance_ratio:.1%}"
        
        print(f"\n✅ Test 2 : RÉUSSI\n")
        return True
    
    except AssertionError as e:
        print(f"\n❌ Test 2 : ÉCHEC - {e}\n")
        return False


def main():
    """
    Point d'entrée principal avec traitement PySpark distribué.
    """
    print("🚀 Début des recommandations avec PySpark...\n")
    
    # Configuration Spark
    conf = SparkConf().setAppName("ImageRecommendation").setMaster("local[*]")
    sc = SparkContext(conf=conf)
    
    try:
        # Charger les données
        print("📥 Chargement des données...\n")
        
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        with open(LABELS_FILE, "r", encoding="utf-8") as f:
            labels = json.load(f)
        
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users = json.load(f)
        
        print(f"✅ {len(metadata)} images chargées")
        print(f"✅ {len(users)} utilisateurs chargés")
        
        # === Tâche 5 : Système de Recommandation ===
        print("\n🤖 TÂCHE 5 : SYSTÈME DE RECOMMANDATION\n")
        
        # Préparer les features
        print("🔧 Préparation des caractéristiques...\n")
        df_features = prepare_features(labels, metadata)
        X_all, encoders, feature_cols = encode_features(df_features)
        
        print(f"✅ {len(df_features)} images avec {len(feature_cols)} caractéristiques")
        
        # Générer recommandations pour tous les utilisateurs
        print("\n" + "=" * 80)
        print("🎯 GÉNÉRATION DES RECOMMANDATIONS")
        print("=" * 80)
        
        all_recommendations = {}
        
        for user_id in users.keys():
            user_name = users[user_id]['name']
            print(f"\n👤 Utilisateur : {user_name} ({user_id})")
            print(f"   Profil : Aime {', '.join(users[user_id]['favorite_colors'][:3])}")
            print(f"   Tags favoris : {', '.join(users[user_id]['favorite_tags'][:3])}")
            
            recommendations = recommend_images_spark(
                user_id=user_id,
                users=users,
                df_features=df_features,
                X_all=X_all,
                labels=labels,
                sc=sc,
                n_recommendations=5
            )
            
            # Convertir en format JSON-serializable
            all_recommendations[user_id] = [
                {
                    "filename": filename,
                    "score": score,
                    "reason": reason
                }
                for filename, score, reason in recommendations
            ]
            
            print(f"\n   📌 Recommandations :")
            for i, (filename, score, reason) in enumerate(recommendations, 1):
                print(f"      {i}. {filename} (score: {score:.3f})")
                print(f"         → {reason}")
            
            print("\n" + "-" * 80)
        
        # Sauvegarder les recommandations
        with open(RECOMMENDATIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(all_recommendations, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Recommandations générées pour {len(all_recommendations)} utilisateurs")
        print(f"💾 Recommandations sauvegardées : {RECOMMENDATIONS_FILE}")
        
        # === Tâche 6 : Tests ===
        print("\n" + "=" * 80)
        print("🧪 TÂCHE 6 : TESTS")
        print("=" * 80)
        
        test_results = []
        
        # Test 1 : Intégrité des données
        test_results.append(test_data_integrity(metadata, labels))
        
        # Test 2 : Qualité des recommandations (pour un utilisateur test)
        test_user = list(users.keys())[0]
        test_recs = [(r["filename"], r["score"], r["reason"]) 
                     for r in all_recommendations[test_user]]
        test_results.append(test_recommendation_quality(test_recs, test_user, users, labels))
        
        # Résumé
        print("\n" + "=" * 80)
        if all(test_results):
            print("🎉 TOUS LES TESTS RÉUSSIS !")
        else:
            print("⚠️ CERTAINS TESTS ONT ÉCHOUÉ")
        print("=" * 80)
        
        print("\n✅ Traitement complet terminé !")
    
    finally:
        sc.stop()
        print("\n🛑 SparkContext arrêté")


if __name__ == "__main__":
    main()
