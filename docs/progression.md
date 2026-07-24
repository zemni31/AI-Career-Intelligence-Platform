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

### 5. Power BI — Dashboards (06/07/2026)
**Fichier 1 : Market_Intelligence.pbix**
- Top 10 compétences les plus demandées
- Salaire moyen par métier + slicer pays
- Répartition des offres par pays
- Répartition Remote / Non-Remote

**Fichier 2 : Tendances.pbix**
- Évolution mensuelle des offres (2025 vs 2026)
- Compétences en progression (2025 vs 2026)

**Fichier 3 : Entreprises.pbix**
- Top 15 entreprises qui recrutent
- Répartition par taille d'entreprise

## 🚧 Prochaine étape
- Améliorer le design des dashboards
- Rédiger le README.md GitHub
- Automatisation ETL (Task Scheduler)
- Préparer la présentation du projet

### 6. Application web Streamlit — Career Advisor (07/07/2026)
- Application multi-pages : Accueil, Mon Profil, Résultats, Plan de carrière, Tableau de bord
- Score de compatibilité métier (Dice coefficient)
- Jauge de compatibilité + badges (Excellent / Bon / Moyen)
- Export rapport PDF (fpdf2)
- Graphiques interactifs Plotly (salaires, compétences, géographie, tendances, entreprises)
- Intégration complète des visuels Power BI dans Streamlit

---

## 📊 État actuel (08/07/2026)

| Table | Lignes |
|---|---|
| jobs | ~5856 |
| companies | ~1400 |
| skills | 108 |
| job_skills | 10132 |

---

## 🚧 Prochaines étapes
- [ ] AI Agent Chatbot
- [ ] Prédiction de salaire (ML)
- [ ] README.md GitHub
- [ ] Présentation finale


 Finalisation du projet (24/07/2026)

- Nettoyage de l'architecture du projet
- Suppression des fichiers inutiles
- Création du fichier requirements.txt
- Rédaction du README GitHub
- Mise à jour de la documentation
- Vérification complète des fonctionnalités
- Préparation de la version finale du projet

---

## 🚧 Prochaine étape

### Rédaction du rapport de stage
- Présentation de l'entreprise
- Analyse des besoins
- Conception de la solution
- Architecture technique
- Développement de la plateforme
- Résultats obtenus
- Conclusion et perspectives