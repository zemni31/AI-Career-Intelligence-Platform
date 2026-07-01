"""
src/db/connection.py

Gère la connexion à la base PostgreSQL du projet AI Career Intelligence Platform.
Toutes les variables sensibles (host, user, password...) sont lues depuis le
fichier .env à la racine du projet -- jamais codées en dur ici.
"""

import os
from pathlib import Path

import psycopg2
from psycopg2.extensions import connection as PGConnection
from dotenv import load_dotenv

# Charge le fichier .env situé à la racine du projet,
# peu importe d'où ce script est appelé.
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)


def get_connection() -> PGConnection:
    """
    Ouvre et retourne une connexion à la base PostgreSQL définie dans .env.
    """
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
    )
    return conn


def test_connection() -> None:
    """
    Vérifie rapidement que la connexion fonctionne.
    Affiche la version de PostgreSQL si tout va bien.
    """
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print("Connexion réussie à PostgreSQL.")
        print("Version :", version[0])
        cur.close()
        conn.close()
    except Exception as e:
        print("Échec de la connexion à PostgreSQL.")
        print("Détail de l'erreur :", e)


if __name__ == "__main__":
    test_connection()
    