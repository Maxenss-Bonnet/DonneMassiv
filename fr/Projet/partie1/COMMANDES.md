# 🚀 Commandes Rapides - Partie 1

## Prérequis
- Python 3.10+ installé
- Clé API Unsplash configurée dans `.env`
- Jupyter Lab ou VS Code avec extension Jupyter

---

## 📝 Configuration initiale

```powershell
# Aller dans le dossier partie1
cd "c:\Users\maxen\.vscodeProject\DonneMassiv\fr\Projet\partie1"

# (Si première fois) Créer et activer un environnement virtuel
python -m venv .venv
.venv\Scripts\Activate.ps1

# Installer les dépendances
pip install -r requirements.txt

# Configurer la clé API
Copy-Item .env.example .env
# → Éditer .env et remplacer 'your_access_key_here' par votre vraie clé
```

---

## ▶️ Exécuter le notebook

```powershell
# Option 1 : Jupyter Lab (interface web)
jupyter lab BONNET_DURANO.ipynb

# Option 2 : VS Code
# Ouvrir BONNET_DURANO.ipynb dans VS Code, puis Kernel > Restart & Run All

# Option 3 : Exécution en ligne de commande (sans interface)
jupyter nbconvert --to notebook --execute BONNET_DURANO.ipynb --output BONNET_DURANO_executed.ipynb
```

---

## 📁 Vérifier les résultats

```powershell
# Vérifier les fichiers générés
Get-ChildItem data\ | Format-Table Name, Length, LastWriteTime

# Nombre d'images collectées
(Get-ChildItem images\).Count

# Afficher les premières recommandations
Get-Content data\recommendations.json | python -c "import json,sys; d=json.load(sys.stdin); [print(f'{u}: {[r[\"filename\"] for r in recs]}') for u,recs in d.items()]"
```

---

## 🧪 Exécuter les tests uniquement

Dans le notebook, localiser la cellule **Tâche 6** et exécuter uniquement les cellules de test :

```python
# Charger les données et exécuter les 3 tests
test_data_integrity()
test_functional()
test_recommendation_quality()
```

---

## 🧹 Nettoyer et recommencer

```powershell
# Supprimer les données générées (garder les images pour éviter de re-télécharger)
Remove-Item data\images_metadata.json -ErrorAction SilentlyContinue
Remove-Item data\images_labels.json   -ErrorAction SilentlyContinue
Remove-Item data\users.json           -ErrorAction SilentlyContinue
Remove-Item data\recommendations.json -ErrorAction SilentlyContinue
Remove-Item data\visualisations.png   -ErrorAction SilentlyContinue

# Supprimer aussi les images (si besoin d'une nouvelle collecte)
Remove-Item images\* -ErrorAction SilentlyContinue
```

---

## 📦 Préparer la soumission

```powershell
# Créer le dossier de soumission
$zip_name = "BONNET_DURANO"
New-Item -ItemType Directory -Path "..\$zip_name" -Force

# Copier les fichiers requis
Copy-Item "BONNET_DURANO.ipynb"     "..\$zip_name\"
Copy-Item "data\images_metadata.json" "..\$zip_name\data\" -Force
Copy-Item "data\images_labels.json"   "..\$zip_name\data\" -Force
Copy-Item "data\users.json"           "..\$zip_name\data\" -Force
# NE PAS inclure : images/ (trop volumineux), .env (secrets)

# Créer l'archive ZIP
Compress-Archive -Path "..\$zip_name\*" -DestinationPath "..\$zip_name.zip" -Force

Write-Host "✅ Archive créée : $zip_name.zip"
```

---

## ✅ Checklist avant soumission

- [ ] `.env` configuré avec la clé API Unsplash
- [ ] Notebook exécuté sans erreurs (Kernel > Restart & Run All)
- [ ] 120 images présentes dans `images/`
- [ ] Les 5 fichiers dans `data/` sont générés
- [ ] Les 3 suites de tests passent
- [ ] `rapport_synthese.pdf` rédigé et inclus dans le ZIP

---

## 🔍 Dépannage

### Module non trouvé
```powershell
pip install -r requirements.txt
```

### Erreur clé API
```powershell
Get-Content .env   # Vérifier que UNSPLASH_ACCESS_KEY est défini
```

### Kernel mort dans Jupyter
→ Kernel > Restart, puis ré-exécuter depuis le début

### CWD incorrect (les fichiers ne se créent pas au bon endroit)
→ S'assurer que le notebook est ouvert depuis `partie1/`, pas depuis `fr/Projet/`
→ Dans le notebook, exécuter `import os; print(os.getcwd())` pour vérifier

---

## 📊 Temps estimés

| Tâche | Temps estimé |
|-------|-------------|
| Tâche 1 : Collecte (120 images) | ~5–8 minutes |
| Tâche 2 : Étiquetage (KMeans × 120) | ~2–4 minutes |
| Tâche 3 : Profils utilisateurs | < 1 minute |
| Tâche 4 : Visualisation | < 1 minute |
| Tâche 5 : Recommandation (ML) | < 1 minute |
| Tâche 6 : Tests | < 1 minute |
| **Total** | **~10–15 minutes** |
