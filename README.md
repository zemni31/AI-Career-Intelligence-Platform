# 🤖 AI Career Intelligence Platform

Une plateforme intelligente d'analyse du marché de l'emploi en Data & Intelligence Artificielle développée avec **Python, PostgreSQL, Power BI, Streamlit et Machine Learning**.

Le projet aide les étudiants et les professionnels à explorer le marché de l'emploi, comparer leurs compétences avec les exigences des métiers et obtenir des recommandations personnalisées.

---

## 📸 Aperçu de la plateforme

![Accueil](images/home.png)

---

# 🚀 Fonctionnalités

## 📊 1. Market Intelligence Dashboard (Power BI)

- Analyse de plus de 1400 offres d'emploi IA
- KPI du marché
- Top métiers recherchés
- Top compétences demandées
- Analyse géographique
- Analyse des salaires
- Tendances du marché IA

---

## 👤 2. AI Career Advisor (Streamlit)

Le Career Advisor permet de :

- saisir son profil
- sélectionner ses compétences
- comparer son profil avec les métiers IA
- obtenir un score de compatibilité
- identifier les compétences acquises
- identifier les compétences à développer
- construire un plan de carrière personnalisé

---

## 🤖 3. Assistant IA

L'assistant IA permet :

- répondre aux questions générales sur les métiers Data & IA
- expliquer les compétences recherchées
- conseiller les utilisateurs sur leur parcours professionnel
- répondre aux questions liées au domaine de l'Intelligence Artificielle

---

## 📈 4. Prédiction Machine Learning

Le projet intègre un modèle **XGBoost** permettant d'estimer un salaire à partir du profil de l'utilisateur.

Le modèle utilise notamment :

- expérience
- niveau du poste
- pays
- type de contrat
- travail remote
- taille de l'entreprise

---

## 🔄 5. Pipeline ETL

Les données sont automatiquement collectées depuis plusieurs sources :

- Kaggle
- Adzuna API

Le pipeline :

- collecte les données
- nettoie les données
- fusionne les différentes sources
- charge les données dans PostgreSQL

---

# 🛠 Technologies utilisées

- Python
- PostgreSQL
- Streamlit
- Power BI
- Pandas
- Scikit-learn
- XGBoost
- Plotly
- Groq API
- SQL


---

# ⚙ Installation

Cloner le dépôt :

```bash
git clone https://github.com/<votre-utilisateur>/AI-Career-Intelligence-Platform.git
```

Entrer dans le projet :

```bash
cd AI-Career-Intelligence-Platform
```

Installer les dépendances :

```bash
pip install -r requirements.txt
```

---

# ▶ Lancer l'application

Depuis la racine du projet :

```bash
python -m streamlit run src/career_advisor/app.py
```

Puis ouvrir :

```
http://localhost:8501
```

---

# 📊 Base de données

Le projet utilise PostgreSQL.

Principales tables :

- jobs
- companies
- countries
- skills
- job_skills

---

# 📈 Machine Learning

Algorithme :

- XGBoost Regressor

Objectif :

Prédire le salaire moyen à partir des caractéristiques d'une offre d'emploi.

---

# 📊 Sources de données

- Kaggle AI Jobs Dataset
- Adzuna Jobs API

---

# 👩‍💻 Auteur

**Rihab Zemni**

Étudiante en Génie Réseaux et Télécommunications

INSAT – Université de Carthage

---

# 📄 Licence

Projet académique développé dans le cadre d'un stage de fin d'année.