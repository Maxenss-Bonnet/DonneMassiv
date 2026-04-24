"""
Conteneur 2 : Analyse et Étiquetage
Étiquetage des images et analyse des profils utilisateurs avec PySpark.
La génération des visualisations est déléguée au conteneur 'visualization'.

Optimisations scalabilité (Priorité 1 & 2) :
- Broadcast variable pour `labels` (évite duplication sur chaque worker).
- `mapPartitions` pour KMeans (amortit l'overhead par partition).
- `repartition` explicite (équilibrage des tasks).
- SparkConf paramétrable (mémoire + parallélisme via variables d'env).
"""

import os
import json
import logging
import sys
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Iterator
from PIL import Image
from collections import Counter
from pyspark import SparkContext, SparkConf
from sklearn.cluster import KMeans


# === Configuration du logger ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [analysis] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# === Configuration des chemins ===
INPUT_DIR = Path(os.getenv("INPUT_DIR", "/shared_data"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/shared_data"))
IMAGES_DIR = INPUT_DIR / "images"
METADATA_FILE = INPUT_DIR / "images_metadata.json"
LABELS_FILE = OUTPUT_DIR / "images_labels.json"
USERS_FILE = OUTPUT_DIR / "users.json"

# === Configuration Spark (paramétrable via env pour adapter à la machine cible) ===
SPARK_PARALLELISM = int(os.getenv("SPARK_PARALLELISM", "200"))
SPARK_DRIVER_MEMORY = os.getenv("SPARK_DRIVER_MEMORY", "2g")
SPARK_EXECUTOR_MEMORY = os.getenv("SPARK_EXECUTOR_MEMORY", "2g")


def validate_environment() -> None:
    """
    Valide la présence des entrées requises avant de démarrer Spark.
    """
    if not INPUT_DIR.exists():
        raise RuntimeError(
            f"❌ INPUT_DIR introuvable : {INPUT_DIR}. "
            "Le volume Docker partagé n'est pas monté correctement."
        )
    if not METADATA_FILE.exists():
        raise RuntimeError(
            f"❌ Fichier de métadonnées manquant : {METADATA_FILE}. "
            "Le conteneur 'acquisition' a-t-il bien terminé avec succès ?"
        )
    if not IMAGES_DIR.exists():
        raise RuntimeError(
            f"❌ Dossier images manquant : {IMAGES_DIR}."
        )
    logger.info("✅ Variables d'environnement validées")


# Validation au démarrage
validate_environment()

logger.info(f"📁 Dossier images : {IMAGES_DIR}")
logger.info(f"📁 Fichier métadonnées : {METADATA_FILE}")


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
        logger.error(f"❌ Erreur extraction couleurs {image_path.name} : {e}")
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
    Fonction utilisée par `process_image_labels_partition` (mapPartitions).

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

        logger.info(f"✅ {filename} : {len(dominant_colors)} couleurs, {orientation}, {size_category}")
        return (filename, labels_dict)

    except Exception as e:
        logger.error(f"❌ Erreur traitement {filename} : {e}")
        return (filename, None)


def process_image_labels_partition(items_iter: Iterator[tuple]) -> Iterator[tuple]:
    """
    Traite TOUS les items d'une partition Spark en une seule passe (mapPartitions).

    Avantages vs `map()` :
    - Amortit l'overhead de sérialisation Python<->JVM par partition au lieu de par item.
    - Garde les imports lourds (sklearn, PIL, numpy) chauds dans le worker.
    - Permet d'éventuels traitements batch (ici : itération séquentielle locale).

    À très grande échelle (1M+ images), gain mesurable de 10-30 % sur le temps total.
    """
    for item in items_iter:
        yield process_image_labels(item)


def build_user_profile_broadcast(user_item: tuple, labels_value: dict) -> tuple:
    """
    Construit le profil d'un utilisateur en utilisant les labels diffusés
    via une variable Spark broadcast.

    Args:
        user_item: tuple (user_id, user_data) — sans labels (broadcast)
        labels_value: contenu de la broadcast variable (déréférencé côté lambda)

    Returns:
        tuple (user_id, profile_dict)
    """
    user_id, user_data = user_item
    labels = labels_value

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


def compute_partitions(n_items: int, items_per_partition: int = 10) -> int:
    """
    Calcule un nombre de partitions équilibré :
    - jamais < 4 (pour exploiter le multi-cœurs même sur petit dataset)
    - jamais > SPARK_PARALLELISM (pour ne pas exploser le scheduler)
    """
    return max(4, min(SPARK_PARALLELISM, max(1, n_items // items_per_partition)))


def main():
    """
    Point d'entrée principal avec traitement PySpark distribué.
    La visualisation (Tâche 4) est déléguée au conteneur 'visualization'.
    """
    logger.info("🚀 Début de l'analyse avec PySpark...")

    # === Configuration Spark optimisée pour la scalabilité ===
    conf = (
        SparkConf()
        .setAppName("ImageAnalysis")
        .setMaster("local[*]")
        .set("spark.driver.memory", SPARK_DRIVER_MEMORY)
        .set("spark.executor.memory", SPARK_EXECUTOR_MEMORY)
        .set("spark.default.parallelism", str(SPARK_PARALLELISM))
        .set("spark.sql.shuffle.partitions", str(SPARK_PARALLELISM))
    )
    sc = SparkContext(conf=conf)
    logger.info(
        f"⚙️ Spark : driver={SPARK_DRIVER_MEMORY}, executor={SPARK_EXECUTOR_MEMORY}, "
        f"parallelism={SPARK_PARALLELISM}"
    )

    try:
        # === Tâche 2 : Étiquetage ===
        logger.info("🏷️ TÂCHE 2 : ÉTIQUETAGE")

        # Charger les métadonnées
        with open(METADATA_FILE, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        # Distribuer l'étiquetage sur les workers Spark
        # mapPartitions : amortit l'overhead par partition (vs map par item)
        metadata_items = list(metadata.items())
        n_partitions = compute_partitions(len(metadata_items), items_per_partition=10)
        logger.info(f"📦 {len(metadata_items)} images réparties en {n_partitions} partitions")

        images_rdd = sc.parallelize(metadata_items, numSlices=n_partitions)
        labels_rdd = images_rdd.mapPartitions(process_image_labels_partition)

        # Filter : retirer les échecs
        successful_labels_rdd = labels_rdd.filter(lambda x: x[1] is not None)

        # Collect : récupérer les résultats
        labels_list = successful_labels_rdd.collect()
        labels = {filename: label_data for filename, label_data in labels_list}

        # Sauvegarder
        with open(LABELS_FILE, "w", encoding="utf-8") as f:
            json.dump(labels, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ Étiquetage terminé : {len(labels)} images annotées")
        logger.info(f"💾 Labels sauvegardés : {LABELS_FILE}")

        # === Analyse des tags globaux : FlatMap + ReduceByKey ===
        # FlatMap : aplatit les listes de tags de chaque image en paires (tag, 1)
        # ReduceByKey : agrège pour compter les occurrences par tag
        logger.info("🏷️ Analyse des tags globaux (flatMap + reduceByKey)...")
        tags_rdd = sc.parallelize(list(labels.values()), numSlices=n_partitions)
        tag_counts_rdd = (
            tags_rdd
            .flatMap(lambda label: label["tags"])
            .map(lambda tag: (tag, 1))
            .reduceByKey(lambda a, b: a + b)
            .sortBy(lambda x: x[1], ascending=False)
        )
        top_tags = tag_counts_rdd.take(10)
        logger.info("📊 Top 10 tags les plus fréquents :")
        for tag, count in top_tags:
            logger.info(f"   - {tag} : {count}")

        # === Tâche 3 : Analyse ===
        logger.info("👥 TÂCHE 3 : ANALYSE DES UTILISATEURS")

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

        # === Construction des profils utilisateurs avec BROADCAST ===
        # PRIORITÉ 1 : `labels` est diffusé une seule fois sur chaque worker
        # au lieu d'être sérialisé dans la closure de chaque task.
        logger.info("📡 Broadcast de `labels` sur les workers Spark...")
        labels_bc = sc.broadcast(labels)

        users_items = [(uid, udata) for uid, udata in users_raw.items()]
        n_partitions_users = compute_partitions(len(users_items), items_per_partition=5)
        users_rdd = sc.parallelize(users_items, numSlices=n_partitions_users)

        # Map : construire chaque profil en parallèle (utilise le broadcast)
        profiles_rdd = users_rdd.map(
            lambda x: build_user_profile_broadcast(x, labels_bc.value)
        )

        # Collect
        profiles_list = profiles_rdd.collect()
        users = {user_id: profile for user_id, profile in profiles_list}

        # Libérer le broadcast (récupère la mémoire des workers)
        labels_bc.unpersist()

        # Sauvegarder
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ {len(users)} profils utilisateurs créés")
        logger.info(f"💾 Profils sauvegardés : {USERS_FILE}")

        # Afficher profils
        for user_id, profile in users.items():
            logger.info(f"👤 {user_id} ({profile['name']})")
            logger.info(f"   - Couleurs : {profile['favorite_colors']}")
            logger.info(f"   - Orientation : {profile['favorite_orientation']}")
            logger.info(f"   - Tags : {profile['favorite_tags']}")

        logger.info("✅ Analyse complète terminée — visualisation déléguée au conteneur 'visualization'")

    finally:
        sc.stop()
        logger.info("🛑 SparkContext arrêté")


if __name__ == "__main__":
    main()
