import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def test_connection():
    # Fetch merchants from database
    response = supabase.table("merchants").select("*").execute()
    print("Connection Successful! Merchants in DB:", response.data)

if __name__ == "__main__":
    test_connection()