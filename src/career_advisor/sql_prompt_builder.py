def build_prompt(question: str, db_context: str, sql_type: str) -> str:
    prompt = f"""
Tu es un expert PostgreSQL.

Base :

{db_context}

Question :

{question}
"""

    if sql_type == "growth":
        prompt += """

Tu réponds à une question d'évolution temporelle.

Utilise posting_year.
Compare les années.
Calcule la croissance.
N'invente aucune colonne.
"""

    elif sql_type == "salary":
        prompt += """

Tu réponds à une question sur les salaires.

Utilise salary_avg.
Ignore les NULL.
Ne joins jamais salary_avg avec companies si aucune relation valide n'existe.
"""

    elif sql_type == "skills":
        prompt += """

Les compétences sont dans :
skills
job_skills

Utilise toujours ces tables.
"""

    elif sql_type == "company":
        prompt += """

Tu réponds à une question sur les entreprises.

Utilise la table companies et sa relation avec jobs.
"""

    elif sql_type == "country":
        prompt += """

Tu réponds à une question sur des pays.

Utilise la table countries.
Utilise exactement les noms de pays présents dans la base.
"""

    prompt += """

Retourne uniquement

<SQL>
...
</SQL>
"""

    return prompt
