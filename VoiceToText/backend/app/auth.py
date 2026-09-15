import uuid
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.config import settings

bearer = HTTPBearer()
_jwks_client: jwt.PyJWKClient | None = None


def jwks_client() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(f"{settings().supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json")
    return _jwks_client


async def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)) -> uuid.UUID:
    try:
        token = credentials.credentials
        header = jwt.get_unverified_header(token)
        if header.get("alg") not in ("RS256", "ES256"):
            raise ValueError("Unsupported token algorithm")
        key = jwks_client().get_signing_key_from_jwt(token).key
        claims = jwt.decode(token, key, algorithms=[header["alg"]], audience="authenticated", issuer=settings().supabase_jwt_issuer)
        return uuid.UUID(claims["sub"])
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="Invalid session") from exc
