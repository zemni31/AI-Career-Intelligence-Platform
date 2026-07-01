"""
src/etl/load_kaggle_ai_jobs.py

ETL amélioré (Méthode 2) :
  1. Normalisation des noms de pays
  2. Chargement de la map countries depuis la base
  3. Insertion de toutes les offres dans jobs
"""

import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent.parent))
from db.connection import get_connection
from utils.country_normalizer import COUNTRY_NORMALIZATION
DATA_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "raw" / "ai_jobs_market_2025_2026.csv"




def load_country_map(cur) -> dict:
    cur.execute("SELECT id, name FROM countries;")
    rows = cur.fetchall()
    return {name: id_ for id_, name in rows}


def main():
    print("Lecture du fichier CSV...")
    df = pd.read_csv(DATA_PATH)
    print(f"{len(df)} lignes trouvées.")

    conn = get_connection()
    cur = conn.cursor()

    country_map = load_country_map(cur)

    inserted = 0
    skipped  = 0

    for _, row in df.iterrows():
        # Normalisation du nom de pays
        raw_country = row["country"]
        country_name = COUNTRY_NORMALIZATION.get(raw_country, raw_country)
        country_id = country_map.get(country_name) if country_name else None

        # Si le pays est inconnu (ni normalisé, ni dans la base) → on skip
        if country_name is not None and country_id is None:
            skipped += 1
            continue

        cur.execute(
            """
            INSERT INTO jobs (
                external_id, source, job_title, job_category,
                country_id, city,
                salary_min, salary_max, salary_avg, salary_currency,
                experience_level, years_of_experience, education_required,
                company_size, industry,
                required_skills_raw,
                demand_score, demand_growth_yoy_pct,
                ai_salary_premium_pct, benefits_score_10,
                is_llm_role, is_remote_friendly, salary_tier,
                posting_year, posting_month
            )
            VALUES (
                %s, %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s,
                %s, %s,
                %s, %s,
                %s, %s, %s,
                %s, %s
            )
            ON CONFLICT (external_id, source) DO NOTHING;
            """,
            (
                row["job_id"], "kaggle_ai_jobs", row["job_title"], row["job_category"],
                country_id, row["city"],
                row["salary_min_usd"], row["salary_max_usd"], row["annual_salary_usd"], "USD",
                row["experience_level"], row["years_of_experience"], row["education_required"],
                row["company_size"], row["industry"],
                row["required_skills"],
                row["demand_score"], row["demand_growth_yoy_pct"],
                row["ai_salary_premium_pct"], row["benefits_score_10"],
                bool(row["is_llm_role"]), bool(row["is_remote_friendly"]), row["salary_tier"],
                row["posting_year"], row["posting_month"],
            ),
        )
        if cur.rowcount == 1:
            inserted += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"Terminé. {inserted} lignes insérées, {skipped} lignes ignorées (pays inconnu).")


if __name__ == "__main__":
    main()