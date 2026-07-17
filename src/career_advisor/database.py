import pandas as pd
from db.connection import get_connection


def get_database_schema(conn) -> pd.DataFrame:
    query = """
    SELECT
        table_name,
        column_name,
        data_type
    FROM information_schema.columns
    WHERE table_schema='public'
    ORDER BY table_name, ordinal_position;
    """
    return pd.read_sql(query, conn)


def get_reference_data(conn):
    countries = pd.read_sql(
        "SELECT DISTINCT name FROM countries ORDER BY name;",
        conn
    )

    jobs = pd.read_sql(
        """
        SELECT DISTINCT job_title
        FROM jobs
        WHERE job_title IS NOT NULL
        ORDER BY job_title
        LIMIT 100
        """,
        conn
    )

    skills = pd.read_sql(
        """
        SELECT DISTINCT name
        FROM skills
        ORDER BY name
        LIMIT 100
        """,
        conn
    )

    return countries, jobs, skills


def build_database_context(conn) -> str:
    schema = get_database_schema(conn)
    countries, jobs, skills = get_reference_data(conn)

    context = "DATABASE SCHEMA\n\n"

    for table in schema["table_name"].unique():
        context += f"\nTable {table}\n"
        cols = schema[schema.table_name == table]
        for _, row in cols.iterrows():
            context += f"- {row.column_name} ({row.data_type})\n"

    context += "\nCountries:\n"
    context += "\n".join(countries["name"])

    context += "\n\nJob titles:\n"
    context += "\n".join(jobs["job_title"])

    context += "\n\nSkills:\n"
    context += "\n".join(skills["name"])

    return context


def get_database_context() -> str:
    """
    Retourne un résumé de la base pour aider le LLM
    """

    conn = get_connection()

    tables = pd.read_sql(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema='public';
        """,
        conn
    )

    columns = pd.read_sql(
        """
        SELECT table_name,column_name
        FROM information_schema.columns
        WHERE table_schema='public'
        ORDER BY table_name,column_name;
        """,
        conn
    )

    countries = pd.read_sql(
        """
        SELECT name
        FROM countries
        ORDER BY name;
        """,
        conn
    )

    years = pd.read_sql(
        """
        SELECT DISTINCT posting_year
        FROM jobs
        WHERE posting_year IS NOT NULL
        ORDER BY posting_year;
        """,
        conn
    )

    sources = pd.read_sql(
        """
        SELECT DISTINCT source
        FROM jobs;
        """,
        conn
    )

    conn.close()

    context = f"""
DATABASE SCHEMA

Tables:
{tables.to_string(index=False)}

Columns:
{columns.to_string(index=False)}

Countries:
{countries.to_string(index=False)}

Posting years:
{years.to_string(index=False)}

Sources:
{sources.to_string(index=False)}
"""

    return context
