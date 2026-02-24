# Partie 1 : Système de Recommandation d'Images — Notebook Jupyter

## 📋 Description

Cette partie implémente l'intégralité du pipeline de recommandation d'images dans un **notebook Jupyter monolithique** :

1. **Collecte de données** : 120 images sous licence Unsplash collectées via l'API Unsplash
2. **Étiquetage et annotation** : Extraction de couleurs (KMeans), orientation, taille, tags
3. **Analyse des utilisateurs** : 5 profils simulés avec construction des préférences
4. **Visualisation** : 9 graphiques (orientation, taille, format, couleurs, tags, etc.)
5. **Système de recommandation** : RandomForestClassifier (filtrage basé sur le contenu)
6. **Tests** : 3 suites de tests (intégrité des données, fonctionnel, qualité des recommandations)

## 📦 Prérequis

- Python 3.10+
- Clé API Unsplash (gratuite sur [unsplash.com/developers](https://unsplash.com/developers))
- Jupyter Lab ou VS Code avec l'extension Jupyter

## 🚀 Installation

### 1. Installer les dépendances

```powershell
cd "c:\Users\maxen\.vscodeProject\DonneMassiv\fr\Projet\partie1"
pip install -r requirements.txt
```

### 2. Configurer la clé API

```powershell
# Copier le template .env
Copy-Item .env.example .env
```

Éditer le fichier `.env` et remplacer `your_access_key_here` par votre clé API Unsplash.

**⚠️ Important** : Ne jamais committer le fichier `.env` dans Git !

### 3. Ouvrir le notebook

```powershell
# Avec Jupyter Lab
jupyter lab BONNET_DURANO.ipynb

# Ou ouvrir directement dans VS Code
code BONNET_DURANO.ipynb
```

## ▶️ Exécution

1. **Ouvrir** `BONNET_DURANO.ipynb` dans Jupyter
2. **Kernel > Restart & Run All** pour exécuter toutes les cellules dans l'ordre
3. Vérifier que toutes les cellules se terminent sans erreur

**Temps d'exécution estimé** : 10–15 minutes (dont ~5 min pour la collecte d'images via API)

## 📂 Structure du dossier

```
partie1/
├── BONNET_DURANO.ipynb     # Notebook principal (6 tâches)
├── requirements.txt         # Dépendances Python
├── README.md                # Ce fichier
├── COMMANDES.md             # Aide-mémoire des commandes
├── .env.example             # Template clé API (à copier → .env)
├── .env                     # Votre clé API (à créer, ne pas committer)
├── .gitignore
├── data/
│   ├── images_metadata.json  # Générée par Tâche 1 (120 images)
│   ├── images_labels.json    # Générée par Tâche 2
│   ├── users.json            # Générée par Tâche 3 (5 profils)
│   ├── recommendations.json  # Générée par Tâche 5
│   └── visualisations.png    # Générée par Tâche 4 (9 graphiques)
└── images/
    └── image_001.jpg … image_120.jpg   # 120 images JPEG
```

## 📊 Fichiers générés

| Fichier | Description | Taille estimée |
|---------|-------------|----------------|
| `images/` | 120 images JPEG Unsplash | ~25 MB |
| `data/images_metadata.json` | Métadonnées des 120 images | ~250 KB |
| `data/images_labels.json` | Labels, couleurs, orientation | ~120 KB |
| `data/users.json` | Profils de 5 utilisateurs | ~10 KB |
| `data/recommendations.json` | 5 recommandations × 5 utilisateurs | ~5 KB |
| `data/visualisations.png` | 9 graphiques | ~200 KB |

## 🧪 Tests

Le notebook contient 3 suites de tests dans la **Tâche 6** :

- **`test_data_integrity()`** : Vérifie que toutes les images ont des métadonnées valides
- **`test_functional()`** : Vérifie l'extraction de couleurs, les profils utilisateurs
- **`test_recommendation_quality()`** : Vérifie la qualité et la pertinence des recommandations

Si tous les tests passent, vous verrez :
```
🎉 TOUS LES TESTS RÉUSSIS !
```

## 🎯 Comparaison avec la Partie 2

| Aspect | Partie 1 (Notebook) | Partie 2 (Docker + PySpark) |
|--------|---------------------|-----------------------------|
| **Architecture** | Monolithique | Distribuée (3 conteneurs) |
| **Traitement** | Séquentiel (boucles) | Parallèle (map-reduce) |
| **Déploiement** | Local uniquement | Conteneurisé, portable |
| **Scalabilité** | Limitée | Haute (multi-workers) |

## 🐛 Dépannage

### Erreur : clé API manquante
```
ValueError: ❌ Clé API Unsplash manquante ! Vérifiez le fichier .env
```
→ Vérifier que `.env` existe dans `partie1/` et contient `UNSPLASH_ACCESS_KEY=votre_cle`

### Erreur : module not found
→ Exécuter `pip install -r requirements.txt` depuis `partie1/`

### Les images ne s'affichent pas
→ S'assurer que le notebook est ouvert depuis `partie1/` (le CWD doit être `partie1/`)

## 📚 Références

- [Documentation Unsplash API](https://unsplash.com/documentation)
- [Scikit-learn RandomForestClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html)
- [Pillow (PIL)](https://pillow.readthedocs.io/)
- [KMeans Clustering](https://scikit-learn.org/stable/modules/generated/sklearn.cluster.KMeans.html)

---

**Auteurs** : BONNET & DURANO  
**Date** : Février 2026  
**Cours** : Données Massives
