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

## How to Test the Backend

To test the backend, run the following command:

```bash
uv run python tests/__init__.py
```
