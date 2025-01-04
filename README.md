# Aukciszek Backend

## How to Start the Backend

To start the backend, run the following command:

```bash
poetry run python api/__init__.py --port=PORT
```

You need to run this command in five different terminals, each with a different port. For example:

Terminal 1: `poetry run python api/__init__.py --port=5000`

Terminal 2: `poetry run python api/__init__.py --port=5001`

Terminal 3: `poetry run python api/__init__.py --port=5002`

Terminal 4: `poetry run python api/__init__.py --port=5003`

Terminal 5: `poetry run python api/__init__.py --port=5004`

## How to Test the Backend

To test the backend, run the following command:

```bash
poetry run python tests/__init__.py
```
