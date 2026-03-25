## Projet partie 2

L'objectif de la partie 2 est de transformer votre projet de la partie 1 en une **application distribuee et conteneurisee** utilisant Docker (TP 6) et PySpark (TP 5). Vous allez decomposer votre notebook monolithique en services independants et scalables qui communiquent via des volumes de donnees partages.

### Vue d'ensemble

Dans la partie 1, l'ensemble de votre pipeline (collecte de donnees, etiquetage, analyse, visualisation, recommandation) s'execute dans un seul notebook Jupyter. Dans la partie 2, vous allez :

1. **Identifier les taches independantes** de votre pipeline de la partie 1
2. **Remplacer les boucles sequentielles par des operations PySpark** (map-reduce, expressions lambda)
3. **Empaqueter chaque tache dans un conteneur Docker** avec son propre Dockerfile
4. **Utiliser des volumes Docker** pour partager les donnees (JSON, CSV, images) entre les conteneurs
5. **Orchestrer le tout** avec `docker-compose`

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        docker-compose.yml                            │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐   ┌──────────────────┐   ┌────────────────┐   │
│  │  Conteneur 1 :    │   │  Conteneur 2 :    │   │  Conteneur 3 : │   │
│  │  Acquisition      │──▶│  Analyse          │──▶│ Recommandation │   │
│  │  de donnees       │   │  & Etiquetage     │   │                │   │
│  │  - Telecharger    │   │  - Extraction     │   │ - Profil util. │   │
│  │  - Extraire EXIF  │   │  - Regroupement   │   │ - Recommander  │   │
│  │  - Sauv. metadon. │   │  - Profils util.  │   │ - Visualiser   │   │
│  └────────┬──────────┘   └────────┬──────────┘   └───────┬────────┘   │
│           │                       │                       │            │
│           ▼                       ▼                       ▼            │
│  ┌──────────────────────────────────────────────────────────────┐     │
│  │                    Volume Docker partage                      │     │
│  │  /shared_data/                                                │     │
│  │  ├── images/               # Images telechargees              │     │
│  │  ├── images_metadata.json  # Du conteneur 1                   │     │
│  │  ├── images_labels.json    # Du conteneur 2                   │     │
│  │  ├── users.json            # Du conteneur 2                   │     │
│  │  └── recommendations.json  # Du conteneur 3                   │     │
│  └──────────────────────────────────────────────────────────────┘     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Etape 1 : Identifier les taches independantes

Examinez votre notebook de la partie 1 et decomposez-le en au moins **trois taches independantes**. Decomposition suggeree :

| Conteneur | Taches de la partie 1 couvertes | Entree | Sortie |
|-----------|--------------------------------|--------|--------|
| **Acquisition de donnees** | Tache 1 (Collecte de donnees) | URLs des sources d'images | `images/`, `images_metadata.json` |
| **Analyse & Etiquetage** | Tache 2 (Etiquetage), Tache 3 (Analyse), Tache 4 (Visualisation) | `images/`, `images_metadata.json` | `images_labels.json`, `users.json`, visualisations PNG |
| **Recommandation** | Tache 5 (Recommandation), Tache 6 (Tests) | `images_labels.json`, `users.json` | `recommendations.json`, resultats de tests |

Vous pouvez decomposer davantage en plus de conteneurs (par exemple, des conteneurs separes pour l'etiquetage, l'analyse et la visualisation).

### Etape 2 : Remplacer les boucles par des operations PySpark

Pour chaque conteneur, identifiez les **boucles sequentielles** de votre code de la partie 1 et reecrivez-les en utilisant les operations distribuees de PySpark :

#### Exemple : Extraction de couleurs (de la tache 2)

**Partie 1 (boucle sequentielle) :**
```python
# Traitement des images une par une dans une boucle
results = []
for image_file in image_files:
    img = load_image(image_file)
    colors = extract_colors(img)
    results.append({"file": image_file, "colors": colors})
```

**Partie 2 (PySpark) :**
```python
from pyspark import SparkContext

sc = SparkContext("local[*]", "ExtractionCouleurs")

# Distribuer la liste des fichiers images sur les workers
images_rdd = sc.parallelize(image_files)

# Map : appliquer l'extraction de couleurs a chaque image en parallele
colors_rdd = images_rdd.map(lambda f: (f, extract_colors(load_image(f))))

# Collecter les resultats
results = colors_rdd.collect()
```

#### Exemple : Construction du profil utilisateur (de la tache 3)

**Partie 1 (boucle sequentielle) :**
```python
# Construction des profils un utilisateur a la fois
profiles = []
for user in users:
    fav_colors = []
    for img in user["favorites"]:
        fav_colors.extend(labels[img]["color_names"])
    most_common = Counter(fav_colors).most_common(3)
    profiles.append({"user": user["id"], "colors": most_common})
```

