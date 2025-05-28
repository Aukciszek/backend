from decouple import config as dconfig
from supabase import create_client

try:
    SUPABASE_URL = dconfig("SUPABASE_URL", cast=str)
    SUPABASE_KEY = dconfig("SUPABASE_KEY", cast=str)

    def get_supabase():
        return create_client(str(SUPABASE_URL), str(SUPABASE_KEY))

    supabase = get_supabase()

except:
    supabase = None