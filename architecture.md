# Aukciszek Backend Architecture

**Python Version:** 3.13.3 (recommended version from [python.org](https://www.python.org/))

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

The backend communicates with **Supabase**, where user data is stored (uid, email, password, and isAdmin). Every endpoint that handles user/admin interactions is protected by middleware, which verifies the user's JWT to ensure proper authentication. User passwords are securely hashed using argon2.

Endpoints used for server-to-server communication are secured by validating that the request comes from a trusted IP, and ensures that the IP from which a request is sent only modifies the assets assigned to it.

**Authentication and Access Control:**

- Only the **Login Server** has access to the full list of JWT keys because it is the sole server that communicates with Supabase, and is trusted by users due to its handling of all JWT keys. Other servers only possess their respective JWT key and do not know any of the other keys or Supabase credentials.

**Server Communication:**

- **Production:**  
  In production, servers communicate over HTTPS for secure data transmission. Generally, you shouldn't deploy servers behind a proxy unless it's absolutely essential.
  If a proxy is used, it must be explicitly configured and fully trusted. This trusted proxy is responsible for replacing any existing `X-Forwarded-For` or `X-Real-IP` headers from untrusted sources with the true client's IP address it received. Our recent versions have removed proxy header support to reduce the risk of proxy misconfiguration and potential security vulnerabilities, emphasizing the need for a properly secured and trusted proxy when one is in use.

- **Alternative Communication:**  
  There is also an option to establish communication over **WireGuard**. This method is fully described in the `wireguard` branch.
