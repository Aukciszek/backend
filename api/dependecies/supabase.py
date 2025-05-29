from decouple import config as dconfig
from supabase import create_client

try:
    SUPABASE_URL = dconfig("SUPABASE_URL", cast=str)
except Exception:
    SUPABASE_URL = None

try:
    SUPABASE_KEY = dconfig("SUPABASE_KEY", cast=str)
except Exception:
    SUPABASE_KEY = None


def get_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None

    return create_client(str(SUPABASE_URL), str(SUPABASE_KEY))


supabase = get_supabase()
