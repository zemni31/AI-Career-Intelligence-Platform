"""
src/career_advisor/chatbot.py
Chatbot RAG — Text-to-SQL + ML + Groq (Llama 3.1)
"""

import os
import sys
import json
import re
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

sys.path.append(str(Path(__file__).resolve().parent.parent))
from db.connection import get_connection
from database import get_database_context
from sql_classifier import detect_sql_type
from sql_prompt_builder import build_prompt
from sql_validator import validate_sql, correct_sql_with_llm


def clean_response(text: str) -> str:
    """Supprime les balises <think>...</think> des réponses du LLM."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

# ── Chargement configuration ──────────────────────────────
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ── Chargement modèle ML ──────────────────────────────────
MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

try:
    ml_model       = joblib.load(MODELS_DIR / "salary_model.pkl")
    model_columns  = joblib.load(MODELS_DIR / "model_columns.pkl")
    skills_encoder = joblib.load(MODELS_DIR / "skills_encoder.pkl")
    ML_AVAILABLE   = True
except Exception as e:
    ML_AVAILABLE = False
    print(f"Modèle ML non disponible : {e}")

DEBUG = True


# ── Schéma de la base (pour le Text-to-SQL) ──────────────
DB_SCHEMA = """
Tables disponibles dans la base PostgreSQL ai_career_intelligence :

1. jobs (id, job_title, job_category, experience_level, years_of_experience,
          salary_avg, salary_min, salary_max, company_size, is_remote_friendly,
          industry, posted_date, posting_year, posting_month,
          country_id, company_id, source, description)
   - source : 'kaggle_ai_jobs' ou 'adzuna'
   - salary_avg en USD annuel
   - experience_level : 'Entry', 'Mid', 'Senior', 'Lead'

2. skills (id, name, category)
   - category : 'Langage', 'Cloud', 'BI Tool', 'ML Framework', 'Big Data'...

3. job_skills (job_id, skill_id)
   - Table de relation entre jobs et skills

4. countries (id, code, name, continent)

5. companies (id, name, size, country_id)
"""

# ── Prompt système ────────────────────────────────────────
SYSTEM_PROMPT = f"""
Tu es un assistant expert en marché de l'emploi Data & Intelligence Artificielle.
Tu aides les étudiants et professionnels à prendre des décisions de carrière.

Tu as accès à trois sources d'information :

