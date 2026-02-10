# TP5 : Apache Spark pour le traitement massif des donnees

Cette seance de TP introduit Apache Spark, un framework distribue puissant pour le traitement de donnees a grande echelle. Vous apprendrez les RDD, les DataFrames, Spark SQL et les techniques d'optimisation des performances.

## Prerequis

- Docker et Docker Compose installes
- Connaissances de base en programmation Python
- TP4 termine (calcul parallele et distribue)

## Demarrage rapide

### Option 1 : Utiliser Docker Compose (recommande)

1. **Construire et demarrer le conteneur :**

   ```bash
   docker-compose up --build
   ```
   
   Note : Evitez `--no-cache` sauf si vous avez besoin d'une reconstruction propre. Spark est volumineux et Docker reutilise la couche de telechargement lors des builds suivants.

2. **Acceder a Jupyter Lab :**

   Ouvrez votre navigateur et allez a :
   ```
   http://localhost:8888
   ```

3. **Acceder a l'UI Spark (lors de l'execution des jobs) :**

   ```
   http://localhost:4040
   ```

4. **Ouvrir le notebook :**

   Dans Jupyter Lab, ouvrez `/app/notebooks/tp5.ipynb`.

5. **Arreter le conteneur :**

   ```bash
   docker-compose down
   ```

### Option 2 : Utiliser Docker directement

1. **Construire l'image :**

   ```bash
   docker build -t tp5-spark .
   ```

2. **Executer le conteneur avec les volumes :**

   ```bash
   docker run -it --rm \
     -p 8888:8888 \
     -p 4040:4040 \
     --shm-size=2g \
     -v $(pwd)/tp5.ipynb:/app/notebooks/tp5.ipynb \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/output:/app/output \
     tp5-spark
   ```

3. **Acceder a Jupyter Lab :**

   Ouvrez `http://localhost:8888` dans votre navigateur.

## Structure du dossier

```
TP5/
|- Dockerfile           # Definition de l'image Docker avec Java et Spark
|- docker-compose.yml   # Configuration Docker Compose
|- requirements.txt     # Dependances Python
|- README.md            # Ce fichier
|- tp5.ipynb            # Notebook principal
|- data/                # Fichiers de donnees (volume monte)
|- output/              # Fichiers de sortie (volume monte)
```

## Apercu des exercices

| Exercice | Sujet | Difficulte |
|----------|-------|------------|
| 1 | Architecture Spark et bases des RDD | 1 |
| 2 | Transformations et actions RDD | 1 |
| 3 | DataFrames et gestion des schemas | 2 |
| 4 | Spark SQL et requetes complexes | 2 |
| 5 | Joins, fonctions fenetres et aggregations | 2 |
| 6 | Partitionnement, cache et optimisation | 3 |
| 7 | Traitement de jeux de donnees a grande echelle | 3 |

## Composants installes

L'image Docker inclut :

### Java
- **OpenJDK 17** : requis pour Apache Spark

### Packages Python
- **Jupyter** : JupyterLab pour un environnement interactif
- **NumPy/Pandas** : calcul numerique et manipulation de donnees
- **Matplotlib** : visualisation de donnees
- **PyArrow** : conversion efficace Spark/Pandas
- **psutil** : utilitaires systeme et processus

## Utilisation des volumes

### Volume data

Le dossier `data/` est monte vers `/app/data` dans le conteneur. En plus, le dossier de donnees partagees est monte vers `/app/shared_data`.

```bash
# Creer le dossier data
mkdir -p data

# Copier des fichiers de donnees
cp vos_donnees.csv data/
```

### Volume output

Le dossier `output/` est monte vers `/app/output` dans le conteneur. Les resultats seront enregistres ici :

```python
# Dans votre notebook - enregistrer en Parquet
df.write.parquet('/app/output/results.parquet')

# Enregistrer en CSV
df.write.csv('/app/output/results.csv')
```

## Configuration Spark

### Parametres memoire

La configuration par defaut alloue 2 Go pour la memoire du driver et de l'executor. Modifiez dans `docker-compose.yml` :

```yaml
environment:
  - SPARK_DRIVER_MEMORY=4g
  - SPARK_EXECUTOR_MEMORY=4g
```

