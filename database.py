from supabase import create_client
import os
from dotenv import load_dotenv

SUPABASE_URL = os.getenv['SUPABASE_URL']
SUPABASE_KEY = os.getenv['SUPABASE_KEY']
supabase = create_client(supabase_key=SUPABASE_KEY,supabase_url=SUPABASE_URL)