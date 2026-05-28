# Rapport de Soutenance : Projet AgroFrugal

## 1. Vision et Objectifs
Le projet **AgroFrugal** vise à fournir un outil de diagnostic agricole par SMS pour des zones rurales où la connectivité (4G instable) et les ressources énergétiques sont limitées. 
L'enjeu technique était de déployer un modèle de Traitement du Langage Naturel (NLP) performant sur une infrastructure "Edge" tout en minimisant son empreinte environnementale.

## 2. Optimisation du Modèle (Phase 1)
### Quantification Dynamique INT8
Nous avons choisi de passer d'un modèle **DistilBERT FP32** à une version **quantifiée en INT8**.
- **Justification** : La quantification réduit la précision des poids du modèle de 32 bits à 8 bits. Cela divise par 2 la taille sur disque et accélère les calculs CPU.
- **Résultat** : 
    - Taille : **253 MB → 131 MB** (-48%).
    - Latence P95 : **17ms → 12ms**.
    - Impact Écologique : Réduction directe de la consommation électrique par inférence.

*Référence code : `app.py` (lignes 70-76) où le modèle est chargé et quantifié dynamiquement.*

## 3. Développement de l'API et Efficacité Logicielle (Phase 2)
### Inférence NER (Named Entity Recognition)
L'API utilise DistilBERT pour extraire l'intention (maladie, irrigation, récolte) et une logique frugale par mots-clés pour les entités (cultures).
- **Choix technique** : Utilisation de FastAPI pour son support natif de l'asynchrone et sa légèreté.
- **Cache Redis** : Un cache a été implémenté pour éviter de relancer l'inférence IA sur des messages identiques (ex: "Mes tomates ont du mildiou").
- **Justification** : Le cache est la mesure d'éco-conception la plus efficace : une lecture Redis consomme ~100x moins d'énergie qu'une inférence BERT.

## 4. Stratégie "Green IT" en CI/CD (Phase 3)
### La Green Gate
Nous avons implémenté un script `evaluate.py` servant de verrou pour le déploiement.
- **Critères de validation** : 
    - `Accuracy > 92%` : Garantie de la qualité de service.
    - `CO2 < 0.001 kg/inférence` : Garantie de respect du budget carbone.
- **Justification** : Empêcher toute régression environnementale dès la phase de développement (approche "Shift Left" appliquée à l'écologie).

## 5. Infrastructure et Déploiement (Phase 4)
### Dockerisation Optimisée
Le `Dockerfile` utilise un **build multi-stage**.
- **Justification** : On sépare la phase d'installation (builder) de la phase d'exécution (runtime). Cela permet de supprimer les caches pip, les compilateurs et les fichiers inutiles.
- **Résultat** : Une image finale < 150 MB, minimisant la bande passante nécessaire pour le déploiement sur des sites distants en 4G.

### Kubernetes "Right-sizing"
Le fichier `deployment.template.yaml` définit des limites de ressources strictes :
- `Requests: 256Mi RAM / 100m CPU`.
- **Justification** : Évite le gaspillage de ressources (Over-provisioning) sur le cluster. 
- **Scale-to-Zero** : Une stratégie saisonnière a été définie pour éteindre les services durant l'hiver agricole (Novembre-Février), économisant 60% des coûts d'infrastructure annuelle.

## 6. Monitoring et Observabilité (Phase 5)
L'application est instrumentée via **Prometheus** et **CodeCarbon**.
- **Indicateurs suivis** : Latence P95, CO2 cumulé, et utilisation CPU.
- **Justification** : On ne peut améliorer que ce que l'on mesure. Le dashboard Grafana permet un pilotage par la donnée réelle de l'impact environnemental de l'IA en production.