1. BASE DE DONNÉES PostgreSQL (Text-to-SQL)
   Utilise-la pour les questions sur :
   - Statistiques réelles (salaires moyens, nombre d'offres, top compétences...)
   - Classements (top pays, top entreprises, top métiers...)
   - Tendances historiques des données

2. MODÈLE ML (prédiction de salaire)
   Utilise OBLIGATOIREMENT le format <ML_PREDICT> quand la question contient :
   - "estime", "estimation", "estimé", "prédit", "prédiction"
   - "combien je vais gagner", "quel salaire pour moi"
   - "mon salaire", "salaire estimé", "salaire prédit"
   - Un profil personnel : "je suis", "avec mes compétences", "pour mon profil"
   - Une combinaison métier + pays + compétences personnelles

   EXEMPLE OBLIGATOIRE :
   Question : "Estime mon salaire : Data Scientist Senior en France avec Python et SQL"
   Réponse : <ML_PREDICT>{{"job_title": "Data Scientist", "experience_level": "Senior", 
   "country": "France", "skills": ["Python", "SQL"], 
   "years_of_experience": 5}}</ML_PREDICT>

   NE JAMAIS utiliser SQL pour une question de prédiction personnalisée.

3. TES CONNAISSANCES GÉNÉRALES
   Utilise-les pour :
   - Définitions de métiers Data/IA
   - Conseils de carrière généraux
   - Questions hors données

RÈGLES IMPORTANTES :
- Réponds TOUJOURS en français
- Pour les questions SQL, génère UNE SEULE requête SQL valide
- La requête SQL doit être entre les balises <SQL> et </SQL>
- Pour les prédictions ML, indique <ML_PREDICT> avec les paramètres JSON
- Ne génère JAMAIS de données inventées — dis "je ne dispose pas de cette information"
- Sois concis et précis

RÈGLES SQL IMPORTANTES :
- Pour les salaires, utilise toujours la colonne salary_avg
- Filtre toujours avec WHERE salary_avg IS NOT NULL AND salary_avg > 0
- Pour les titres de postes, utilise ILIKE pour éviter les problèmes de casse
  Ex: WHERE job_title ILIKE '%Data Scientist%'
- Pour les pays, utilise la table countries.
- Les pays sont enregistrés ainsi :
  - UK -> United Kingdom
  - USA -> United States
  - US -> United States
  - Utilise toujours les noms présents dans la base de données.
- Ne jamais filtrer par source sauf si l'utilisateur le demande explicitement
- Pour compter les offres par pays, utilise toutes les sources combinées
- Pour les salaires, utilise de préférence source = 'kaggle_ai_jobs' car Adzuna a peu de salaires
- Pour les compétences et métiers, utilise toutes les sources
- La source principale pour les salaires est 'kaggle_ai_jobs'

Schéma de la base de données :
{DB_SCHEMA}

FORMAT DE RÉPONSE :
- Si SQL nécessaire : <SQL>SELECT ...</SQL> suivi de ton analyse
- Si ML nécessaire : <ML_PREDICT>{{"job_title": "...", "country": "...", ...}}</ML_PREDICT>
- Si réponse générale : réponds directement
"""


# ── Exécution SQL ─────────────────────────────────────────
def execute_sql(query: str) -> pd.DataFrame | str:
    """Exécute une requête SQL via SQLAlchemy."""
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(
            f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
            f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_NAME')}"
        )
        with engine.connect() as conn:
            df = pd.read_sql(text(query), conn)
        return df
    except Exception as e:
        return f"Erreur SQL : {e}"


# ── Prédiction ML ─────────────────────────────────────────
def predict_salary(params: dict) -> str:
    """Prédit un salaire avec le modèle XGBoost."""
    if not ML_AVAILABLE:
        return "Modèle ML non disponible."

    try:
        skills_list   = params.get("skills", [])
        known_skills  = [s for s in skills_list if s in skills_encoder.classes_]
        skills_encoded = pd.DataFrame(
            skills_encoder.transform([known_skills]),
            columns=[f"skill_{c}" for c in skills_encoder.classes_]
        )

        input_row = pd.DataFrame(columns=model_columns)
        input_row.loc[0] = 0

        categorical_map = {
            "job_title":          params.get("job_title", ""),
            "country":             params.get("country", ""),
            "experience_level":    params.get("experience_level", ""),
            "is_remote_friendly":  params.get("is_remote_friendly", False),
            "job_category":        params.get("job_category", ""),
            "employment_type":     params.get("employment_type", ""),
            "company_size":        params.get("company_size", ""),
            "industry":            params.get("industry", ""),
        }

        for col, val in categorical_map.items():
            col_name = f"{col}_{val}"
            if col_name in input_row.columns:
                input_row[col_name] = 1

        if "years_of_experience" in input_row.columns:
            input_row["years_of_experience"] = params.get("years_of_experience", 3)

        for col in skills_encoded.columns:
            if col in input_row.columns:
                input_row[col] = skills_encoded[col].values[0]

        input_row  = input_row.fillna(0)
        prediction = np.expm1(ml_model.predict(input_row)[0])
        return f"${prediction:,.0f} USD/an"

    except Exception as e:
        return f"Erreur prédiction : {e}"


# ── Extraction SQL depuis la réponse LLM ──────────────────
import re

def extract_sql(text: str):
    """
    Extrait une requête SQL quel que soit le format renvoyé par le LLM.
    Compatible avec :
      - <SQL>...</SQL>
      - ```sql ... ```
      - SELECT ... directement
    """

    if not text:
        return None

    # Cas 1 : <SQL> ... </SQL>
    match = re.search(r"<SQL>(.*?)</SQL>", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Cas 2 : ```sql ... ```
    match = re.search(r"```sql\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Cas 3 : ``` ... ```
    match = re.search(r"```\s*(.*?)```", text, re.DOTALL)
    if match:
        sql = match.group(1).strip()
        if sql.upper().startswith("SELECT"):
            return sql

    # Cas 4 : réponse directe
    if text.strip().upper().startswith("SELECT"):
        return text.strip()

    return None


def validate_sql(query: str) -> tuple[str | None, str | None]:
    """Valide une requête SQL avant exécution."""
    if not query:
        return None, "Requête vide."

    sql = query.strip()
    sql_upper = sql.upper()

    if not sql_upper.startswith("SELECT"):
        return None, "Seules les requêtes SELECT sont autorisées."

    forbidden = ["INSERT ", "UPDATE ", "DELETE ", "DROP ", "TRUNCATE ", "ALTER "]
    if any(word in sql_upper for word in forbidden):
        return None, "Seules les requêtes SELECT sont autorisées."

    conn = None
    try:
        conn = get_connection()
        schema = pd.read_sql(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema='public'
            """,
            conn
        )
    except Exception as e:
        return None, f"Impossible de valider la requête SQL : {e}"
    finally:
        if conn is not None:
            conn.close()

    table_names = set(schema["table_name"].unique())
    table_columns = {}
    for _, row in schema.iterrows():
        table_columns.setdefault(row["table_name"], set()).add(row["column_name"])

    found_tables = []
    for match in re.findall(r"\bFROM\s+([a-zA-Z0-9_\.]+)|\bJOIN\s+([a-zA-Z0-9_\.]+)", sql, re.IGNORECASE):
        found_tables.extend([t for t in match if t])

    normalized_tables = [t.split(".")[-1].strip() for t in found_tables]
    for table in normalized_tables:
        if table not in table_names:
            return None, f"Table inconnue : {table}."

    return sql, None


