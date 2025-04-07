# Aukciszek Backend

## How to Start the Backend

To start the backend, run the following command:

```bash
uv run uvicorn api.__init__:app --port PORT
```

You need to run this command in five different terminals, each with a different port. For example:

Terminal 1: `uv run uvicorn api.__init__:app --port 5001`

Terminal 2: `uv run uvicorn api.__init__:app --port 5002`

Terminal 3: `uv run uvicorn api.__init__:app --port 5003`

Terminal 4: `uv run uvicorn api.__init__:app --port 5004`

Terminal 5: `uv run uvicorn api.__init__:app --port 5005`

## How to Test the Backend

To test the backend, run the following command:

```bash
uv run python tests/__init__.py
```
