"""
src/etl/load_adzuna_jobs.py

ETL Adzuna : collecte les offres Data/IA via l'API Adzuna
pour plusieurs pays et les insère dans la base PostgreSQL.

Pipeline :
  1. Appel API par pays et par métier
  2. Normalisation du pays
  3. Insertion/récupération de la company
  4. Insertion de l'offre dans jobs
  5. Parsing basique des skills depuis la description
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

import requests

sys.path.append(str(Path(__file__).resolve().parent.parent))
from db.connection import get_connection
from utils.country_normalizer import COUNTRY_NORMALIZATION

# ── Configuration ────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

APP_ID  = os.getenv("API_APP_ID")
APP_KEY = os.getenv("API_KEY")

BASE_URL = "https://api.adzuna.com/v1/api/jobs"

# Pays à interroger (code Adzuna)
COUNTRIES = ["gb", "us", "fr", "de", "nl"]

# Métiers à rechercher
JOB_TITLES = [
    "data scientist",
    "data analyst",
    "machine learning engineer",
    "data engineer",
    "AI engineer",
]

RESULTS_PER_PAGE = 50
MAX_PAGES        = 3   # 50 x 3 = 150 offres max par métier par pays


# ── Helpers ──────────────────────────────────────────────────
def fetch_jobs(country_code: str, job_title: str, page: int) -> dict:
    """Appelle l'API Adzuna et retourne le JSON brut."""
    url = f"{BASE_URL}/{country_code}/search/{page}"
    params = {
        "app_id":           APP_ID,
        "app_key":          APP_KEY,
        "what":             job_title,
        "results_per_page": RESULTS_PER_PAGE,
        "content-type":     "application/json",
    }
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def load_country_map(cur) -> dict:
    cur.execute("SELECT id, name FROM countries;")
    return {name: id_ for id_, name in cur.fetchall()}


def get_or_create_company(cur, name: str, country_id: int) -> int:
    """Retourne l'id d'une company, la crée si elle n'existe pas."""
    cur.execute(
        "SELECT id FROM companies WHERE name = %s AND country_id = %s;",
        (name, country_id)
    )
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        "INSERT INTO companies (name, country_id) VALUES (%s, %s) RETURNING id;",
        (name, country_id)
    )
    return cur.fetchone()[0]


def get_or_create_skill(cur, skill_name: str) -> int:
    """Retourne l'id d'une skill, la crée si elle n'existe pas."""
    cur.execute("SELECT id FROM skills WHERE name = %s;", (skill_name,))
    row = cur.fetchone()
    if row:
        return row[0]

    cur.execute(
        "INSERT INTO skills (name, category) VALUES (%s, NULL) RETURNING id;",
        (skill_name,)
    )
    return cur.fetchone()[0]


# Liste de skills connues à rechercher dans la description
SKILLS_TO_DETECT = [
    "Python", "SQL", "R", "Java", "Scala",
    "AWS", "Azure", "GCP", "Docker", "Kubernetes",
    "Power BI", "Tableau", "Excel",
    "TensorFlow", "PyTorch", "Scikit-learn",
    "Pandas", "NumPy", "Spark", "Hadoop",
    "NLP", "LLM", "LangChain", "Hugging Face",
    "Git", "Airflow", "dbt", "Snowflake", "Databricks",
]

def extract_skills_from_description(description: str) -> list:
    """
    Détecte les compétences connues dans le texte de la description.
    Retourne une liste de noms de compétences trouvées.
    """
    if not description:
        return []
    found = []
    desc_lower = description.lower()
    for skill in SKILLS_TO_DETECT:
        if skill.lower() in desc_lower:
            found.append(skill)
    return found


# ── Main ─────────────────────────────────────────────────────
def main():
    conn = get_connection()
    cur  = conn.cursor()

    country_map = load_country_map(cur)

    inserted_jobs   = 0
    skipped_jobs    = 0
    inserted_skills = 0

    for country_code in COUNTRIES:
        for job_title in JOB_TITLES:
            print(f"→ [{country_code.upper()}] {job_title}...")

            for page in range(1, MAX_PAGES + 1):
                try:
                    data = fetch_jobs(country_code, job_title, page)
                except Exception as e:
                    print(f"  Erreur API page {page} : {e}")
                    break

                results = data.get("results", [])
                if not results:
                    break   # plus de résultats disponibles

                for job in results:
                    # ── Pays ──────────────────────────────────
                    area = job.get("location", {}).get("area", [])
                    raw_country = area[0] if area else None

                    country_name = COUNTRY_NORMALIZATION.get(
                        raw_country, raw_country
                    )
                    country_id = country_map.get(country_name) if country_name else None

                    if country_name and country_id is None:
                        cur.execute(
                            "INSERT INTO countries (name) VALUES (%s) RETURNING id;",
                            (country_name,)
                        )
                        country_id = cur.fetchone()[0]
                        country_map[country_name] = country_id

                    # ── Company ───────────────────────────────
                    company_name = job.get("company", {}).get("display_name")
                    company_id   = None
                    if company_name and country_id:
                        company_id = get_or_create_company(
                            cur, company_name, country_id
                        )

                    # ── Date ──────────────────────────────────
                    created_str = job.get("created")
                    posted_date = None
                    if created_str:
                        posted_date = datetime.fromisoformat(
                            created_str.replace("Z", "+00:00")
                        ).date()

                    # ── Insertion job ─────────────────────────
                    cur.execute("""
                        INSERT INTO jobs (
                            external_id, source,
                            job_title, job_category,
                            company_id, country_id, city,
                            salary_min, salary_max,
                            salary_currency, salary_is_predicted,
                            employment_type, contract_time,
                            description, posted_date
                        )
                        VALUES (
                            %s, %s,
                            %s, %s,
                            %s, %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s
                        )
                        ON CONFLICT (external_id, source) DO NOTHING;
                    """, (
                        job.get("id"), "adzuna",
                        job.get("title"),
                        job.get("category", {}).get("label"),
                        company_id, country_id,
                        job.get("location", {}).get("display_name"),
                        job.get("salary_min"), job.get("salary_max"),
                        "GBP" if country_code == "gb" else "USD",
                        job.get("salary_is_predicted") == "1",
                        job.get("contract_type"),
                        job.get("contract_time"),
                        job.get("description"), posted_date,
                    ))

                    if cur.rowcount == 1:
                        inserted_jobs += 1

                        # ── Skills depuis description ─────────
                        job_id = cur.lastrowid
                        # Pour PostgreSQL, on récupère l'id via RETURNING
                        cur.execute(
                            "SELECT id FROM jobs WHERE external_id = %s AND source = 'adzuna';",
                            (job.get("id"),)
                        )
                        row = cur.fetchone()
                        if row:
                            job_db_id = row[0]
                            skills = extract_skills_from_description(
                                job.get("description", "")
                            )
                            for skill_name in skills:
                                skill_id = get_or_create_skill(cur, skill_name)
                                cur.execute("""
                                    INSERT INTO job_skills (job_id, skill_id)
                                    VALUES (%s, %s)
                                    ON CONFLICT DO NOTHING;
                                """, (job_db_id, skill_id))
                                if cur.rowcount == 1:
                                    inserted_skills += 1

                conn.commit()
                time.sleep(0.5)   # pause pour respecter les limites de l'API

    cur.close()
    conn.close()

    print("\n✓ ETL Adzuna terminé.")
    print(f"  Offres insérées     : {inserted_jobs}")
    print(f"  Offres ignorées     : {skipped_jobs}")
    print(f"  Relations job_skills: {inserted_skills}")


if __name__ == "__main__":
    main()