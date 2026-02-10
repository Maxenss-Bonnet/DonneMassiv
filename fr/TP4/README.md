# TP4 : Fondamentaux du calcul parallele et distribue

Cette seance de TP couvre des concepts de calcul parallele et distribue en Python, y compris la programmation fonctionnelle, le multiprocessing et l'optimisation des performances.

## Prerequis

- Docker et Docker Compose installes
- Connaissances de base en programmation Python

## Demarrage rapide

### Option 1 : Utiliser Docker Compose (recommande)

1. **Construire et demarrer le conteneur :**

   ```bash
   docker-compose up --build
   ```

2. **Acceder a Jupyter Lab :**

   Ouvrez votre navigateur et allez a :
   ```
   http://localhost:8888
   ```

3. **Ouvrir le notebook :**

   Dans Jupyter Lab, ouvrez `/app/notebooks/tp4.ipynb`.

4. **Arreter le conteneur :**

   ```bash
   docker-compose down
   ```

### Option 2 : Utiliser Docker directement

1. **Construire l'image :**

   ```bash
   docker build -t tp4 .
   ```

2. **Executer le conteneur avec les volumes :**

   ```bash
   docker run -it --rm \
     -p 8888:8888 \
     -v $(pwd)/tp4.ipynb:/app/notebooks/tp4.ipynb \
     -v $(pwd)/data:/app/data \
     -v $(pwd)/output:/app/output \
     tp4
   ```

3. **Acceder a Jupyter Lab :**

   Ouvrez `http://localhost:8888` dans votre navigateur.

## Structure du dossier

```
TP4/
|- Dockerfile           # Definition de l'image Docker
|- docker-compose.yml   # Configuration Docker Compose
|- requirements.txt     # Dependances Python
|- README.md            # Ce fichier
|- tp4.ipynb            # Notebook principal
|- data/                # Fichiers de donnees (volume monte)
|- output/              # Fichiers de sortie (volume monte)
```

## Apercu des exercices

| Exercice | Sujet | Difficulte |
|----------|-------|------------|
| 1 | Programmation fonctionnelle (filter, map, reduce) | 1 |
| 2 | Expressions lambda et fonctions d'ordre superieur | 1 |
| 3 | Generateurs et iterateurs | 2 |
| 4 | Introduction au multiprocessing | 2 |
| 5 | Communication entre processus (queues et pipes) | 2 |
| 6 | concurrent.futures et patterns asynchrones | 3 |
| 7 | Benchmarks de performance et optimisation | 3 |

## Packages installes

L'image Docker inclut :

- **Jupyter** : JupyterLab pour un environnement interactif
- **NumPy/Pandas** : Calcul numerique et manipulation de donnees
- **Matplotlib** : Visualisation de donnees
- **Dask** : Calcul parallele avec ordonnancement de taches
- **Joblib** : Pipelining leger et calcul parallele
- **memory-profiler** : Profilage de l'utilisation memoire
- **psutil** : Utilitaires systeme et processus

## Utilisation des volumes

### Volume data

Le dossier `data/` est monte vers `/app/data` dans le conteneur. Placez vos fichiers d'entree ici :

```bash
# Creer le dossier data
mkdir -p data

# Copier des fichiers de donnees
cp vos_donnees.csv data/
```

### Volume output

Le dossier `output/` est monte vers `/app/output` dans le conteneur. Les resultats seront enregistres ici :

```python
# Dans votre notebook
import pandas as pd

results = pd.DataFrame(...)
results.to_csv('/app/output/results.csv')
```

## Depannage

### Port deja utilise

Si le port 8888 est deja utilise, modifiez `docker-compose.yml` :

```yaml
ports:
  - "8889:8888"  # Utiliser le port 8889 a la place
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
  -u $(id -u):$(id -g) \
  -v $(pwd)/tp4.ipynb:/app/notebooks/tp4.ipynb \
  -v $(pwd)/data:/app/data \
  tp4
```

### Problemes de memoire avec le multiprocessing

Le notebook inclut des exercices avec le multiprocessing. Si vous rencontrez des problemes de memoire :

1. **Augmenter la memoire Docker :**

   Dans Docker Desktop, allez dans Settings > Resources > Memory et augmentez la limite.

2. **Ou ajouter des limites de memoire a docker-compose.yml :**

   ```yaml
   services:
     jupyter:
       ...
       deploy:
         resources:
           limits:
             memory: 4G
   ```

### Plantages du kernel

Si le kernel Jupyter plante pendant les exercices de multiprocessing :

1. Redemarrez le kernel depuis l'interface Jupyter
2. Executez les cellules une par une au lieu de "Run All"
3. Reduisez le nombre de processus dans les appels a Pool()

## Configuration CPU pour le multiprocessing

Par defaut, les conteneurs Docker ont acces a tous les CPU de l'hote. Pour limiter l'acces CPU :

```yaml
# Dans docker-compose.yml
services:
  jupyter:
    ...
    deploy:
      resources:
        limits:
          cpus: '4'  # Limiter a 4 CPU
```

## Lancer des tests

Pour verifier que l'environnement est correctement configure :

```bash
# Entrer dans le conteneur
docker-compose exec jupyter bash

# Lancer un test rapide
python -c "
import multiprocessing
import numpy as np
import pandas as pd
print(f'CPUs available: {multiprocessing.cpu_count()}')
print(f'NumPy version: {np.__version__}')
print(f'Pandas version: {pd.__version__}')
print('All dependencies installed correctly!')
"
```

## Ressources supplementaires

- [Documentation multiprocessing Python](https://docs.python.org/3/library/multiprocessing.html)
- [Documentation concurrent.futures](https://docs.python.org/3/library/concurrent.futures.html)
- [Documentation Dask](https://docs.dask.org/)
- [Documentation Jupyter](https://jupyter.org/documentation)

## Licence

Ce TP fait partie du cours TDM (Traitement de Donnees Massives).
