# Progression du projet
**Date : 01/07/2026**

## ✅ Étapes terminées

### 1. Environnement de développement
- Architecture du projet mise en place
- Configuration de VS Code
- Environnement Python
- Dépôt GitHub créé et synchronisé

### 2. Base de données PostgreSQL
- Schéma relationnel implémenté
- Tables créées :
  - countries
  - companies
  - skills
  - jobs
  - job_skills
- Données de référence (countries, skills) importées

### 3. Pipeline ETL
- ETL Kaggle développé
- Normalisation des pays (USA, UK, UAE...)
- 1500 offres Kaggle importées
- ETL Adzuna développé
- 3534 offres Adzuna importées
- Parser des compétences développé
- 14746 relations `job_skills` générées

### 4. Contrôle qualité
- Validation des données importées
- Vérification des statistiques SQL
- Premier pipeline ETL entièrement fonctionnel

---

## 🚧 Prochaine étape

### Intégration Power BI
- Connexion Power BI ↔ PostgreSQL
- Création du modèle de données
- Développement des tableaux de bord

### Dashboards prévus
- Dashboard 1 : Market Intelligence
- Dashboard 2 : Career Advisor
- Dashboard 3 : Skills Intelligence

---

## 📊 État actuel

- Countries : **17**
- Skills : **27**
- Jobs (Kaggle) : **1500**
- Jobs (Adzuna) : **3534**
- Total des offres : **5034**
- Relations `job_skills` : **14746**

---

## 🎯 Objectif suivant

Construire la première version interactive de la plateforme Power BI en utilisant les données stockées dans PostgreSQL.