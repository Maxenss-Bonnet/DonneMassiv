"""
Conteneur 2 : Analyse et Étiquetage
Étiquetage des images, analyse des utilisateurs et visualisation avec PySpark.
"""

import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Tuple
from PIL import Image
from collections import Counter
from pyspark import SparkContext, SparkConf
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif pour Docker
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from sklearn.cluster import KMeans

# Configuration
INPUT_DIR = Path(os.getenv("INPUT_DIR", "/shared_data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/shared_data"))
IMAGES_DIR = INPUT_DIR / "images"
METADATA_FILE = INPUT_DIR / "images_metadata.json"
LABELS_FILE = OUTPUT_DIR / "images_labels.json"
USERS_FILE = OUTPUT_DIR / "users.json"
VIZ_FILE = OUTPUT_DIR / "visualisations.png"

print(f"📁 Dossier images : {IMAGES_DIR}")
print(f"📁 Fichier métadonnées : {METADATA_FILE}")


def rgb_to_name(rgb: Tuple[int, int, int]) -> str:
    """
    Convertit une couleur RGB en nom approximatif.
    """
    r, g, b = rgb
    
    if r > 200 and g < 100 and b < 100:
        return "rouge"
    elif r < 100 and g > 200 and b < 100:
        return "vert"
    elif r < 100 and g < 100 and b > 200:
        return "bleu"
    elif r > 200 and g > 200 and b < 100:
        return "jaune"
    elif r > 200 and g < 150 and b > 200:
        return "magenta"
    elif r < 150 and g > 200 and b > 200:
        return "cyan"
    elif r > 220 and g > 220 and b > 220:
        return "blanc"
    elif r < 50 and g < 50 and b < 50:
        return "noir"
    elif abs(r - g) < 20 and abs(g - b) < 20:
        return "gris"
    elif r > 200 and g > 150 and b < 100:
        return "orange"
    elif r > 150 and g > 100 and b < 80:
        return "marron"
    elif r > 200 and g > 150 and b > 200:
        return "rose"
    else:
        if r > g and r > b:
            return "rouge"
        elif g > r and g > b:
            return "vert"
        else:
            return "bleu"


def extract_dominant_colors(image_path: Path, n_colors: int = 5) -> List[List[int]]:
    """
    Extrait les couleurs dominantes d'une image avec KMeans.
    """
    try:
        img = Image.open(image_path)
        img.thumbnail((200, 200))
        
        img_array = np.array(img)
        
        if len(img_array.shape) == 2:
            img_array = np.stack([img_array] * 3, axis=-1)
        elif img_array.shape[2] == 4:
            img_array = img_array[:, :, :3]
        
        pixels = img_array.reshape(-1, 3)
        
        kmeans = KMeans(n_clusters=n_colors, random_state=42, n_init=10)
        kmeans.fit(pixels)
        
        colors = kmeans.cluster_centers_.astype(int).tolist()
        
        return colors
    
    except Exception as e:
        print(f"❌ Erreur extraction couleurs {image_path.name} : {e}")
        return [[128, 128, 128]]


def get_orientation(width: int, height: int) -> str:
    """Détermine l'orientation d'une image."""
    ratio = width / height
    
    if 0.95 <= ratio <= 1.05:
        return "carré"
    elif ratio > 1.05:
        return "paysage"
    else:
        return "portrait"


def get_size_category(width: int, height: int) -> str:
    """Détermine la catégorie de taille d'une image."""
    max_dimension = max(width, height)
    
    if max_dimension < 500:
        return "vignette"
    elif max_dimension <= 1500:
        return "moyenne"
    else:
        return "grande"


def process_image_labels(item: tuple) -> tuple:
    """
    Traite une image et extrait ses labels.
    Fonction exécutée en parallèle par les workers Spark.
    
    Args:
        item: tuple (filename, metadata_dict)
    
    Returns:
        tuple (filename, labels_dict)
    """
    filename, meta = item
    
    try:
        image_path = IMAGES_DIR / filename
        
        # Extraire couleurs dominantes
        dominant_colors = extract_dominant_colors(image_path, n_colors=5)
        
        # Convertir RGB en noms
        color_names = [rgb_to_name(tuple(color)) for color in dominant_colors]
        
        # Orientation
        orientation = get_orientation(meta["width"], meta["height"])
        
        # Catégorie de taille
        size_category = get_size_category(meta["width"], meta["height"])
        
        # Tags (depuis la description/query)
        tags = [meta["query"]]
        if meta.get("alt_description"):
            words = meta["alt_description"].lower().split()
            tags.extend([w for w in words if len(w) > 3][:5])
        
        # Labels
        labels_dict = {
            "predominant_colors": dominant_colors,
            "color_names": color_names,
            "orientation": orientation,
            "size_category": size_category,
            "tags": list(set(tags))
        }
        
        print(f"✅ {filename} : {len(dominant_colors)} couleurs, {orientation}, {size_category}")
        return (filename, labels_dict)
    
    except Exception as e:
        print(f"❌ Erreur traitement {filename} : {e}")
        return (filename, None)


