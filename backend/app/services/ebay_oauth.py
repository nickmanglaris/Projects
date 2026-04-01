"""
eBay OAuth2 service skeleton.
Handles authorization URL generation, callback token exchange, and token refresh.
Tokens are stored encrypted in the app_config table.
"""
import json
import secrets
from datetime import datetime, timedelta
from typing import Optional

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.app_config import AppConfig


def _get_fernet() -> Fernet:
    key = settings.SECRET_KEY.encode().ljust(32)[:32]
    import base64
    fernet_key = base64.urlsafe_b64encode(key)
    return Fernet(fernet_key)


async def _get_config(db: AsyncSession, key: str) -> Optional[str]:
    result = await db.execute(select(AppConfig).where(AppConfig.key == key))
    row = result.scalar_one_or_none()
    return row.value if row else None


async def _set_config(db: AsyncSession, key: str, value: str):
    result = await db.execute(select(AppConfig).where(AppConfig.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = value
    else:
        db.add(AppConfig(key=key, value=value))
    await db.commit()


def get_auth_url(state: str) -> str:
    base = "https://auth.sandbox.ebay.com" if settings.EBAY_SANDBOX else "https://auth.ebay.com"
    scopes = "https://api.ebay.com/oauth/api_scope https://api.ebay.com/oauth/api_scope/buy.order.readonly https://api.ebay.com/oauth/api_scope/sell.finances"
    params = (
        f"?client_id={settings.EBAY_CLIENT_ID}"
        f"&redirect_uri={settings.EBAY_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={scopes}"
        f"&state={state}"
    )
    return f"{base}/oauth2/authorize{params}"


async def generate_auth_url(db: AsyncSession) -> str:
    state = secrets.token_urlsafe(16)
    await _set_config(db, "ebay_oauth_state", state)
    return get_auth_url(state)


async def handle_callback(db: AsyncSession, code: str, state: str) -> dict:
    stored_state = await _get_config(db, "ebay_oauth_state")
    if stored_state != state:
        raise ValueError("Invalid OAuth state parameter")

    base = "https://api.sandbox.ebay.com" if settings.EBAY_SANDBOX else "https://api.ebay.com"
    import httpx, base64
    credentials = base64.b64encode(
        f"{settings.EBAY_CLIENT_ID}:{settings.EBAY_CLIENT_SECRET}".encode()
    ).decode()

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{base}/identity/v1/oauth2/token",
            headers={
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": settings.EBAY_REDIRECT_URI,
            },
        )
        resp.raise_for_status()
        token_data = resp.json()

    f = _get_fernet()
    encrypted = f.encrypt(json.dumps(token_data).encode()).decode()
    await _set_config(db, "ebay_token", encrypted)
    return {"connected": True}


async def get_auth_status(db: AsyncSession) -> dict:
    token_str = await _get_config(db, "ebay_token")
    if not token_str:
        return {"connected": False, "expires_at": None}
    try:
        f = _get_fernet()
        token_data = json.loads(f.decrypt(token_str.encode()).decode())
        return {"connected": True, "expires_at": token_data.get("expires_in")}
    except Exception:
        return {"connected": False, "expires_at": None}


async def disconnect(db: AsyncSession):
    await _set_config(db, "ebay_token", "")
