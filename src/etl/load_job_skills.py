"""
src/etl/load_job_skills.py

Parse la colonne required_skills_raw de la table jobs
et remplit la table job_skills avec les relations job ↔ skill.

Stratégie :
  1. Splitter sur '|'
  2. Nettoyer les espaces et supprimer les doublons
  3. Si la compétence n'existe pas dans skills → l'ajouter automatiquement
  4. Insérer dans job_skills
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from db.connection import get_connection


def get_or_create_skill(cur, skill_name: str) -> int:
    """
    Retourne l'id d'une compétence.
    Si elle n'existe pas encore dans la table skills, elle est créée.
    """
    cur.execute("SELECT id FROM skills WHERE name = %s;", (skill_name,))
    row = cur.fetchone()

    if row:
        return row[0]

    # Compétence inconnue → on l'ajoute avec catégorie NULL
    cur.execute(
        "INSERT INTO skills (name, category) VALUES (%s, %s) RETURNING id;",
        (skill_name, None)
    )
    return cur.fetchone()[0]


def main():
    conn = get_connection()
    cur = conn.cursor()

    # Récupère toutes les offres qui ont des compétences brutes à parser
    cur.execute("""
        SELECT id, required_skills_raw
        FROM jobs
        WHERE required_skills_raw IS NOT NULL
          AND required_skills_raw != '';
    """)
    jobs = cur.fetchall()
    print(f"{len(jobs)} offres à traiter.")

    inserted     = 0
    skills_added = 0

    for job_id, raw_skills in jobs:
        # 1. Splitter sur '|' et nettoyer
        skills = [s.strip() for s in raw_skills.split("|")]

        # 2. Supprimer les doublons tout en gardant l'ordre
        seen = set()
        unique_skills = []
        for s in skills:
            if s and s not in seen:
                seen.add(s)
                unique_skills.append(s)

        for skill_name in unique_skills:
            # 3. Récupérer ou créer la compétence
            skill_id = get_or_create_skill(cur, skill_name)

            # 4. Insérer dans job_skills (ignorer si déjà existant)
            cur.execute("""
                INSERT INTO job_skills (job_id, skill_id)
                VALUES (%s, %s)
                ON CONFLICT DO NOTHING;
            """, (job_id, skill_id))

            if cur.rowcount == 1:
                inserted += 1

    conn.commit()
    cur.close()
    conn.close()

    print(f"Terminé.")
    print(f"  Relations job_skills insérées : {inserted}")


if __name__ == "__main__":
    main()