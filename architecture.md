# Aukciszek Backend Architecture

**Python Version:** Latest (recommended version from [python.org](https://www.python.org/))

**Framework:**  
The backend is built on [FastAPI](https://fastapi.tiangolo.com/) which provides a high-performance API.

**Server Communication:**

- **Production:**  
  Servers in production can communicate with each other over **HTTPS** to ensure secure data transmission.

- **Alternative Communication:**  
  There is also an option to establish communication over **WireGuard**. This method is fully described in the `wireguard` branch.
