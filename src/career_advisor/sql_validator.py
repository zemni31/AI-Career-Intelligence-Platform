import re

import pandas as pd
from db.connection import get_connection
from utils.country_normalizer import COUNTRY_NORMALIZATION

FORBIDDEN_KEYWORDS = ["INSERT ", "UPDATE ", "DELETE ", "DROP ", "TRUNCATE ", "ALTER "]
SQL_KEYWORDS = {
    "SELECT", "FROM", "WHERE", "JOIN", "ON", "GROUP", "ORDER", "BY", "LIMIT",
    "HAVING", "AS", "AND", "OR", "IN", "IS", "NOT", "NULL", "CASE", "WHEN",
    "THEN", "ELSE", "END", "DISTINCT", "BETWEEN", "EXISTS", "UNION"
}


def get_schema_info() -> pd.DataFrame:
    conn = get_connection()
    try:
        schema = pd.read_sql(
            """
            SELECT table_name, column_name
            FROM information_schema.columns
            WHERE table_schema='public'
            """,
            conn
        )
        return schema
    finally:
        conn.close()


def normalize_country_values(query: str) -> str:
    normalized = query
    for short, full in COUNTRY_NORMALIZATION.items():
        if not full:
            continue

        normalized = re.sub(
            rf"(['\"])({re.escape(short)})\1",
            rf"\1{full}\1",
            normalized,
            flags=re.IGNORECASE
        )

        normalized = re.sub(
            rf"\b{re.escape(short)}\b",
            full,
            normalized,
            flags=re.IGNORECASE
        )

    return normalized


def extract_tables(query: str) -> list[str]:
    matches = re.findall(r"\b(?:FROM|JOIN)\s+([a-zA-Z0-9_\.]+)", query, re.IGNORECASE)
    return [m.split(".")[-1].strip() for m in matches if m]


def extract_aliases(query: str) -> dict[str, str]:
    aliases = {}
    for match in re.findall(r"\b(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)\s+([a-zA-Z0-9_]+)\b", query, re.IGNORECASE):
        table, alias = match
        aliases[alias] = table
    return aliases


def extract_qualified_columns(query: str) -> list[tuple[str, str]]:
    return re.findall(r"\b([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\b", query)


def extract_unqualified_columns(query: str) -> list[str]:
    tokens = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b", query)
    return [t for t in tokens if t.upper() not in SQL_KEYWORDS]


def validate_sql(query: str) -> tuple[str | None, str | None]:
    if not query:
        return None, "Requête vide."

    sql = query.strip()
    sql_upper = sql.upper()

    if not sql_upper.startswith("SELECT"):
        return None, "Seules les requêtes SELECT sont autorisées."

    if any(word in sql_upper for word in FORBIDDEN_KEYWORDS):
        return None, "Seules les requêtes SELECT sont autorisées."

    sql = normalize_country_values(sql)

    try:
        schema = get_schema_info()
    except Exception as e:
        return None, f"Impossible de valider la requête SQL : {e}"

    table_names = set(schema["table_name"].unique())
    table_columns = {}
    for _, row in schema.iterrows():
        table_columns.setdefault(row["table_name"], set()).add(row["column_name"])

    tables = extract_tables(sql)
    for table in tables:
        if table not in table_names:
            return None, f"Table inconnue : {table}."

    aliases = extract_aliases(sql)
    qualified_columns = extract_qualified_columns(sql)
    for alias, column in qualified_columns:
        table_name = aliases.get(alias, alias)
        if table_name not in table_names:
            return None, f"Table inconnue pour l'alias : {alias}."
        if column not in table_columns.get(table_name, set()):
            return None, f"Colonne inconnue : {alias}.{column}."

    return sql, None


def correct_sql_with_llm(query: str, error_message: str, db_context: str, client) -> str | None:
    prompt = f"""
La requête SQL suivante a échoué sur PostgreSQL.

Contexte de la base :
{db_context}

Requête SQL :
{query}

Erreur PostgreSQL :
{error_message}

Corrige la requête pour qu'elle soit compatible avec la base de données.
Conserve l'intention de la question.
Ne modifie que ce qui est nécessaire.
Retourne uniquement la requête SQL entre <SQL> et </SQL>.
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
        max_tokens=300
    )

    content = response.choices[0].message.content
    match = re.search(r"<SQL>(.*?)</SQL>", content, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    return None
