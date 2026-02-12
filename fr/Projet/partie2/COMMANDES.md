# 🚀 Commandes Rapides - Partie 2

## Prérequis
- Docker Desktop installé et démarré
- Clé API Unsplash configurée dans .env

## 📝 Vérifier la configuration

```powershell
# Vérifier que Docker est lancé
docker --version
docker compose version

# Vérifier que le fichier .env existe
Get-Content .env
```

## 🏗️ Construire et exécuter

```powershell
# Aller dans le dossier partie2
cd "c:\Users\maxen\.vscodeProject\DonneMassiv\fr\Projet\partie2"

# Construire et exécuter tous les conteneurs (en séquence)
docker compose up --build

# OU en mode détaché (arrière-plan)
docker compose up --build -d
```

## 📊 Surveiller l'exécution

```powershell
# Voir les logs en temps réel
docker compose logs -f

# Logs d'un conteneur spécifique
docker compose logs acquisition
docker compose logs analysis
docker compose logs recommendation

# Statut des conteneurs
docker compose ps
```

## 📁 Vérifier les résultats

```powershell
# Lister les fichiers générés
docker compose run --rm recommendation ls -lh /shared_data/

# Voir les métadonnées
docker compose run --rm recommendation cat /shared_data/images_metadata.json

# Voir les recommandations
docker compose run --rm recommendation cat /shared_data/recommendations.json
```

## 💾 Copier les résultats

```powershell
# Copier tous les fichiers du volume
docker cp projet_recommendation:/shared_data ./output

# Vérifier les fichiers copiés
Get-ChildItem -Path ./output -Recurse

# Statistiques
Get-ChildItem -Path ./output/images | Measure-Object | Select-Object Count
```

## 🧹 Nettoyer

```powershell
# Arrêter les conteneurs
docker compose down

# Supprimer aussi les volumes (⚠️ supprime les données)
docker compose down -v

# Supprimer les images Docker
docker compose down --rmi all

# Tout nettoyer
docker compose down -v --rmi all
```

## 🔍 Dépannage

### Docker ne démarre pas
```powershell
# Vérifier le service
Get-Service docker
# Redémarrer Docker Desktop manuellement
```

### Erreur de clé API
```powershell
# Vérifier le contenu de .env
Get-Content .env
# S'assurer que UNSPLASH_ACCESS_KEY est défini
```

### Rebuild d'un conteneur spécifique
```powershell
docker compose build acquisition
docker compose up acquisition
```

### Voir les ressources utilisées
```powershell
docker stats
```

## 📊 Temps estimés

- **acquisition** : 5-10 minutes (~120 images)
- **analysis** : 5-10 minutes (étiquetage + visualisation)
- **recommendation** : 2-5 minutes (ML + tests)
- **Total** : 15-25 minutes

## ✅ Checklist d'exécution

- [ ] Docker Desktop lancé
- [ ] Fichier .env configuré avec clé API
- [ ] `docker compose up --build` exécuté
- [ ] Tous les conteneurs terminés avec succès
- [ ] Tests passés (vérifier les logs)
- [ ] Résultats copiés dans ./output
- [ ] Fichiers vérifiés :
  - [ ] images_metadata.json
  - [ ] images_labels.json
  - [ ] users.json
  - [ ] visualisations.png
  - [ ] recommendations.json

## 🎯 Commandes pour la soumission

```powershell
# Créer le dossier de soumission
New-Item -ItemType Directory -Path "./submission"

# Copier les fichiers nécessaires
Copy-Item -Path "./acquisition" -Destination "./submission/acquisition" -Recurse
Copy-Item -Path "./analysis" -Destination "./submission/analysis" -Recurse
Copy-Item -Path "./recommendation" -Destination "./submission/recommendation" -Recurse
Copy-Item -Path "./docker-compose.yml" -Destination "./submission/"
Copy-Item -Path "./.env.example" -Destination "./submission/"
Copy-Item -Path "./README.md" -Destination "./submission/"

# Copier les résultats (sans les images)
New-Item -ItemType Directory -Path "./submission/output"
Copy-Item -Path "./output/*.json" -Destination "./submission/output/"
Copy-Item -Path "./output/*.png" -Destination "./submission/output/"

# Créer le ZIP (nécessite 7zip ou un outil similaire)
Compress-Archive -Path "./submission/*" -DestinationPath "./BONNET_DURANO_Partie2.zip"
```
