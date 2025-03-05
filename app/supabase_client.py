import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_API_KEY = os.getenv('SUPABASE_API_KEY')

supabase: Client = create_client(SUPABASE_URL, SUPABASE_API_KEY)
