def detect_sql_type(question: str, client) -> str:
    prompt = f"""
Tu es un classificateur.

Classe cette question dans UNE SEULE catégorie.

Catégories :

COUNT
RANKING
GROWTH
SALARY
SKILLS
COMPANY
COUNTRY
TEMPORAL
COMPARISON
OTHER

Question :

{question}

Réponds uniquement par le nom de la catégorie.
"""

    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0,
        max_tokens=5
    )

    return response.choices[0].message.content.strip().upper()
