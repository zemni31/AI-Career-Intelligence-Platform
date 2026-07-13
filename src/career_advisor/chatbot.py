"""
src/career_advisor/chatbot.py
Chatbot RAG — Text-to-SQL + ML + Groq (Llama 3.1)
"""

import os
import sys
import json
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

sys.path.append(str(Path(__file__).resolve().parent.parent))
from db.connection import get_connection

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
   Utilise-le quand la question contient des mots comme :
   "prédit", "estime", "combien je vais gagner", "quel salaire pour moi",
   "si j'ai ces compétences combien", "mon salaire estimé"

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

Schéma de la base de données :
{DB_SCHEMA}

FORMAT DE RÉPONSE :
- Si SQL nécessaire : <SQL>SELECT ...</SQL> suivi de ton analyse
- Si ML nécessaire : <ML_PREDICT>{{"job_title": "...", "country": "...", ...}}</ML_PREDICT>
- Si réponse générale : réponds directement
"""


# ── Exécution SQL ─────────────────────────────────────────
def execute_sql(query: str) -> pd.DataFrame | str:
    """Exécute une requête SQL et retourne les résultats."""
    try:
        conn = get_connection()
        df   = pd.read_sql(query, conn)
        conn.close()
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
def extract_sql(text: str) -> str | None:
    """Extrait la requête SQL entre les balises <SQL> et </SQL>."""
    import re
    match = re.search(r"<SQL>(.*?)</SQL>", text, re.DOTALL)
    return match.group(1).strip() if match else None


def extract_ml_params(text: str) -> dict | None:
    """Extrait les paramètres ML entre les balises <ML_PREDICT>."""
    import re
    match = re.search(r"<ML_PREDICT>(.*?)</ML_PREDICT>", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except:
            return None
    return None


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
    # Construction des messages
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Ajout de l'historique (max 10 derniers échanges)
    for msg in history[-10:]:
        messages.append(msg)
    
    messages.append({"role": "user", "content": question})

    # Appel Groq
    response = client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=messages,
        temperature=0.3,
        max_tokens=1500
    )

    llm_response = response.choices[0].message.content

    # ── Traitement SQL ────────────────────────────────────
    sql_query = extract_sql(llm_response)
    if sql_query:
        sql_result = execute_sql(sql_query)
        
        if isinstance(sql_result, pd.DataFrame) and not sql_result.empty:
            # Renvoie les résultats au LLM pour formulation
            result_str = sql_result.to_string(index=False)
            
            followup_messages = messages + [
                {"role": "assistant", "content": llm_response},
                {"role": "user", "content": 
                 f"Voici les résultats SQL :\n{result_str}\n\n"
                 f"Formule une réponse claire et concise en français "
                 f"sans mentionner le SQL ni les balises techniques."}
            ]
            
            final_response = client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=followup_messages,
                temperature=0.3,
                max_tokens=800
            )
            final_answer = final_response.choices[0].message.content
        else:
            final_answer = "Je n'ai pas trouvé de données correspondantes dans la base."
    
    # ── Traitement ML ─────────────────────────────────────
    elif extract_ml_params(llm_response):
        ml_params  = extract_ml_params(llm_response)
        prediction = predict_salary(ml_params)
        
        followup_messages = messages + [
            {"role": "assistant", "content": llm_response},
            {"role": "user", "content": 
             f"La prédiction du modèle ML est : {prediction}\n\n"
             f"Formule une réponse claire pour l'utilisateur en intégrant "
             f"cette estimation et en ajoutant quelques conseils pertinents."}
        ]
        
        final_response = client.chat.completions.create(
            model="llama-3.1-70b-versatile",
            messages=followup_messages,
            temperature=0.3,
            max_tokens=800
        )
        final_answer = final_response.choices[0].message.content

    # ── Réponse générale ──────────────────────────────────
    else:
        final_answer = llm_response

    # Mise à jour de l'historique
    history.append({"role": "user",      "content": question})
    history.append({"role": "assistant", "content": final_answer})

    return final_answer, history


# ── Test rapide ───────────────────────────────────────────
if __name__ == "__main__":
    history = []
    questions = [
        "Quelles sont les 5 compétences les plus demandées ?",
        "Quel est le salaire moyen d'un Data Scientist ?",
        "Estime mon salaire : Data Scientist Senior en France avec Python et SQL",
    ]
    
    for q in questions:
        print(f"\n🧑 {q}")
        response, history = chat(q, history)
        print(f"🤖 {response}")