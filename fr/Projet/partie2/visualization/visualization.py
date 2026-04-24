"""
Conteneur 4 : Visualisation
Génère les graphiques statistiques à partir des labels, métadonnées et profils
utilisateurs produits par les conteneurs précédents.
Séparé du conteneur d'analyse pour une meilleure séparation des responsabilités.
"""

import os
import json
import logging
import sys
from pathlib import Path
from typing import Dict
from collections import Counter

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif pour Docker
import matplotlib.pyplot as plt
import matplotlib.patches as patches


# === Configuration du logger ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [visualization] %(message)s',
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
VIZ_FILE = OUTPUT_DIR / "visualisations.png"


def validate_environment() -> None:
    """Valide la présence des fichiers produits par le conteneur d'analyse."""
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


def create_visualizations(metadata: Dict, labels: Dict, users: Dict) -> None:
    """
    Crée les 9 visualisations statistiques dans un unique fichier PNG.
    """
    df_meta = pd.DataFrame(metadata).T
    df_labels = pd.DataFrame(labels).T

    plt.rcParams['figure.figsize'] = (12, 8)
    plt.rcParams['font.size'] = 10

    fig = plt.figure(figsize=(18, 12))

    # 1. Distribution par orientation
    ax1 = plt.subplot(3, 3, 1)
    orientation_counts = df_labels['orientation'].value_counts()
    ax1.bar(orientation_counts.index, orientation_counts.values,
            color=['#3498db', '#e74c3c', '#2ecc71'])
    ax1.set_title('Distribution par Orientation', fontsize=12, fontweight='bold')
    ax1.set_ylabel("Nombre d'images")
    ax1.grid(axis='y', alpha=0.3)

    # 2. Distribution par catégorie de taille
    ax2 = plt.subplot(3, 3, 2)
    size_counts = df_labels['size_category'].value_counts()
    ax2.bar(size_counts.index, size_counts.values,
            color=['#f39c12', '#9b59b6', '#1abc9c'])
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
                                     facecolor=np.array(color)/255,
                                     edgecolor='black', linewidth=0.5)
            ax7.add_patch(rect)
        y_pos += 1

    ax7.set_xlim(0, 5)
    ax7.set_ylim(0, len(sample_images))
    ax7.set_aspect('equal')
    ax7.set_title('Palettes de Couleurs (10 images)', fontsize=12, fontweight='bold')
    ax7.set_yticks(np.arange(len(sample_images)) + 0.4)
    ax7.set_yticklabels([img.replace('image_', 'img_').replace('.jpg', '')
                         for img in sample_images])
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
    plt.close(fig)

    logger.info(f"💾 Visualisations sauvegardées : {VIZ_FILE}")


def main() -> None:
    """Point d'entrée : charge les données JSON et génère le PNG."""
    logger.info("🚀 Début de la génération des visualisations...")
    validate_environment()

    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        metadata = json.load(f)
    with open(LABELS_FILE, "r", encoding="utf-8") as f:
        labels = json.load(f)
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        users = json.load(f)

    logger.info(f"📥 {len(metadata)} images, {len(labels)} labels, {len(users)} utilisateurs")

    create_visualizations(metadata, labels, users)

    logger.info("✅ Génération des visualisations terminée")


if __name__ == "__main__":
    main()
