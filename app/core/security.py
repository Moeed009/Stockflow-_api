from functools import lru_cache

import httpx
from jose import jwt, jwk, JWTError

from app.core.config import settings


@lru_cache
def _get_jwks() -> dict:
    
    url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
    response = httpx.get(url, timeout=10)
    response.raise_for_status()
    return response.json()


def _find_jwk_for_kid(kid: str) -> dict | None:
    jwks = _get_jwks()
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return key
    return None


def _verify_with_jwks(token: str, kid: str, alg: str) -> dict:
    matching_key = _find_jwk_for_kid(kid)
    if matching_key is None:
        raise JWTError(f"No matching JWKS key found for kid={kid}, alg={alg}")

    public_key = jwk.construct(matching_key, algorithm=alg)
    pem = public_key.to_pem().decode("utf-8") if hasattr(public_key, "to_pem") else matching_key
    return jwt.decode(token, pem, algorithms=[alg], audience="authenticated")


def decode_supabase_token(token: str) -> dict:
   
    header = jwt.get_unverified_header(token)
    alg = header.get("alg", "HS256")

    if alg == "HS256":
        
        return jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )

    kid = header.get("kid")
    if not kid:
        raise JWTError("Token header has no 'kid' - cannot look up JWKS key")

    try:
        return _verify_with_jwks(token, kid, alg)
    except JWTError:
       
        _get_jwks.cache_clear()
        return _verify_with_jwks(token, kid, alg)