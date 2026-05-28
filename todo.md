# Roadmap AgroFrugal : Diagnostic Agricole Frugal

Ce document détaille les étapes à suivre pour finaliser le projet **AgroFrugal** en respectant les principes d'éco-conception et d'IA frugale.

---

## Phase 1 : Optimisation du Modèle (Algorithmie)
*Objectif : Réduire l'empreinte du modèle NER sans sacrifier la précision.*

- [ ] **Benchmark Initial** : Ouvrir `notebook_ner.ipynb` et exécuter le comparatif BERT vs DistilBERT FP32 (Taille, Latence P95, CO2 via CodeCarbon).
- [ ] **Quantification INT8** : Compléter la section 2 du notebook pour quantifier dynamiquement DistilBERT (`torch.quantization.quantize_dynamic`).
    - *Cible : Taille ~110 MB (-41% vs FP32), Latence -67%.*
- [ ] **Évaluation de Précision** : Vérifier que l'accuracy reste > 92% (perte < 0.5% acceptée).
- [ ] **Export des Métriques** : Générer le fichier `out/metrics.json` contenant `accuracy` et `co2_kg_per_inference`.
- [ ] **Persistence** : Sauvegarder le modèle quantifié dans `./models/distilbert-int8/`.

## Phase 2 : Développement de l'API (Logiciel)
*Objectif : Déployer une API FastAPI performante avec cache et instrumentation.*

- [ ] **Chargement du Modèle** : Dans `app.py`, implémenter le chargement du modèle INT8 et du tokenizer dans le hook `startup`.
- [ ] **Moteur NER** : Remplacer le placeholder de la fonction `_extract` par l'inférence réelle du modèle DistilBERT.
    - *Cible : Latence d'inférence < 100ms.*
- [ ] **Recherche FAQ Sémantique** : Améliorer `_find_faq` en utilisant la similarité cosinus des embeddings plutôt qu'une recherche par mots-clés.
- [ ] **Stratégie de Cache** : Vérifier la connexion Redis et ajuster la TTL dans `diagnose` pour optimiser le hit rate (> 60%).
- [ ] **Headers Green IT** : S'assurer que le middleware `CodeCarbonMiddleware` expose bien les headers `X-CO2-kg` et `X-Latency-ms`.

## Phase 3 : CI/CD & Green Gate (Automatisation)
*Objectif : Automatiser la validation de la qualité et de l'empreinte carbone.*

- [ ] **Configuration Pipeline** : Adapter `shared/github_actions_template.yml` pour le workflow `agrofrugal`.
- [ ] **Implémentation Green Gate** : Configurer le job `green-gate` pour échouer si :
    - `accuracy < 0.92`
    - `co2_kg_per_inference > 0.001`
- [ ] **Tests de Performance** : Intégrer `pytest-benchmark` pour bloquer les commits provoquant une régression de performance > 10%.

## Phase 4 : Infrastructure & Déploiement (Cloud/Edge)
*Objectif : Minimiser les ressources consommées au runtime.*

- [ ] **Optimisation Docker** : Finaliser le `Dockerfile.template` (Multi-stage build).
    - *Cible : Image finale < 150 MB pour transmission 4G.*
- [ ] **Right-sizing K8s** : Ajuster `requests` et `limits` dans `deployment.template.yaml`.
    - `requests` = P95 mesuré.
    - `limits` = 2x `requests`.
- [ ] **Scale-to-Zero** : Configurer la stratégie saisonnière pour désactiver les pods de novembre à février (saison morte agricole).

## Phase 5 : Monitoring & Pilotage (Observabilité)
*Objectif : Suivre l'impact réel et la qualité de service.*

- [ ] **Dashboard Grafana** : Importer `shared/grafana_dashboard.json` et vérifier les 4 panels :
    1. Latence P95 par projet.
    2. CO2 cumulé (kg).
    3. Utilisation CPU pods (%).
    4. Budget d'erreur SLO 99%.
- [ ] **Configuration Prometheus** : Vérifier que le scraping est limité aux métriques essentielles (via `metric_relabel_configs`) pour garder l'empreinte RAM < 200 MB.
- [ ] **Alerting** : Définir les 3 alertes SLO critiques pour la disponibilité et la performance.

---
*Livrable final : API déployée sur K3s avec Green Gate active et dashboard de suivi CO2.*
