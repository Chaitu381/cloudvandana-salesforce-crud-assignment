from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
from dataclasses import asdict, dataclass
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, Request, Response, status

from .config import Settings


@dataclass
class SalesforceSession:
    access_token: str
    refresh_token: str | None
    instance_url: str
    identity_url: str | None = None
    display_name: str | None = None
    username: str | None = None
    user_id: str | None = None
    organization_id: str | None = None
    issued_at: int = 0


class SecureCodec:
    def __init__(self, secret: str):
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
        self._fernet = Fernet(key)

    def dumps(self, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return self._fernet.encrypt(raw).decode("ascii")

    def loads(self, token: str, *, max_age: int | None = None) -> dict[str, Any]:
        try:
            raw = self._fernet.decrypt(token.encode("ascii"), ttl=max_age)
            value = json.loads(raw.decode("utf-8"))
        except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid or expired secure token") from exc
        if not isinstance(value, dict):
            raise ValueError("Invalid secure token payload")
        return value


def codec(settings: Settings) -> SecureCodec:
    return SecureCodec(settings.session_secret)


def new_oauth_transaction(settings: Settings) -> tuple[str, str, str]:
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
    payload = {"state": state, "verifier": verifier, "created_at": int(time.time())}
    return state, challenge, codec(settings).dumps(payload)


def parse_oauth_transaction(settings: Settings, value: str | None) -> dict[str, Any]:
    if not value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth transaction cookie is missing")
    try:
        return codec(settings).loads(value, max_age=settings.oauth_max_age_seconds)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="OAuth transaction is invalid or expired") from exc


def encode_session(settings: Settings, session: SalesforceSession) -> str:
    return codec(settings).dumps(asdict(session))


def decode_session(settings: Settings, value: str | None) -> SalesforceSession | None:
    if not value:
        return None
    try:
        data = codec(settings).loads(value, max_age=settings.session_max_age_seconds)
        return SalesforceSession(**data)
    except (ValueError, TypeError):
        return None


def get_session_from_request(request: Request, settings: Settings) -> SalesforceSession:
    session = decode_session(settings, request.cookies.get(settings.session_cookie_name))
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Salesforce login required")
    return session


def set_session_cookie(response: Response, settings: Settings, session: SalesforceSession) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=encode_session(settings, session),
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def encode_cursor(settings: Settings, payload: dict[str, Any]) -> str:
    return codec(settings).dumps({"kind": "cursor", **payload})


def decode_cursor(settings: Settings, value: str) -> dict[str, Any]:
    try:
        payload = codec(settings).loads(value, max_age=86400)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid or expired pagination cursor") from exc
    if payload.get("kind") != "cursor":
        raise HTTPException(status_code=400, detail="Invalid pagination cursor")
    return payload