**Partie 2 (PySpark) :**
```python
# Distribuer le traitement des utilisateurs avec les RDD
users_rdd = sc.parallelize(users)

# Map chaque utilisateur vers son profil en utilisant lambda
profiles_rdd = users_rdd.map(lambda u: build_user_profile(u, labels))

# Utiliser reduceByKey pour agreger les comptages de tags de tous les utilisateurs
all_tags_rdd = users_rdd.flatMap(lambda u: get_user_tags(u, labels)) \
                        .map(lambda tag: (tag, 1)) \
                        .reduceByKey(lambda a, b: a + b)

top_tags = all_tags_rdd.sortBy(lambda x: x[1], ascending=False).take(10)
```

#### Exemple : Calcul de score de recommandation (de la tache 5)

**Partie 1 (boucle sequentielle) :**
```python
# Notation des images pour un utilisateur de maniere sequentielle
scores = []
for img in all_images:
    score = compute_similarity(user_profile, image_features[img])
    scores.append((img, score))
scores.sort(key=lambda x: x[1], reverse=True)
```

**Partie 2 (PySpark) :**
```python
# Distribuer le calcul de scores sur les workers
images_rdd = sc.parallelize(all_images)

# Map : calculer le score de similarite en parallele
scores_rdd = images_rdd.map(lambda img: (img, compute_similarity(user_profile, image_features[img])))

# Trier et prendre les meilleures recommandations
recommendations = scores_rdd.sortBy(lambda x: x[1], ascending=False).take(10)
```

### Etape 3 : Creer les conteneurs Docker

Chaque conteneur necessite :
- **Dockerfile** avec les dependances requises (Python, PySpark, bibliotheques)
- **Script(s) Python** implementant la tache avec les operations PySpark
- **requirements.txt** listant les dependances Python

Referez-vous aux exemples du TP 6 pour la structure des conteneurs :
- Exemple `SharedVolume/` pour la communication via volumes entre conteneurs
- Exemple `AppDB/` pour l'orchestration multi-conteneurs

#### Exemple de Dockerfile pour le conteneur d'analyse de donnees :

```dockerfile
FROM python:3.10-slim

# Installer Java (requis pour PySpark)
RUN apt-get update && apt-get install -y openjdk-17-jdk-headless && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY analyze.py .
CMD ["python", "analyze.py"]
```

#### Exemple de requirements.txt :
```
pyspark==3.5.3
numpy==1.26.4
Pillow==10.4.0
```

### Etape 4 : Utiliser les volumes Docker pour le partage de donnees

Utilisez un volume Docker partage pour que les conteneurs puissent lire et ecrire des fichiers de donnees (JSON, CSV, images). Chaque conteneur lit ses entrees depuis le volume partage et ecrit ses sorties dans le volume partage.

#### Exemple de docker-compose.yml :

```yaml
version: "3.8"

services:
  acquisition:
    build: ./acquisition
    volumes:
      - shared_data:/shared_data
    environment:
      - OUTPUT_DIR=/shared_data

  analysis:
    build: ./analysis
    depends_on:
      acquisition:
        condition: service_completed_successfully
    volumes:
      - shared_data:/shared_data
    environment:
      - INPUT_DIR=/shared_data
      - OUTPUT_DIR=/shared_data

  recommendation:
    build: ./recommendation
    depends_on:
      analysis:
        condition: service_completed_successfully
    volumes:
      - shared_data:/shared_data
    environment:
      - INPUT_DIR=/shared_data
      - OUTPUT_DIR=/shared_data

volumes:
  shared_data:
```

### Etape 5 : Executer et verifier

```bash
# Construire et executer tous les conteneurs en sequence
docker compose up --build

# Verifier le volume partage pour les sorties
docker compose run --rm recommendation ls /shared_data/
```

### Evaluation (Partie 2)

| Criteres | Points | Details |
|----------|--------|---------|
| Decomposition en taches | 25% | Separation claire en 3+ conteneurs independants, chacun avec des entrees/sorties bien definies |
| Volumes Docker | 25% | Utilisation correcte des volumes partages pour passer les fichiers JSON, CSV et images entre conteneurs |
| Map-reduce et expressions lambda | 25% | Boucles sequentielles de la partie 1 remplacees par des operations PySpark `map`, `flatMap`, `filter`, `reduceByKey` et des expressions lambda |
| Utilisation de PySpark | 25% | Utilisation correcte de SparkContext, operations RDD et traitement distribue dans au moins 2 conteneurs |

**Remarque** : Vous pouvez consulter des [exemples supplementaires](../../examples) de conteneurs Docker ainsi que les exemples du TP 5 et du TP 6.