def extract_ml_params(text: str) -> dict | None:
    """Extrait les paramètres ML entre les balises <ML_PREDICT>."""
    match = re.search(r"<ML_PREDICT>(.*?)</ML_PREDICT>", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except:
            return None
    return None


def detect_intent(question: str) -> str:
    """
    Détermine si la question nécessite :
    SQL / ML / GENERAL
    """

    prompt = f"""
Tu es un classificateur.

Tu dois répondre UNIQUEMENT par un mot parmi :

SQL
ML
GENERAL

SQL :
- nombre d'offres
- statistiques
- salaires observés
- top compétences
- entreprises
- pays
- métiers
- tendances
- informations présentes dans la base

ML :
- estimation
- prédiction
- salaire futur
- combien vais-je gagner
- mon salaire
- selon mon profil
- avec mes compétences

GENERAL :
- définition
- explication
- conseil
- différence entre deux métiers
- questions hors base

Question :

{question}

Réponds uniquement par :

SQL
ML
GENERAL
"""

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role":"user",
                "content":prompt
            }
        ],
        temperature=0,
        max_tokens=5
    )

    return response.choices[0].message.content.strip().upper()


def generate_sql(question: str):
    db_context = ""

    try:
        db_context = get_database_context()
    except Exception as e:
        if DEBUG:
            print(f"Impossible de charger le contexte de la base : {e}")

    sql_type = detect_sql_type(question, client)
    if DEBUG:
        print("SQL type detected:", sql_type)

    prompt = build_prompt(question, db_context, sql_type)

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role":"user",
                "content":prompt
            }
        ],
        temperature=0
    )

    if DEBUG:
        print("\n===== REPONSE BRUTE DU LLM =====")
        print(response.choices[0].message.content)
        print("================================\n")

    return clean_response(response.choices[0].message.content)


