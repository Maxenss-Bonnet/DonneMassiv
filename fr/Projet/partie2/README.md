# Partie 2 : Système de Recommandation Distribué

## 📋 Description

Cette partie transforme le notebook monolithique de la partie 1 en une **application distribuée et conteneurisée** utilisant Docker et PySpark.

Le système est décomposé en **3 conteneurs indépendants** qui communiquent via un volume Docker partagé :

1. **Conteneur Acquisition** : Collecte des images depuis Unsplash API avec traitement parallèle
2. **Conteneur Analysis** : Étiquetage des images, analyse des utilisateurs et visualisation
3. **Conteneur Recommendation** : Système de recommandation et tests

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        docker-compose.yml                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐   ┌──────────────────┐   ┌────────────────┐   │
│  │  Conteneur 1 :    │──▶│  Conteneur 2 :    │──▶│  Conteneur 3 : │   │
│  │  Acquisition      │   │  Analysis         │   │ Recommendation │   │
│  │  - Télécharger    │   │  - Extraction     │   │ - Profil util. │   │
│  │  - PySpark RDD    │   │  - Map-reduce     │   │ - ML distribué │   │
│  │  - Sauv. JSON     │   │  - Visualisation  │   │ - Tests        │   │
│  └────────┬──────────┘   └────────┬──────────┘   └───────┬────────┘   │
│           │                       │                       │            │
│           ▼                       ▼                       ▼            │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │                    Volume Docker partagé                      │     │
│  │  /shared_data/                                                │     │
│  │  ├── images/               # Images téléchargées              │     │
│  │  ├── images_metadata.json  # Du conteneur 1                   │     │
│  │  ├── images_labels.json    # Du conteneur 2                   │     │
│  │  ├── users.json            # Du conteneur 2                   │     │
│  │  ├── visualisations.png    # Du conteneur 2                   │     │
│  │  └── recommendations.json  # Du conteneur 3                   │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## 🔑 Utilisation de PySpark

Chaque conteneur utilise PySpark pour distribuer le traitement :

### Conteneur 1 : Acquisition
- **Map** : Télécharger et traiter chaque image en parallèle
- **Filter** : Retirer les images corrompues
- **Collect** : Récupérer les métadonnées

### Conteneur 2 : Analysis
- **Map** : Extraire les couleurs (KMeans) en parallèle
- **Map** : Construire les profils utilisateurs en parallèle
- **FlatMap + ReduceByKey** : Agréger les tags globaux

### Conteneur 3 : Recommendation
- **Map** : Calculer les scores de similarité en parallèle
- **Filter** : Exclure les favoris
- **SortBy** : Trier par score décroissant
- **Take** : Prendre le top N

## 📦 Prérequis

- Docker Desktop installé et démarré
- Docker Compose (inclus avec Docker Desktop)
- Clé API Unsplash (gratuite)

## 🚀 Installation et Exécution

### 1. Configuration de la clé API

Créer un fichier `.env` dans le dossier `partie2/` :

```bash
cd partie2
cp .env.example .env
```

Éditer le fichier `.env` et remplacer `your_access_key_here` par votre clé API Unsplash.

**⚠️ Important** : Ne jamais committer le fichier `.env` dans Git !

### 2. Construire et exécuter tous les conteneurs

```bash
# Construire et exécuter en séquence
docker compose up --build

# Ou en mode détaché (en arrière-plan)
docker compose up --build -d
```

Les conteneurs s'exécutent dans l'ordre :
1. `acquisition` → télécharge ~120 images (~5-10 min)
2. `analysis` → étiquette, analyse et visualise (~5-10 min)
3. `recommendation` → génère recommandations et teste (~2-5 min)

**Temps total estimé** : 15-25 minutes

### 3. Vérifier les logs

```bash
# Voir les logs en temps réel
docker compose logs -f

# Logs d'un conteneur spécifique
docker compose logs acquisition
docker compose logs analysis
docker compose logs recommendation
```

### 4. Vérifier les résultats

```bash
# Lister les fichiers générés dans le volume
docker compose run --rm recommendation ls -lh /shared_data/

# Afficher le contenu d'un fichier JSON
docker compose run --rm recommendation cat /shared_data/recommendations.json
```

### 5. Copier les résultats vers votre machine

```bash
# Copier tous les fichiers du volume
docker cp projet_recommendation:/shared_data ./output

# Ou copier un fichier spécifique
docker cp projet_recommendation:/shared_data/recommendations.json ./recommendations.json
```

### 6. Nettoyer

```bash
# Arrêter et supprimer les conteneurs
docker compose down

# Supprimer aussi les volumes (⚠️ supprime toutes les données)
docker compose down -v

# Supprimer les images Docker
docker compose down --rmi all
```

## 📂 Structure du projet

