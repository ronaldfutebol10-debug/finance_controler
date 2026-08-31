from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

supabase = create_client(supabase_url=SUPABASE_URL,supabase_key=SUPABASE_KEY,)
print("Response", supabase)