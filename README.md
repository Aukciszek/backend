# Aukciszek Backend

## How to Start the Backend

It's recommended to have `uv` installed.

Installation guide: https://docs.astral.sh/uv/getting-started/installation/

To start the backend, run the following command:

```bash
SERVER_ID="ID" uv run uvicorn api.__init__:app --port PORT
```

You need to run this command in five different terminals, each with a different port. For example:

Terminal 1: `SERVER_ID="0" uv run uvicorn api.__init__:app --port 5001`

Terminal 2: `SERVER_ID="1" uv run uvicorn api.__init__:app --port 5002`

Terminal 3: `SERVER_ID="2" uv run uvicorn api.__init__:app --port 5003`

Terminal 4: `SERVER_ID="3" uv run uvicorn api.__init__:app --port 5004`

Terminal 5: `SERVER_ID="4" uv run uvicorn api.__init__:app --port 5005`

To make only one of the servers a valid login server without editing .env file, add more env variables redeclarations. For exaple on Windows:

Terminal 1: $env:SERVER_ID="0"; $env:SUPABASE_URL="correct_url"; $env:SUPABASE_KEY="correct_key"; $env:SECRET_KEYS_JWT="server_0_key, server_1_key, server_2_key, server_3_key, server_4_key"; uv run uvicorn api.__init__:app --port 5001

Terminal 2: $env:SERVER_ID="1"; $env:SUPABASE_URL="None"; $env:SUPABASE_KEY="None"; $env:SECRET_KEYS_JWT="0, server_1_key, 0, 0, 0"; uv run uvicorn api.__init__:app --port 5002

Terminal 3: $env:SERVER_ID="2"; $env:SUPABASE_URL="None"; $env:SUPABASE_KEY="None"; $env:SECRET_KEYS_JWT="0, 0, server_2_key, 0, 0"; uv run uvicorn api.__init__:app --port 5003

Terminal 4: $env:SERVER_ID="3"; $env:SUPABASE_URL="None"; $env:SUPABASE_KEY="None"; $env:SECRET_KEYS_JWT="0, 0, 0, server_3_key, 0"; uv run uvicorn api.__init__:app --port 5004

Terminal 5: $env:SERVER_ID="4"; $env:SUPABASE_URL="None"; $env:SUPABASE_KEY="None"; $env:SECRET_KEYS_JWT="0, 0, 0, 0, server_4_key"; uv run uvicorn api.__init__:app --port 5005

## How to Test the Backend

To test the backend, run the following command:

```bash
uv run python tests/__init__.py
```