### Memoire partagee

Spark requiert une memoire partagee suffisante. Par defaut, c'est 2 Go. Augmentez si necessaire :

```yaml
shm_size: '4gb'
```

### Acceder a l'UI Spark

Lors de l'execution de jobs Spark, l'UI est disponible a :
```
http://localhost:4040
```

Cela fournit des informations sur :
- Jobs actifs et termines
- Stages et taches
- Stockage (RDD/DataFrames en cache)
- Configuration de l'environnement
- Executors

## Depannage

### Port deja utilise

Si le port 8888 ou 4040 est deja utilise, modifiez `docker-compose.yml` :

```yaml
ports:
  - "8889:8888"  # Utiliser le port 8889 pour Jupyter
  - "4041:4040"  # Utiliser le port 4041 pour l'UI Spark
```

### Problemes de permissions sous Linux

Si vous rencontrez des problemes de permissions avec les volumes montes :

```bash
# Definir les bonnes permissions
chmod -R 777 data output
```

Ou lancez avec votre identifiant utilisateur :

```bash
docker run -it --rm \
  -p 8888:8888 \
  -p 4040:4040 \
  -u $(id -u):$(id -g) \
  -v $(pwd)/tp5.ipynb:/app/notebooks/tp5.ipynb \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/output:/app/output \
  tp5-spark
```

### Problemes de memoire

Spark peut etre gourmand en memoire. Si vous rencontrez des erreurs de memoire :

1. **Augmenter la memoire Docker :**

   Dans Docker Desktop, allez dans Settings > Resources > Memory et augmentez la limite a au moins 4 Go.

2. **Augmenter la memoire du conteneur :**

   ```yaml
   services:
     jupyter-spark:
       ...
       deploy:
         resources:
           limits:
             memory: 6G
   ```

3. **Reduire la taille des donnees pour les exercices :**

   Quand vous travaillez avec de gros jeux de donnees, commencez par des echantillons plus petits :

   ```python
   # Echantillonner 10 % des donnees
   sampled_df = large_df.sample(fraction=0.1)
   ```

### Java introuvable

Si vous voyez des erreurs Java, verifiez que Java est installe :

```bash
docker-compose exec jupyter-spark java -version
```

### Probleme de session Spark

Si SparkContext est deja lance :

```python
# Arreter le contexte existant
sc.stop()

# Ou obtenir une session existante
spark = SparkSession.builder.getOrCreate()
```

### Plantages du kernel

Si le kernel Jupyter plante pendant les operations Spark :

1. Redemarrez le kernel depuis l'interface Jupyter
2. Reduisez la quantite de donnees traitee
3. Augmentez l'allocation memoire
4. Utilisez `persist()` avec le niveau de stockage DISK pour de gros datasets

## Lancer des tests

Pour verifier que l'environnement est correctement configure :

```bash
# Entrer dans le conteneur
docker-compose exec jupyter-spark bash

# Lancer un test rapide
python -c "
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName('test').getOrCreate()
print(f'Spark Version: {spark.version}')
print(f'Java Home: $(echo \$JAVA_HOME)')
df = spark.range(10)
print(f'Test DataFrame count: {df.count()}')
spark.stop()
print('PySpark fonctionne correctement !')
"
```

## Conseils de performance

1. **Utiliser les DataFrames plutot que les RDD** quand c'est possible pour une meilleure optimisation
2. **Mettre en cache** les resultats intermediaires utilises plusieurs fois
3. **Utiliser des formats colonnaires** (Parquet/ORC) pour les gros datasets
4. **Partitionner les donnees** par colonnes filtrees frequemment
5. **Utiliser les broadcast joins** pour les petites tables de jointure
6. **Surveiller via l'UI Spark** pour identifier les goulots d'etranglement

## Ressources supplementaires

- [Documentation Apache Spark](https://spark.apache.org/docs/latest/)
- [Reference API PySpark](https://spark.apache.org/docs/latest/api/python/)
- [Guide Spark SQL](https://spark.apache.org/docs/latest/sql-programming-guide.html)
- [Optimisation des performances Spark](https://spark.apache.org/docs/latest/tuning.html)

## Licence

Ce TP fait partie du cours TDM (Traitement de Donnees Massives).
