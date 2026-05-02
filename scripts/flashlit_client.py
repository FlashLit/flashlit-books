#!/usr/bin/env python3
"""Shared Flashlit API/Auth0 helpers for the flashlit-books skill."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

AUTH0_DOMAIN = os.getenv("FLASHLIT_AUTH0_DOMAIN", "dev-ypldsmybqxh0wmid.us.auth0.com")
CLIENT_ID = os.getenv("FLASHLIT_AUTH0_CLIENT_ID", "TXj8I6oAsTurU6sBzxVS8CC2pARBQ6uR")
AUDIENCE = os.getenv("FLASHLIT_AUTH0_AUDIENCE", "https://api.flashlit.ai:7400")
API_BASE = os.getenv("FLASHLIT_API_BASE", "https://api.flashlit.ai").rstrip("/")
CALLBACK_PORT = int(os.getenv("FLASHLIT_AUTH_CALLBACK_PORT", "8765"))
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"
TOKEN_PATH = Path(os.getenv("FLASHLIT_AUTH_CACHE", "~/.config/flashlit-pi/auth.json")).expanduser()


class FlashlitError(RuntimeError):
    pass


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def make_pkce() -> tuple[str, str]:
    verifier = b64url(secrets.token_bytes(64))
    challenge = b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def build_authorize_url(code_challenge: str, state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid profile email offline_access",
        "audience": AUDIENCE,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    return f"https://{AUTH0_DOMAIN}/authorize?{urllib.parse.urlencode(params)}"


def exchange_code(code: str, verifier: str) -> dict[str, Any]:
    payload = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "code_verifier": verifier,
        "redirect_uri": REDIRECT_URI,
    }
    return auth0_post("/oauth/token", payload)


def refresh_tokens(refresh_token: str) -> dict[str, Any]:
    payload = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": refresh_token,
    }
    return auth0_post("/oauth/token", payload)


def auth0_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"https://{AUTH0_DOMAIN}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise FlashlitError(f"Auth0 request failed: HTTP {e.code}: {body}") from e


def save_tokens(tokens: dict[str, Any]) -> None:
    old = load_cached_tokens(required=False) or {}
    if "refresh_token" not in tokens and old.get("refresh_token"):
        tokens["refresh_token"] = old["refresh_token"]

    expires_in = int(tokens.get("expires_in", 0) or 0)
    record = {
        **tokens,
        "expires_at": int(time.time()) + expires_in - 60 if expires_in else 0,
        "auth0_domain": AUTH0_DOMAIN,
        "client_id": CLIENT_ID,
        "audience": AUDIENCE,
        "api_base": API_BASE,
    }
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(json.dumps(record, indent=2), encoding="utf-8")
    os.chmod(TOKEN_PATH, 0o600)


def load_cached_tokens(required: bool = True) -> dict[str, Any] | None:
    if not TOKEN_PATH.exists():
        if required:
            raise FlashlitError(f"Not authenticated. Run: python3 scripts/flashlit_auth.py login")
        return None
    try:
        return json.loads(TOKEN_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        raise FlashlitError(f"Could not read token cache at {TOKEN_PATH}: {e}") from e


def get_access_token() -> str:
    manual = os.getenv("FLASHLIT_AUTH_TOKEN")
    if manual:
        return manual

    tokens = load_cached_tokens(required=True) or {}
    token = tokens.get("access_token")
    if not token:
        raise FlashlitError("Token cache has no access_token. Run login again.")

    expires_at = int(tokens.get("expires_at", 0) or 0)
    if expires_at and time.time() >= expires_at:
        refresh_token = tokens.get("refresh_token")
        if not refresh_token:
            raise FlashlitError("Cached access token expired and no refresh token is available. Run login again.")
        new_tokens = refresh_tokens(refresh_token)
        save_tokens(new_tokens)
        token = new_tokens.get("access_token")
        if not token:
            raise FlashlitError("Refresh succeeded but no access_token was returned.")

    return token


def api_request(path: str, method: str = "GET", body: bytes | None = None, headers: dict[str, str] | None = None) -> Any:
    token = get_access_token()
    req_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=body,
        headers=req_headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            content = resp.read().decode("utf-8")
            if not content:
                return None
            return json.loads(content)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        raise FlashlitError(f"Flashlit API failed: HTTP {e.code}: {error_body}") from e


def list_books(
    skip: int = 0,
    limit: int = 20,
    sort_by: str = "created_at",
    sort_order: int = -1,
    show_imported: bool = True,
    search: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "skip": skip,
        "limit": limit,
        "sort_by": sort_by,
        "sort_order": sort_order,
        "show_imported": str(show_imported).lower(),
    }
    if search:
        params["search"] = search
    return api_request(f"/v1/books/?{urllib.parse.urlencode(params)}")