# ── Fonction principale du chatbot ────────────────────────
def chat(question: str, history: list) -> tuple[str, list]:
    """
    Traite une question utilisateur et retourne la réponse.
    
    Args:
        question : question de l'utilisateur
        history  : historique de la conversation
    
    Returns:
        (réponse, historique mis à jour)
    """
    intent = detect_intent(question)

    if DEBUG:
        print("=" * 60)
        print("QUESTION :", question)
        print("INTENTION :", intent)
        print("=" * 60)

    # Construction des messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Ajout de l'historique (max 10 derniers échanges)
    for msg in history[-10:]:
        messages.append(msg)
    
    messages.append({"role": "user", "content": question})

    final_answer = ""

    if intent == "SQL":
        llm_response = generate_sql(question)
        sql_query = extract_sql(llm_response)

        if DEBUG:
            print("\nSQL généré :\n")
            print(sql_query)
            print()

        if sql_query is None:
            final_answer = "Je n'ai pas réussi à générer une requête SQL."
        elif any(keyword in sql_query.upper() for keyword in ["DROP", "DELETE", "UPDATE", "INSERT", "TRUNCATE", "ALTER"]):
            final_answer = "Requête refusée."
        else:
            validated_query, validation_error = validate_sql(sql_query)
            if validation_error:
                if DEBUG:
                    print("Validation SQL échouée :", validation_error)

                corrected_sql = None
                try:
                    db_context = get_database_context()
                    corrected_sql = correct_sql_with_llm(sql_query, validation_error, db_context, client)
                except Exception as e:
                    if DEBUG:
                        print("Correction SQL impossible :", e)
                    corrected_sql = None

                if corrected_sql:
                    if DEBUG:
                        print("SQL corrigé par le LLM :")
                        print(corrected_sql)

                    validated_query, validation_error = validate_sql(corrected_sql)
                    if validated_query and not validation_error:
                        sql_query = validated_query
                    else:
                        final_answer = (
                            "La requête SQL n'a pas pu être validée après correction automatique : "
                            f"{validation_error}"
                        )
                else:
                    final_answer = (
                        "La requête SQL générée n'est pas valide : "
                        f"{validation_error}\n\n"
                        "Réessaie avec une question plus précise ou vérifie les colonnes/tables citées."
                    )

            if final_answer == "":
                sql_result = execute_sql(sql_query)
                if DEBUG:
                    print(sql_result)

                if isinstance(sql_result, pd.DataFrame) and not sql_result.empty:
                    result_str = sql_result.to_string(index=False)
                    followup_messages = messages + [
                        {"role": "assistant", "content": llm_response},
                        {"role": "user", "content": 
                         f"Voici les résultats SQL :\n{result_str}\n\n"
                         f"Formule une réponse claire et concise en français "
                         f"sans mentionner le SQL ni les balises techniques."}
                    ]
                    final_response = client.chat.completions.create(
                        model="meta-llama/llama-4-scout-17b-16e-instruct",
                        messages=followup_messages,
                        temperature=0.3,
                        max_tokens=800
                    )
                    final_answer = clean_response(final_response.choices[0].message.content)
                else:
                    if isinstance(sql_result, pd.DataFrame) and sql_result.empty:
                        if "salary_avg" in sql_query and "companies" in sql_query:
                            final_answer = (
                                "Cette information n'est pas disponible dans la base de données.\n\n"
                                "Les données salariales ne sont pas associées aux entreprises, "
                                "il est donc impossible de déterminer quelle entreprise propose "
                                "le salaire moyen le plus élevé.\n\n"
                                "📊 Source : Base PostgreSQL"
                            )
                        else:
                            final_answer = (
                                "Aucune donnée ne correspond à votre recherche.\n\n"
                                "📊 Source : Base PostgreSQL"
                            )
                    else:
                        final_answer = "Je n'ai pas trouvé de données correspondantes dans la base."

        if not final_answer.endswith("📊 Source : Base PostgreSQL"):
            final_answer += "\n\n📊 Source : Base PostgreSQL"

    elif intent == "ML":
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=messages,
            temperature=0.3,
            max_tokens=1500
        )
        llm_response = clean_response(response.choices[0].message.content)

        ml_params = extract_ml_params(llm_response)
        if ml_params:
            prediction = predict_salary(ml_params)
            followup_messages = messages + [
                {"role": "assistant", "content": llm_response},
                {"role": "user", "content": 
                 f"La prédiction du modèle ML est : {prediction}\n\n"
                 f"Formule une réponse claire pour l'utilisateur en intégrant "
                 f"cette estimation et en ajoutant quelques conseils pertinents."}
            ]
            final_response = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=followup_messages,
                temperature=0.3,
                max_tokens=800
            )
            final_answer = clean_response(final_response.choices[0].message.content)
        else:
            final_answer = "Je n'ai pas réussi à extraire les paramètres de prédiction ML."

        final_answer += "\n\n🤖 Source : Modèle Machine Learning"

    else:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=messages,
            temperature=0.3,
            max_tokens=1500
        )
        final_answer = clean_response(response.choices[0].message.content)
        final_answer += "\n\n💡 Source : Connaissances générales"

    # Mise à jour de l'historique
    history.append({"role": "user",      "content": question})
    history.append({"role": "assistant", "content": final_answer})

    return final_answer, history


# ── Test rapide ───────────────────────────────────────────
if __name__ == "__main__":
    history = []
    questions = [
        "Quel métier a connu la plus forte croissance entre 2025 et 2026 ?",

    ]
    
    for q in questions:
        print(f"\n🧑 {q}")
        response, history = chat(q, history)
        print(f"🤖 {response}")