# Diagramme de l'Architecture Complète du Projet

Voici la modélisation complète du pipeline de données de votre projet, incluant l'intégralité du processus : l'acquisition parallèle, l'analyse des images, la génération des utilisateurs, les visualisations, les modèles de machine learning pour les recommandations et la phase de test.

```mermaid
flowchart TB
    %% -- DÉFINITION DES STYLES --
    classDef container fill:#f4f7fb,stroke:#2c3e50,stroke-width:2px,rx:10px,ry:10px
    classDef sparkMap fill:#e8daef,stroke:#9673a6,stroke-width:2px,rx:5px,ry:5px
    classDef sparkRed fill:#dae8fc,stroke:#6c8ebf,stroke-width:2px,rx:5px,ry:5px
    classDef dataNode fill:#fff2cc,stroke:#d6b656,stroke-width:2px,stroke-dasharray: 5 5
    classDef fileNode fill:#d5e8d4,stroke:#82b366,stroke-width:2px
    classDef externalReq fill:#ffe6cc,stroke:#d79b00,stroke-width:2px
    classDef report fill:#f8cecc,stroke:#b85450,stroke-width:2px

    %% -- SOURCES ET EXPORTS FINAUX --
    Unsplash(("API Unsplash")) ::: externalReq
    Rapport(["Rapport de Synthèse PDF<br/>& Résultats de Tests"]) ::: report

    %% -- VOLUME DOCKER PARTAGÉ --
    subgraph DockerVolume ["Volume Docker Partagé : /shared_data/"]
        direction LR
        IMG_DIR["📁 images/"] ::: fileNode
        META_JSON["📄 images_metadata.json"] ::: fileNode
        LABELS_JSON["📄 images_labels.json"] ::: fileNode
        USERS_JSON["📄 users.json"] ::: fileNode
        VIZ_PNG["🖼️ visualisations.png"] ::: fileNode
        RECO_JSON["📄 recommendations.json"] ::: fileNode
    end

    %% ========================================================
    %% CONTENEUR 1 : ACQUISITION
    %% ========================================================
    subgraph CT1 ["Conteneur 1 : Acquisition de données"]
        direction TB
        Spark1["Driver Spark CT1"]
        
        MapAcq("🌐 Traitement Parallèle (Map)<br/>- Téléchargement des images<br/>- Extraction données EXIF") ::: sparkMap
        FilterAcq("⏳ Validation (Filter)<br/>- Rejet des téléchargements en échec") ::: sparkMap
        AggAcq("📦 Agrégation (Collect)<br/>- Rassemblement des métadonnées") ::: sparkRed

        Spark1 -->|"sc.parallelize"| MapAcq
        MapAcq --> FilterAcq
        FilterAcq -->|"collect"| AggAcq
    end

    Unsplash -->|"Requêtes APIs<br/>(Nature, Art...)"| MapAcq
    MapAcq -.->|"Sauvegarde par workers"| IMG_DIR
    AggAcq -.->|"Driver sauvegarde"| META_JSON

    %% ========================================================
    %% CONTENEUR 2 : ANALYSE & ÉTIQUETAGE
    %% ========================================================
    subgraph CT2 ["Conteneur 2 : Analyse & Étiquetage"]
        direction TB
        Spark2["Driver Spark CT2"]
        
        MapColors("🎨 Map Parallèle (Analyse)<br/>- Algorithme KMeans (Couleurs)<br/>- Calcul Orientation & Taille<br/>- Génération des Tags") ::: sparkMap
        AggColors("📦 Collect : Agrégation labels") ::: sparkRed
        
        GenUsers("👥 Génération Utilisateurs<br/>- Simulation de favoris") ::: sparkRed
        MapUsers("🏷️ Map/ReduceByKey Parallèle<br/>- Profilage des préférences<br/>- Top couleurs/tags par uilisateur") ::: sparkMap
        AggUsers("📦 Collect : Agrégation profils") ::: sparkRed

        Matplotlib("📊 Visualisation (Matplotlib)<br/>- Stats de la collection<br/>- Histogrammes des couleurs<br/>- Graphiques préférences usagers") ::: sparkRed

        Spark2 -->|"sc.parallelize"| MapColors
        MapColors --> AggColors
        
        AggColors --> GenUsers
        GenUsers -->|"sc.parallelize"| MapUsers
        MapUsers --> AggUsers

        AggColors --> Matplotlib
        AggUsers --> Matplotlib
    end

    IMG_DIR -.->|"Lecture par workers"| MapColors
    META_JSON -.-> Spark2
    
    AggColors -.->|"Sauvegarde labels"| LABELS_JSON
    AggUsers -.->|"Sauvegarde users"| USERS_JSON
    Matplotlib -.->|"Export graphiques"| VIZ_PNG

    %% ========================================================
    %% CONTENEUR 3 : RECOMMANDATION & TESTS
    %% ========================================================
    subgraph CT3 ["Conteneur 3 : Recommandation & Tests"]
        direction TB
        Spark3["Driver Spark CT3"]

        PrepFeat("⚙️ Préparation & Encodage<br/>- LabelEncoder (Catégoriel)") ::: sparkRed
        MapReco("🧠 Machine Learning Parallèle (Map)<br/>- Random Forest Classifier<br/>- Entraînement sur favoris") ::: sparkMap
        PredReco("✨ Génération des Recommandations<br/>- Inférence sur images non vues") ::: sparkMap
        AggReco("📦 Collect : Agrégation ML") ::: sparkRed
        RunTests("✅ Tests unitaires & Qualité<br/>- assert, exactitude") ::: sparkRed

        Spark3 --> PrepFeat
        PrepFeat -->|"sc.parallelize"| MapReco
        MapReco --> PredReco
        PredReco -->|"collect"| AggReco
        AggReco --> RunTests
    end

    META_JSON -.-> Spark3
    LABELS_JSON -.-> Spark3
    USERS_JSON -.-> Spark3

    AggReco -.->|"Sauvegarde Recos"| RECO_JSON
    RunTests -.->|"Résultats & Validation"| Rapport

    %% Styling Conteneurs
    class CT1,CT2,CT3 container
    class DockerVolume dataNode
```
