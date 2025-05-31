# Aukciszek Backend

Aukciszek backend implements a Multi-Party Computation (MPC) protocol, specifically designed based on the principles outlined in the publication "Secure Multiparty Computation Goes Live" (https://eprint.iacr.org/2008/068.pdf). This foundational paper describes practical techniques for achieving secure multi-party computation, where multiple parties can jointly compute a function over their private inputs without revealing those inputs to each other. It's important to note that this backend specifically implements the comparison functionality as described in the paper, leveraging the distributed and collaborative nature inherent in MPC protocols.

## 🚀 Getting Started

To run the Aukciszek backend, it's **recommended** to use [`uv`](https://docs.astral.sh/uv/getting-started/installation/) — a fast Python package and script runner.

---

## 📦 Prerequisites

Install `uv` by following the official guide:  
👉 https://docs.astral.sh/uv/getting-started/installation/

---

## 🔧 Running the Backend

You’ll need to run **five separate backend instances**, each in its own terminal window and on a different port.

### Key Concepts

- Only **Terminal 1** acts as the **login server**, requiring a valid `SUPABASE_URL`, `SUPABASE_KEY`, and the **full** `SECRET_KEYS_JWT` list.
- Other terminals act as additional backend nodes and only need their corresponding JWT key in the appropriate position of the list. The rest of the entries should be `None`.
- The order of servers in the `SERVERS` environment variable must match the order of JWT keys in `SECRET_KEYS_JWT`.
- The order of keys in `SECRET_KEYS_JWT` corresponds to the order of servers defined in the `SERVERS` environment variable (e.g., `SERVERS='http://localhost:5001, http://localhost:5002, http://localhost:5003, http://localhost:5004, http://localhost:5005'`).

> **Example**:  
> If a server is running on `localhost:5003`, it corresponds to the **third** key in the `SECRET_KEYS_JWT` list.

---

### 🖥️ Terminal Commands

#### Terminal 1 (Login Server)

```bash
export SUPABASE_URL="your_supabase_url"
export SUPABASE_KEY="your_supabase_key"
export SECRET_KEYS_JWT="server_1_key,server_2_key,server_3_key,server_4_key,server_5_key"
uv run uvicorn api.__init__:app --port 5001
```

#### Terminal 2

```bash
export SECRET_KEYS_JWT="server_2_key,None,None,None,None"
uv run uvicorn api.__init__:app --port 5002
```

#### Terminal 3

```bash
export SECRET_KEYS_JWT="server_3_key,None,None,None,None"
uv run uvicorn api.__init__:app --port 5003
```

#### Terminal 4

```bash
export SECRET_KEYS_JWT="server_4_key,None,None,None,None"
uv run uvicorn api.__init__:app --port 5004
```

#### Terminal 5

```bash
export SECRET_KEYS_JWT="server_5_key,None,None,None,None"
uv run uvicorn api.__init__:app --port 5005
```

---

### 📖 API Documentation

Once the server is running, you can access the API documentation at `http://localhost:5001/docs`

---

## 🧪 Running Tests

To run the backend tests:

```bash
uv run python tests/__init__.py
```
