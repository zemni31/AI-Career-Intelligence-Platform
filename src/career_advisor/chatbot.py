"""
src/career_advisor/chatbot.py
Chatbot RAG — Text-to-SQL + ML + Groq (Llama 3.1)
"""

import os
import json
import re
import joblib
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import load_dotenv

try:
    from groq import Groq
except Exception:  # pragma: no cover - fallback for environments without Groq
    Groq = None


def clean_response(text: str) -> str:
    """Supprime les balises <think>...</think> des réponses du LLM."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

# ── Chargement configuration ──────────────────────────────
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if Groq and api_key else None
MODEL_NAME = "llama-3.1-8b-instant"

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


# ── Prompt système ────────────────────────────────────────
SYSTEM_PROMPT = """
Tu es AI Career Assistant, un assistant expert en carrières Data & Intelligence Artificielle.

Tu aides les étudiants et professionnels à :
- Comprendre les métiers Data/IA (Data Scientist, ML Engineer, Data Engineer...)
- Comparer les technologies et frameworks
- Préparer des entretiens techniques
- Choisir des compétences à apprendre
- Comprendre les tendances du marché IA

Pour les statistiques précises (salaires, offres par pays, top compétences),
oriente l'utilisateur vers les tableaux de bord de la plateforme.

Pour les prédictions de salaire personnalisées, tu utilises le modèle ML intégré.
N'invente jamais de chiffres — utilise uniquement les résultats du modèle ML.

Réponds toujours en français, de manière claire et structurée.
"""


# ── Prédiction ML ─────────────────────────────────────────
def predict_salary(params: dict) -> str:
    """Prédit un salaire avec le modèle XGBoost."""
    if not ML_AVAILABLE:
        return "Modèle ML non disponible."

    try:
        skills_list = params.get("skills", [])
        known_skills = [s for s in skills_list if s in skills_encoder.classes_]
        skills_encoded = pd.DataFrame(
            skills_encoder.transform([known_skills]),
            columns=[f"skill_{c}" for c in skills_encoder.classes_]
        )

        input_row = pd.DataFrame(columns=model_columns)
        input_row.loc[0] = 0

        categorical_map = {
            "job_title": params.get("job_title", ""),
            "country": params.get("country", ""),
            "experience_level": params.get("experience_level", ""),
            "is_remote_friendly": params.get("is_remote_friendly", False),
            "job_category": params.get("job_category", ""),
            "employment_type": params.get("employment_type", ""),
            "company_size": params.get("company_size", ""),
            "industry": params.get("industry", ""),
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

        input_row = input_row.fillna(0)
        prediction = np.expm1(ml_model.predict(input_row)[0])
        return f"${prediction:,.0f} USD/an"

    except Exception as e:
        return f"Erreur prédiction : {e}"


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
    Retourne :
    ML ou GENERAL
    """

    prompt = f"""
Tu dois répondre par UN SEUL mot.

ML
GENERAL

ML :
- prédiction
- estimation
- salaire futur
- combien vais-je gagner
- salaire selon mon profil
- prédire

GENERAL :
Toutes les autres questions.

Question :

{question}

Réponse :
"""

    if client is None:
        return "GENERAL"

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0,
            max_tokens=5
        )
    except Exception as exc:
        print(f"Erreur detect_intent : {exc}")
        return "GENERAL"

    return response.choices[0].message.content.strip().upper()


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
    if client is None:
        answer = "L'assistant IA n'est pas disponible pour le moment. Vérifiez votre clé GROQ_API_KEY pour activer le chatbot."
        history.append({"role": "user", "content": question})
        history.append({"role": "assistant", "content": answer})
        return answer, history

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

    answer = ""

    if intent == "ML":
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.3,
                max_tokens=1200
            )
            llm_response = clean_response(
                response.choices[0].message.content
            )
        except Exception as exc:
            print(f"Erreur génération ML: {exc}")
            answer = "Le service de génération est momentanément indisponible. Veuillez réessayer plus tard."
            history.append({"role": "user", "content": question})
            history.append({"role": "assistant", "content": answer})
            return answer, history

        params = extract_ml_params(llm_response)

        if params:
            prediction = predict_salary(params)

            try:
                final = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                    *messages,
                    {
                        "role": "assistant",
                        "content": llm_response
                    },
                    {
                        "role": "user",
                        "content":
                        f"""
Le modèle ML prédit :

{prediction}

Explique simplement cette prédiction.
Donne également quelques conseils de carrière.
"""
                    }
                ]
                )

                answer = clean_response(
                    final.choices[0].message.content
                )
            except Exception as exc:
                print(f"Erreur génération finale ML: {exc}")
                answer = "La prédiction n'a pas pu être complétée. Veuillez réessayer plus tard."

        else:
            answer = "Je n'ai pas réussi à effectuer la prédiction."

        answer += "\n\n🤖 Source : Modèle Machine Learning"

    else:
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.5,
                max_tokens=1200
            )

            answer = clean_response(
                response.choices[0].message.content
            )
        except Exception as exc:
            print(f"Erreur génération générale: {exc}")
            answer = "Le chatbot n'est pas disponible actuellement. Veuillez réessayer plus tard."

        answer += "\n\n💡 Source : Assistant IA"

    # Mise à jour de l'historique
    history.append({"role": "user", "content": question})
    history.append({"role": "assistant", "content": answer})

    return answer, history


# ── Test rapide ───────────────────────────────────────────
if __name__ == "__main__":
    history = []
    questions = [
        "Quel est le meilleur métier ?",

    ]
    
    for q in questions:
        print(f"\n🧑 {q}")
        response, history = chat(q, history)
        print(f"🤖 {response}")