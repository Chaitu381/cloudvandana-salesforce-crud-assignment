from __future__ import annotations

import hmac
import time
from urllib.parse import quote, urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse

from app.core.config import Settings, get_settings
from app.core.security import (
    SalesforceSession,
    clear_session_cookie,
    decode_session,
    new_oauth_transaction,
    parse_oauth_transaction,
    set_session_cookie,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/status")
async def auth_status(request: Request, settings: Settings = Depends(get_settings)):
    session = decode_session(settings, request.cookies.get(settings.session_cookie_name))
    return {
        "authenticated": bool(session),
        "salesforceConfigured": settings.is_salesforce_configured,
        "user": None if not session else {
            "displayName": session.display_name,
            "username": session.username,
            "userId": session.user_id,
            "organizationId": session.organization_id,
        },
    }


@router.get("/login")
async def login(settings: Settings = Depends(get_settings)):
    if not settings.is_salesforce_configured:
        raise HTTPException(status_code=503, detail="Salesforce OAuth is not configured on the server")

    state, challenge, transaction = new_oauth_transaction(settings)
    params = {
        "response_type": "code",
        "client_id": settings.sf_client_id,
        "redirect_uri": settings.callback_url,
        "scope": settings.sf_scopes,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }
    response = RedirectResponse(f"{settings.oauth_authorize_url}?{urlencode(params)}", status_code=302)
    response.set_cookie(
        settings.oauth_cookie_name,
        transaction,
        max_age=settings.oauth_max_age_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
    return response


@router.get("/callback")
async def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    settings: Settings = Depends(get_settings),
):
    if error:
        detail = error_description or error
        return RedirectResponse(f"{settings.frontend_url}/?oauth_error={quote(detail, safe='')}", status_code=302)
    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing OAuth authorization code or state")

    tx = parse_oauth_transaction(settings, request.cookies.get(settings.oauth_cookie_name))
    if not hmac.compare_digest(str(tx.get("state", "")), state):
        raise HTTPException(status_code=400, detail="OAuth state validation failed")

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": settings.sf_client_id,
        "redirect_uri": settings.callback_url,
        "code_verifier": tx["verifier"],
    }
    if settings.sf_client_secret:
        data["client_secret"] = settings.sf_client_secret

    async with httpx.AsyncClient(timeout=settings.api_timeout_seconds) as client:
        token_response = await client.post(settings.oauth_token_url, data=data)
    if token_response.status_code >= 400:
        try:
            detail = token_response.json().get("error_description") or token_response.json().get("error")
        except ValueError:
            detail = "Salesforce token exchange failed"
        raise HTTPException(status_code=502, detail=detail)

    token = token_response.json()
    identity = {}
    identity_url = token.get("id")
    if identity_url:
        try:
            async with httpx.AsyncClient(timeout=settings.api_timeout_seconds) as client:
                identity_response = await client.get(identity_url, headers={"Authorization": f"Bearer {token['access_token']}"})
            if identity_response.is_success:
                identity = identity_response.json()
        except httpx.HTTPError:
            identity = {}

    session = SalesforceSession(
        access_token=token["access_token"],
        refresh_token=token.get("refresh_token"),
        instance_url=token["instance_url"].rstrip("/"),
        identity_url=identity_url,
        display_name=identity.get("display_name"),
        username=identity.get("username"),
        user_id=identity.get("user_id"),
        organization_id=identity.get("organization_id"),
        issued_at=int(time.time()),
    )
    response = RedirectResponse(settings.frontend_url, status_code=302)
    set_session_cookie(response, settings, session)
    response.delete_cookie(settings.oauth_cookie_name, path="/")
    return response


@router.post("/logout")
async def logout(request: Request, settings: Settings = Depends(get_settings)):
    session = decode_session(settings, request.cookies.get(settings.session_cookie_name))
    if session:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(settings.oauth_revoke_url, data={"token": session.access_token})
        except httpx.HTTPError:
            pass
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response, settings)
    return response