def build_user_profile(user_item: tuple) -> tuple:
    """
    Construit le profil d'un utilisateur.
    Fonction exécutée en parallèle par les workers Spark.
    
    Args:
        user_item: tuple (user_id, user_data, labels)
    
    Returns:
        tuple (user_id, profile_dict)
    """
    user_id, user_data, labels = user_item
    
    favorites = user_data["favorite_images"]
    
    # Map: collecter les couleurs de chaque image favorite
    all_colors = []
    for img in favorites:
        if img in labels:
            all_colors.extend(labels[img]["color_names"])
    
    # Map: collecter orientations et tailles
    all_orientations = [labels[img]["orientation"] for img in favorites if img in labels]
    all_sizes = [labels[img]["size_category"] for img in favorites if img in labels]
    
    # FlatMap + reduce: collecter tous les tags
    all_tags = []
    for img in favorites:
        if img in labels:
            all_tags.extend(labels[img]["tags"])
    
    # Trouver les plus fréquents
    favorite_colors = [color for color, _ in Counter(all_colors).most_common(3)]
    favorite_orientation = Counter(all_orientations).most_common(1)[0][0] if all_orientations else "paysage"
    favorite_size = Counter(all_sizes).most_common(1)[0][0] if all_sizes else "moyenne"
    favorite_tags = [tag for tag, _ in Counter(all_tags).most_common(5)]
    
    profile = {
        "user_id": user_id,
        "name": user_data["name"],
        "favorite_colors": favorite_colors,
        "favorite_orientation": favorite_orientation,
        "favorite_size": favorite_size,
        "favorite_tags": favorite_tags,
        "favorite_images": favorites
    }
    
    return (user_id, profile)


