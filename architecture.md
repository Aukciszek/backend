# Aukciszek Backend Architecture

**Python Version:** 3.13.3

**Framework:**  
The backend is built on [FastAPI](https://fastapi.tiangolo.com/) (v0.115.12) which provides a high-performance API.

**Important Libraries:**

- **FastAPI:** v0.115.12
- **aiohttp:** v3.12.6
- **argon2-cffi:** v23.1.0
- **passlib:** v1.7.4
- **pydantic (with email support):** v2.11.5
- **pyjwt:** v2.10.1
- **python-decouple:** v3.8
- **supabase:** v2.15.2
- **uvicorn:** v0.34.2

**User Data and Security:**

The backend communicates with **Supabase**, where user data is stored (uid, email, password, and isAdmin). Every endpoint that handles user interactions is protected by middleware, which verifies the user's JWT to ensure proper authentication.

Endpoints used for server-to-server communication are secured by validating that the request comes from a trusted IP, and ensures that the IP from which a request is sent only modifies the assets assigned to it.

**Authentication and Access Control:**

- Only the **Login Server** has access to the full list of JWT keys because it is the sole server that communicates with Supabase, and is trusted by users due to its handling of all JWT keys. Other servers only possess their respective JWT key and do not know any of the other keys or Supabase credentials.

**Server Communication:**

- **Production:**  
  Servers in production communicate with each other over **HTTPS** to ensure secure data transmission. Additionally, servers must not be deployed behind a proxy, so they receive the real client IP. If operating behind a proxy, the server must be configured to use only trusted proxy headers (such as `X-Forwarded-For` or `X-Real-IP`) and must not blindly forward these headers to the backend. (Note: although previous versions supported proxy header configurations, this feature was removed to avoid the risks associated with misconfigured proxies.)
- **Alternative Communication:**  
  There is also an option to establish communication over **WireGuard**. This method is fully described in the `wireguard` branch.
