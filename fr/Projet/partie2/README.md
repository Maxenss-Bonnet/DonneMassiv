# Partie 2 : Système de Recommandation Distribué

## 📋 Description

Cette partie transforme le notebook monolithique de la partie 1 en une **application distribuée et conteneurisée** utilisant Docker et PySpark.

Le système est décomposé en **4 conteneurs indépendants** qui communiquent via un volume Docker partagé :

1. **Conteneur Acquisition** : Collecte des images depuis Unsplash API avec traitement parallèle (PySpark)
2. **Conteneur Analysis** : Étiquetage des images et analyse des profils utilisateurs (PySpark)
3. **Conteneur Visualization** : Génération des graphiques statistiques (matplotlib/pandas)
4. **Conteneur Recommendation** : Système de recommandation distribué (PySpark + MLlib) et tests

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

3 des 4 conteneurs utilisent PySpark pour distribuer le traitement
(le 4ᵉ, `visualization`, n'utilise que matplotlib/pandas) :

### Conteneur 1 : Acquisition
- **mapPartitions** : Télécharger et extraire EXIF par partition (overhead amorti)
- **Filter** : Retirer les images corrompues
- **Collect** : Récupérer les métadonnées

### Conteneur 2 : Analysis
- **mapPartitions** : Extraire les couleurs (KMeans) par partition
- **Broadcast(`labels`)** : Diffusion une seule fois sur chaque worker
- **FlatMap + ReduceByKey** : Agréger les tags globaux
- **Map** : Construire les profils utilisateurs en parallèle (avec broadcast)

### Conteneur 4 : Recommendation
- **Modèle global MLlib** : 1 seul Random Forest sur (user × image) → favori
  (au lieu de N modèles par user — vrai scaling vers 1M+ utilisateurs)
- **Cross-join Spark** : génération distribuée des paires (user, image)
- **Negative sampling** : équilibrage des classes (favoris rares ~10 %)
- **1 seul `model.transform()`** distribué pour TOUS les utilisateurs
- **Broadcast** : favoris, labels, profils utilisateurs
- **Repartition** : équilibrage explicite du scoring
- **groupByKey + mapValues** : Top-N par utilisateur

## 🚀 Optimisations scalabilité (1M+ utilisateurs)

Les 3 conteneurs Spark intègrent des optimisations pour rester performants
à grande échelle :

| Optimisation | Conteneur(s) | Effet |
|--------------|--------------|-------|
| **Broadcast variables** | analysis, recommendation | Évite la sérialisation de `labels`/profils dans la closure de chaque task |
| **Modèle global MLlib** | recommendation | 1 seul `fit()` au lieu de N — scaling linéaire en lignes, pas en utilisateurs |
| **Cross-join Spark** | recommendation | Génération distribuée des paires (user, image) — zéro RAM driver |
| **Negative sampling** | recommendation | Équilibrage des classes (favoris rares) — évite le biais "tout-zéro" |
| **mapPartitions** | acquisition, analysis | Amortit l'overhead Python<->JVM par partition (gain 10-30 %) |
| **repartition() explicite** | tous | Équilibrage des tasks, contrôle du parallélisme |
| **SparkConf paramétrable** | tous | `SPARK_PARALLELISM`, `SPARK_DRIVER_MEMORY`, `SPARK_EXECUTOR_MEMORY` |

### Variables de tuning (override via `.env`)

```bash
# Adapte selon la machine cible
SPARK_PARALLELISM=200          # Nombre de partitions par défaut
SPARK_DRIVER_MEMORY=2g         # RAM driver Spark
SPARK_EXECUTOR_MEMORY=2g       # RAM executor Spark

# Hyperparamètres MLlib
RF_NUM_TREES=100               # Nombre d'arbres Random Forest
RF_MAX_DEPTH=10                # Profondeur max des arbres
NEG_POS_RATIO=3                # Ratio négatifs/positifs (negative sampling)
```

Sur une machine 16 cœurs / 32 Go : `SPARK_PARALLELISM=400`,
`SPARK_DRIVER_MEMORY=8g`, `SPARK_EXECUTOR_MEMORY=8g` est un bon point de départ.

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
│   └── acquisition.py          # Script avec PySpark (mapPartitions, filter)
│
├── analysis/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── analysis.py             # Script avec PySpark (broadcast, flatMap, reduceByKey)
│
├── visualization/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── visualization.py        # Script matplotlib/pandas (graphiques)
│
└── recommendation/
    ├── Dockerfile
    ├── requirements.txt
    └── recommendation.py       # Script avec PySpark + MLlib (RandomForest distribué)
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

### Acquisition : Téléchargement parallèle (mapPartitions)
```python
images_rdd = sc.parallelize(all_images_data, numSlices=n_partitions)
metadata_rdd = images_rdd.mapPartitions(process_image_partition)  # Parallèle, overhead amorti
results = metadata_rdd.filter(validate_image).collect()
```

### Analysis : Extraction couleurs (mapPartitions) + profils (broadcast)
```python
# Étiquetage par partition
images_rdd = sc.parallelize(metadata_items, numSlices=n_partitions)
labels_rdd = images_rdd.mapPartitions(process_image_labels_partition)
labels = dict(labels_rdd.filter(lambda x: x[1] is not None).collect())

# Broadcast pour les profils utilisateurs
labels_bc = sc.broadcast(labels)
profiles_rdd = users_rdd.map(lambda x: build_user_profile_broadcast(x, labels_bc.value))
```

### Recommendation : Modèle global MLlib + crossJoin distribué
```python
# 1. Cross-join distribué : génération de toutes les paires (user, image)
all_pairs = users_df.crossJoin(images_df)

# 2. Labellisation distribuée + negative sampling pour équilibrer les classes
labeled = all_pairs.withColumn('label', label_udf(col('user_id'), col('filename')))
pos_df = labeled.filter(col('label') == 1)
neg_sampled = labeled.filter(col('label') == 0).sample(False, sample_ratio, seed=42)
training_df = pos_df.union(neg_sampled)

# 3. UN SEUL fit() global (au lieu de N pour N utilisateurs)
pipeline = Pipeline(stages=indexers + [assembler, rf])
model = pipeline.fit(training_df)  # 1 modèle pour TOUS les users !

# 4. UN SEUL transform() global sur toutes les paires candidates
predictions = model.transform(candidates_df)

# 5. groupByKey + mapValues → top-N par utilisateur (distribué)
recommendations = (
    predictions.rdd.map(build_recommendation)
               .groupByKey()
               .mapValues(lambda recs: sorted(recs, key=lambda r: r[1], reverse=True)[:5])
               .collectAsMap()
)
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
