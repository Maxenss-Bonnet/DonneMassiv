"""
Conteneur 1 : Acquisition de données
Collecte des images depuis Unsplash API avec traitement distribué via PySpark.
"""

import os
import json
import requests
from pathlib import Path
from typing import List, Dict
from PIL import Image
from PIL.ExifTags import TAGS
from pyspark import SparkContext, SparkConf

# Configuration
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "/shared_data"))
IMAGES_DIR = OUTPUT_DIR / "images"
METADATA_FILE = OUTPUT_DIR / "images_metadata.json"
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

# Créer les dossiers
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

print(f"📁 Dossier images : {IMAGES_DIR}")
print(f"📁 Fichier métadonnées : {METADATA_FILE}")


def fetch_unsplash_images(query: str, per_page: int = 30, pages: int = 1) -> List[Dict]:
    """
    Récupère des images depuis Unsplash API.
    
    Args:
        query: Terme de recherche
        per_page: Nombre d'images par page (max 30)
        pages: Nombre de pages à récupérer
    
    Returns:
        Liste de dictionnaires contenant les infos des images
    """
    base_url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
    
    images_data = []
    
    for page in range(1, pages + 1):
        params = {
            "query": query,
            "per_page": per_page,
            "page": page
        }
        
        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            images_data.extend(data.get("results", []))
            
            print(f"✅ Query '{query}' - Page {page}/{pages} : {len(data.get('results', []))} images")
            
        except Exception as e:
            print(f"❌ Erreur page {page} pour '{query}' : {e}")
            continue
    
    return images_data


def extract_exif_data(image_path: Path) -> Dict:
    """
    Extrait les données EXIF d'une image.
    
    Args:
        image_path: Chemin vers l'image
    
    Returns:
        Dictionnaire contenant les données EXIF
    """
    exif_data = {}
    
    try:
        img = Image.open(image_path)
        exif = img._getexif()
        
        if exif:
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_data[tag] = str(value)
    except:
        pass
    
    return exif_data


def process_image(item: tuple) -> tuple:
    """
    Traite une image : téléchargement et extraction de métadonnées.
    Cette fonction est exécutée en parallèle par les workers Spark.
    
    Args:
        item: tuple (counter, img_data, query)
    
    Returns:
        tuple (filename, metadata_dict) ou (None, None) si échec
    """
    counter, img_data, query = item
    filename = f"image_{counter:03d}.jpg"
    
    try:
        # Télécharger l'image
        image_url = img_data["urls"]["regular"]
        response = requests.get(image_url, timeout=15)
        response.raise_for_status()
        
        filepath = IMAGES_DIR / filename
        filepath.write_bytes(response.content)
        
        # Ouvrir l'image pour extraire les infos
        with Image.open(filepath) as img:
            width, height = img.size
            format_img = img.format
        
        # Taille du fichier en Ko
        file_size_kb = filepath.stat().st_size / 1024
        
        # Extraire données EXIF
        exif_data = extract_exif_data(filepath)
        
        # Créer le dictionnaire de métadonnées
        metadata = {
            "filename": filename,
            "width": width,
            "height": height,
            "format": format_img,
            "file_size_kb": round(file_size_kb, 2),
            "source_url": img_data["links"]["html"],
            "download_url": image_url,
            "license": "Unsplash License",
            "author": img_data["user"]["name"],
            "author_url": img_data["user"]["links"]["html"],
            "description": img_data.get("description", ""),
            "alt_description": img_data.get("alt_description", ""),
            "query": query,
            "exif": exif_data
        }
        
        print(f"✅ {filename} : {width}x{height}, {file_size_kb:.1f} Ko")
        return (filename, metadata)
    
    except Exception as e:
        print(f"❌ Erreur traitement {filename} : {e}")
        return (None, None)


def main():
    """
    Point d'entrée principal avec traitement PySpark distribué.
    """
    print("🚀 Début de la collecte d'images avec PySpark...\n")
    
    # Configuration Spark
    conf = SparkConf().setAppName("ImageAcquisition").setMaster("local[*]")
    sc = SparkContext(conf=conf)
    
    try:
        # Diversifier les requêtes pour avoir une collection variée
        search_queries = ["nature", "architecture", "food", "animals", "technology", "art"]
        
        # Collecter toutes les images depuis l'API
        all_images_data = []
        for query in search_queries:
            print(f"\n🔍 Recherche : '{query}'")
            images = fetch_unsplash_images(query, per_page=20, pages=1)
            # Ajouter le query à chaque image pour le traitement
            all_images_data.extend([(i + 1 + len(all_images_data), img, query) 
                                    for i, img in enumerate(images)])
        
        print(f"\n📥 {len(all_images_data)} images à traiter")
        
        # Distribuer le traitement des images sur les workers Spark
        # Map : télécharger et extraire métadonnées en parallèle
        images_rdd = sc.parallelize(all_images_data)
        metadata_rdd = images_rdd.map(process_image)
        
        # Filter : retirer les images qui ont échoué (None, None)
        successful_rdd = metadata_rdd.filter(lambda x: x[0] is not None)
        
        # Collect : récupérer tous les résultats
        results = successful_rdd.collect()
        
        # Convertir en dictionnaire
        all_metadata = {filename: metadata for filename, metadata in results}
        
        # Sauvegarder les métadonnées
        with open(METADATA_FILE, "w", encoding="utf-8") as f:
            json.dump(all_metadata, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Collecte terminée : {len(all_metadata)} images téléchargées")
        print(f"💾 Métadonnées sauvegardées : {METADATA_FILE}")
        
        # Statistiques
        if all_metadata:
            total_size = sum(m["file_size_kb"] for m in all_metadata.values())
            avg_width = sum(m["width"] for m in all_metadata.values()) / len(all_metadata)
            avg_height = sum(m["height"] for m in all_metadata.values()) / len(all_metadata)
            
            print(f"\n📈 Statistiques :")
            print(f"  - Taille totale : {total_size:.2f} Ko")
            print(f"  - Dimensions moyennes : {avg_width:.0f} x {avg_height:.0f} px")
    
    finally:
        sc.stop()
        print("\n🛑 SparkContext arrêté")


if __name__ == "__main__":
    main()