def create_visualizations(metadata: Dict, labels: Dict, users: Dict):
    """
    Crée les visualisations avec matplotlib.
    """
    df_meta = pd.DataFrame(metadata).T
    df_labels = pd.DataFrame(labels).T
    
    plt.rcParams['figure.figsize'] = (12, 8)
    plt.rcParams['font.size'] = 10
    
    fig = plt.figure(figsize=(18, 12))
    
    # 1. Distribution par orientation
    ax1 = plt.subplot(3, 3, 1)
    orientation_counts = df_labels['orientation'].value_counts()
    ax1.bar(orientation_counts.index, orientation_counts.values, color=['#3498db', '#e74c3c', '#2ecc71'])
    ax1.set_title('Distribution par Orientation', fontsize=12, fontweight='bold')
    ax1.set_ylabel("Nombre d'images")
    ax1.grid(axis='y', alpha=0.3)
    
    # 2. Distribution par catégorie de taille
    ax2 = plt.subplot(3, 3, 2)
    size_counts = df_labels['size_category'].value_counts()
    ax2.bar(size_counts.index, size_counts.values, color=['#f39c12', '#9b59b6', '#1abc9c'])
    ax2.set_title('Distribution par Catégorie de Taille', fontsize=12, fontweight='bold')
    ax2.set_ylabel("Nombre d'images")
    ax2.grid(axis='y', alpha=0.3)
    
    # 3. Distribution des formats
    ax3 = plt.subplot(3, 3, 3)
    format_counts = df_meta['format'].value_counts()
    colors_pie = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12']
    ax3.pie(format_counts.values, labels=format_counts.index, autopct='%1.1f%%', 
            colors=colors_pie[:len(format_counts)], startangle=90)
    ax3.set_title('Distribution des Formats', fontsize=12, fontweight='bold')
    
    # 4. Top 10 couleurs
    ax4 = plt.subplot(3, 3, 4)
    all_colors = []
    for colors_list in df_labels['color_names']:
        all_colors.extend(colors_list)
    color_freq = Counter(all_colors)
    top_colors = color_freq.most_common(10)
    ax4.barh([c[0] for c in top_colors], [c[1] for c in top_colors], color='#3498db')
    ax4.set_title('Top 10 Couleurs Prédominantes', fontsize=12, fontweight='bold')
    ax4.set_xlabel('Fréquence')
    ax4.grid(axis='x', alpha=0.3)
    
    # 5. Top 10 tags
    ax5 = plt.subplot(3, 3, 5)
    all_tags = []
    for tags_list in df_labels['tags']:
        all_tags.extend(tags_list)
    tag_freq = Counter(all_tags)
    top_tags = tag_freq.most_common(10)
    ax5.barh([t[0] for t in top_tags], [t[1] for t in top_tags], color='#e74c3c')
    ax5.set_title('Top 10 Tags', fontsize=12, fontweight='bold')
    ax5.set_xlabel('Fréquence')
    ax5.grid(axis='x', alpha=0.3)
    
    # 6. Distribution taille fichiers
    ax6 = plt.subplot(3, 3, 6)
    ax6.hist(df_meta['file_size_kb'], bins=30, color='#9b59b6', edgecolor='black', alpha=0.7)
    ax6.set_title('Distribution de la Taille des Fichiers', fontsize=12, fontweight='bold')
    ax6.set_xlabel('Taille (Ko)')
    ax6.set_ylabel('Fréquence')
    ax6.grid(axis='y', alpha=0.3)
    
    # 7. Palettes de couleurs
    ax7 = plt.subplot(3, 3, 7)
    sample_images = list(labels.keys())[:10]
    y_pos = 0
    for img in sample_images:
        colors = labels[img]['predominant_colors']
        for i, color in enumerate(colors[:5]):
            rect = patches.Rectangle((i, y_pos), 1, 0.8, 
                                     facecolor=np.array(color)/255, edgecolor='black', linewidth=0.5)
            ax7.add_patch(rect)
        y_pos += 1
    
    ax7.set_xlim(0, 5)
    ax7.set_ylim(0, len(sample_images))
    ax7.set_aspect('equal')
    ax7.set_title('Palettes de Couleurs (10 images)', fontsize=12, fontweight='bold')
    ax7.set_yticks(np.arange(len(sample_images)) + 0.4)
    ax7.set_yticklabels([img.replace('image_', 'img_').replace('.jpg', '') for img in sample_images])
    ax7.set_xticks([])
    
    # 8. Couleurs préférées par utilisateur
    ax8 = plt.subplot(3, 3, 8)
    user_names = [u['name'][:15] for u in users.values()]
    user_color_counts = {}
    
    for user in users.values():
        for color in user['favorite_colors']:
            if color not in user_color_counts:
                user_color_counts[color] = []
            user_color_counts[color].append(user['name'][:15])
    
    bottom = np.zeros(len(user_names))
    colors_to_plot = list(user_color_counts.keys())[:5]
    
    for color in colors_to_plot:
        values = [user_color_counts[color].count(name) for name in user_names]
        ax8.bar(user_names, values, bottom=bottom, label=color, alpha=0.8)
        bottom += values
    
    ax8.set_title('Couleurs Préférées par Utilisateur', fontsize=12, fontweight='bold')
    ax8.set_ylabel('Nombre de couleurs favorites')
    ax8.legend(loc='upper right', fontsize=8)
    ax8.tick_params(axis='x', rotation=45)
    plt.setp(ax8.xaxis.get_majorticklabels(), rotation=45, ha='right')
    
    # 9. Largeur vs Hauteur
    ax9 = plt.subplot(3, 3, 9)
    ax9.scatter(df_meta['width'], df_meta['height'], alpha=0.5, c='#2ecc71', s=50)
    ax9.set_title('Distribution Largeur vs Hauteur', fontsize=12, fontweight='bold')
    ax9.set_xlabel('Largeur (px)')
    ax9.set_ylabel('Hauteur (px)')
    ax9.grid(alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(VIZ_FILE, dpi=150, bbox_inches='tight')
    
    print(f"💾 Visualisations sauvegardées : {VIZ_FILE}")


def main():
    """
    Point d'entrée principal avec traitement PySpark distribué.
    """
    print("🚀 Début de l'analyse avec PySpark...\n")
    
    # Configuration Spark
    conf = SparkConf().setAppName("ImageAnalysis").setMaster("local[*]")
    sc = SparkContext(conf=conf)
    
    try:
        # === Tâche 2 : Étiquetage ===
        print("\n🏷️ TÂCHE 2 : ÉTIQUETAGE\n")
        
        # Charger les métadonnées
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        # Distribuer l'étiquetage sur les workers Spark
        # Map : traiter chaque image en parallèle
        metadata_items = list(metadata.items())
        images_rdd = sc.parallelize(metadata_items)
        labels_rdd = images_rdd.map(process_image_labels)
        
        # Filter : retirer les échecs
        successful_labels_rdd = labels_rdd.filter(lambda x: x[1] is not None)
        
        # Collect : récupérer les résultats
        labels_list = successful_labels_rdd.collect()
        labels = {filename: label_data for filename, label_data in labels_list}
        
        # Sauvegarder
        with open(LABELS_FILE, "w", encoding="utf-8") as f:
            json.dump(labels, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Étiquetage terminé : {len(labels)} images annotées")
        print(f"💾 Labels sauvegardés : {LABELS_FILE}")
        
        # === Analyse des tags globaux : FlatMap + ReduceByKey ===
        # FlatMap : aplatit les listes de tags de chaque image en paires (tag, 1)
        # ReduceByKey : agrège pour compter les occurrences par tag
        print("\n🏷️ Analyse des tags globaux (flatMap + reduceByKey)...")
        tags_rdd = sc.parallelize(list(labels.values()))
        tag_counts_rdd = (
            tags_rdd
            .flatMap(lambda label: label["tags"])
            .map(lambda tag: (tag, 1))
            .reduceByKey(lambda a, b: a + b)
            .sortBy(lambda x: x[1], ascending=False)
        )
        top_tags = tag_counts_rdd.take(10)
        print("📊 Top 10 tags les plus fréquents :")
        for tag, count in top_tags:
            print(f"   - {tag} : {count}")
        
        # === Tâche 3 : Analyse ===
        print("\n👥 TÂCHE 3 : ANALYSE DES UTILISATEURS\n")
        
        # Créer utilisateurs simulés
        all_images = list(labels.keys())
        
        user_preferences = [
            {"name": "Amoureux de la nature", "preferred_tags": ["nature", "animals"]},
            {"name": "Fan d'architecture", "preferred_tags": ["architecture", "technology"]},
            {"name": "Foodie", "preferred_tags": ["food"]},
            {"name": "Artiste", "preferred_tags": ["art"]},
            {"name": "Éclectique", "preferred_tags": []},
        ]
        
        users_raw = {}
        for i, prefs in enumerate(user_preferences):
            user_id = f"user_{i+1:03d}"
            
            # Sélectionner favoris
            if prefs["preferred_tags"]:
                matching_images = [
                    img for img in all_images
                    if any(tag in labels[img]["tags"] for tag in prefs["preferred_tags"])
                ]
                if matching_images:
                    n_favs = min(len(matching_images), np.random.randint(10, 21))
                    favorites = np.random.choice(matching_images, n_favs, replace=False).tolist()
                else:
                    n_favs = np.random.randint(10, 21)
                    favorites = np.random.choice(all_images, n_favs, replace=False).tolist()
            else:
                n_favs = np.random.randint(10, 21)
                favorites = np.random.choice(all_images, n_favs, replace=False).tolist()
            
            users_raw[user_id] = {
                "user_id": user_id,
                "name": prefs["name"],
                "favorite_images": favorites
            }
        
        # Distribuer la construction des profils sur Spark
        # Map : construire chaque profil en parallèle
        users_items = [(uid, udata, labels) for uid, udata in users_raw.items()]
        users_rdd = sc.parallelize(users_items)
        profiles_rdd = users_rdd.map(build_user_profile)
        
        # Collect
        profiles_list = profiles_rdd.collect()
        users = {user_id: profile for user_id, profile in profiles_list}
        
        # Sauvegarder
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ {len(users)} profils utilisateurs créés")
        print(f"💾 Profils sauvegardés : {USERS_FILE}")
        
        # Afficher profils
        for user_id, profile in users.items():
            print(f"\n  👤 {user_id} ({profile['name']}) :")
            print(f"     - Couleurs : {profile['favorite_colors']}")
            print(f"     - Orientation : {profile['favorite_orientation']}")
            print(f"     - Tags : {profile['favorite_tags']}")
        
        # === Tâche 4 : Visualisation ===
        print("\n📊 TÂCHE 4 : VISUALISATION\n")
        
        create_visualizations(metadata, labels, users)
        
        print("\n✅ Analyse complète terminée !")
    
    finally:
        sc.stop()
        print("\n🛑 SparkContext arrêté")


if __name__ == "__main__":
    main()