```
partie2/
├── docker-compose.yml          # Orchestration des conteneurs
├── .env.example                # Template pour les variables d'environnement
├── .env                        # Vos clés API (à créer, ne pas committer)
├── README.md                   # Ce fichier
│
├── acquisition/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── acquisition.py          # Script avec PySpark
│
├── analysis/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── analysis.py             # Script avec PySpark
│
└── recommendation/
    ├── Dockerfile
    ├── requirements.txt
    └── recommendation.py       # Script avec PySpark
```

## 🧪 Tests

Les tests sont automatiquement exécutés par le conteneur `recommendation` :

- **Test 1** : Intégrité des données
- **Test 2** : Qualité des recommandations

Si tous les tests passent, vous verrez :
```
================================================================================
🎉 TOUS LES TESTS RÉUSSIS !
================================================================================
```

## 🐛 Dépannage

### Erreur : "Cannot connect to Docker daemon"
- Vérifiez que Docker Desktop est lancé

### Erreur : "unauthorized" (Unsplash API)
- Vérifiez votre clé API dans le fichier `.env`
- Assurez-vous que le fichier `.env` est dans `partie2/`

### Conteneur bloqué ou très lent
- L'acquisition peut prendre du temps (~120 images)
- Vérifiez les logs : `docker compose logs -f`

### Manque de mémoire
- Augmentez la mémoire allouée à Docker Desktop (Settings → Resources)
- Recommandé : au moins 4 GB de RAM

### Reconstruire un conteneur spécifique
```bash
docker compose build acquisition
docker compose up acquisition
```

## 📊 Fichiers générés

Après exécution complète, le volume `shared_data` contient :

| Fichier | Description | Taille estimée |
|---------|-------------|----------------|
| `images/` | ~120 images JPEG | ~25 MB |
| `images_metadata.json` | Métadonnées des images | ~250 KB |
| `images_labels.json` | Labels et annotations | ~120 KB |
| `users.json` | Profils utilisateurs | ~10 KB |
| `visualisations.png` | 9 graphiques | ~200 KB |
| `recommendations.json` | Recommandations pour 5 utilisateurs | ~5 KB |

## 🎯 Comparaison Partie 1 vs Partie 2

| Aspect | Partie 1 (Notebook) | Partie 2 (Docker + PySpark) |
|--------|---------------------|------------------------------|
| **Architecture** | Monolithique | Distribuée (3 conteneurs) |
| **Traitement** | Séquentiel (boucles) | Parallèle (map-reduce) |
| **Déploiement** | Local uniquement | Conteneurisé, portable |
| **Scalabilité** | Limitée | Haute (multi-workers) |
| **Reproductibilité** | Dépend de l'environnement | Garantie (Docker) |

## 🔍 Exemples de commandes map-reduce

### Acquisition : Téléchargement parallèle
```python
images_rdd = sc.parallelize(all_images_data)
metadata_rdd = images_rdd.map(process_image)  # Parallèle !
results = metadata_rdd.filter(lambda x: x[0] is not None).collect()
```

### Analysis : Extraction de couleurs parallèle
```python
metadata_items = list(metadata.items())
images_rdd = sc.parallelize(metadata_items)
labels_rdd = images_rdd.map(process_image_labels)  # Parallèle !
labels = dict(labels_rdd.collect())
```

### Recommendation : Calcul de scores parallèle
```python
items_rdd = sc.parallelize(items)
scores_rdd = items_rdd.map(compute_recommendation_score)  # Parallèle !
recommendations = scores_rdd.sortBy(lambda x: x[1], ascending=False).take(5)
```

## 📝 Notes importantes

1. **Clé API** : Le fichier `.env` contient des secrets et ne doit JAMAIS être commité
2. **Volume** : Les données persistent entre les exécutions sauf si vous faites `docker compose down -v`
3. **Ordre** : Les conteneurs doivent s'exécuter dans l'ordre (acquisition → analysis → recommendation)
4. **Performance** : PySpark améliore les performances sur de gros volumes de données

## 🎓 Concepts clés

- **Docker** : Conteneurisation pour isolation et portabilité
- **Docker Compose** : Orchestration de multiples conteneurs
- **PySpark** : Traitement distribué avec map-reduce
- **Volumes** : Partage de données entre conteneurs
- **RDD** : Resilient Distributed Dataset (structure de base PySpark)

## 📚 Références

- [Documentation Docker](https://docs.docker.com/)
- [Documentation Docker Compose](https://docs.docker.com/compose/)
- [Documentation PySpark](https://spark.apache.org/docs/latest/api/python/)
- [Unsplash API](https://unsplash.com/documentation)

---

**Auteurs** : BONNET & DURANO  
**Date** : Février 2026  
**Cours** : Données Massives
