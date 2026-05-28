# AgroFrugal - Projet d'IA Frugale et Éco-conçue

Ce dossier contient le rendu final du projet **AgroFrugal**, un système de diagnostic des maladies des cultures via SMS, optimisé pour une exécution sur le "Edge" (basse consommation, faible latence).

## 📁 Structure du Projet

- `agrofrugal/` : Code source de l'application et ressources.
    - `app.py` : API FastAPI avec inférence NER (DistilBERT INT8).
    - `Dockerfile` : Image Docker multi-stage optimisée (< 150 MB).
    - `evaluate.py` : Script de validation Green Gate (Accuracy & CO2).
    - `models/` : Modèle DistilBERT quantifié en INT8.
    - `tests/` : Tests unitaires automatisés.
- `shared/` : Ressources communes (Middleware CodeCarbon, Config Prometheus/Grafana).
- `soutenance.md` : Rapport détaillé des choix techniques et justifications écologiques.
- `todo.md` : Roadmap de suivi du projet.

## 🚀 Installation et Lancement

### Prérequis
- Python 3.10+
- Docker (optionnel pour le local)
- Redis (pour le cache)

### 1. Préparation de l'environnement
```bash
# Installer les dépendances
pip install -r agrofrugal/requirements.txt
```

### 2. Téléchargement et Génération du Modèle (Indispensable)
Le modèle n'est pas inclus dans le dépôt Git pour des raisons de poids. Vous devez le générer localement (téléchargement automatique depuis Hugging Face puis quantification INT8) :
```bash
python agrofrugal/scripts/quantize.py
```

### 3. Lancement Local de l'API
```bash
# Configurer les variables d'environnement
export PYTHONPATH=$PYTHONPATH:.
export REDIS_URL=redis://localhost:6379/0
export FAQ_PATH=agrofrugal/data/faq_agriculture_300.json
export MODEL_PATH=agrofrugal/models/distilbert-int8

# Lancer l'API
uvicorn agrofrugal.app:app --host 0.0.0.0 --port 8000
```

### Exécution des Tests
```bash
pytest agrofrugal/tests/test_api.py
```

## 📊 Métriques Clés
- **Taille du modèle** : 131 MB (réduction de 48% vs FP32).
- **Latence P95** : < 15ms par inférence.
- **Empreinte Carbone** : < 0.0001 kg CO2 par diagnostic.
- **Accuracy** : > 92% (Green Gate validée).
