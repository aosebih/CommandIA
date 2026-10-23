"""
Manual check of the Supabase connection.

It needs the supabase package (requirements-dev.txt) and real credentials in
the .env, so it skips itself instead of failing at import time when they are
missing.

    python backend/test_db.py
"""
import os
import sys

from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def credentials_are_real():
    for value in (SUPABASE_URL, SUPABASE_KEY):
        if not value:
            return False
        stripped = value.strip().strip("'\"").lower()
        if stripped.startswith("your_") and stripped.endswith("_here"):
            return False
    return True


def test_connection():
    """Fetch the merchants from the database."""
    from supabase import Client, create_client

    if not credentials_are_real():
        print("Supabase is not configured, nothing to check.")
        return None

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    response = supabase.table("merchants").select("*").execute()
    print("Connection Successful! Merchants in DB:", response.data)
    return response.data


if __name__ == "__main__":
    try:
        test_connection()
    except ImportError:
        print("The supabase package is missing: pip install -r requirements-dev.txt")
        sys.exit(1)
