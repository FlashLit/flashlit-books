#!/usr/bin/env python3
"""Authenticate to Flashlit/Auth0 for the flashlit-books skill."""

from __future__ import annotations

import argparse
import json
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from flashlit_client import (
    API_BASE,
    AUTH0_DOMAIN,
    AUDIENCE,
    CALLBACK_PORT,
    CLIENT_ID,
    REDIRECT_URI,
    TOKEN_PATH,
    FlashlitError,
    b64url,
    build_authorize_url,
    exchange_code,
    get_access_token,
    list_books,
    load_cached_tokens,
    make_pkce,
    save_tokens,
)
import secrets


class CallbackHandler(BaseHTTPRequestHandler):
    auth_code: str | None = None
    auth_error: str | None = None
    expected_state: str | None = None

    def log_message(self, fmt: str, *args):
        return

    def do_GET(self):
        import urllib.parse

        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        handler_cls = type(self)

        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        state = params.get("state", [None])[0]
        if state != handler_cls.expected_state:
            handler_cls.auth_error = "Invalid state returned by Auth0"
        elif "error" in params:
            handler_cls.auth_error = params.get("error_description", params.get("error", ["Unknown error"]))[0]
        else:
            handler_cls.auth_code = params.get("code", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        if handler_cls.auth_error:
            body = f"<h1>Flashlit login failed</h1><p>{handler_cls.auth_error}</p>"
        else:
            body = "<h1>Flashlit login complete</h1><p>You can close this tab and return to the terminal.</p>"
        self.wfile.write(body.encode("utf-8"))


def cmd_login(args: argparse.Namespace) -> int:
    verifier, challenge = make_pkce()
    state = b64url(secrets.token_bytes(32))
    CallbackHandler.auth_code = None
    CallbackHandler.auth_error = None
    CallbackHandler.expected_state = state

    authorize_url = build_authorize_url(challenge, state)

    print("Flashlit Auth0 login")
    print(f"Domain:       {AUTH0_DOMAIN}")
    print(f"Client ID:    {CLIENT_ID}")
    print(f"Audience:     {AUDIENCE}")
    print(f"API base:     {API_BASE}")
    print(f"Callback URL: {REDIRECT_URI}")
    print()
    print("If Auth0 rejects the callback, add this URL to Allowed Callback URLs:")
    print(f"  {REDIRECT_URI}")
    print()
    print("Opening browser. If it does not open, paste this URL manually:")
    print(authorize_url)
    print()

    server = HTTPServer(("localhost", CALLBACK_PORT), CallbackHandler)
    webbrowser.open(authorize_url)

    print("Waiting for Auth0 callback...")
    while CallbackHandler.auth_code is None and CallbackHandler.auth_error is None:
        server.handle_request()
    server.server_close()

    if CallbackHandler.auth_error:
        print(f"Login failed: {CallbackHandler.auth_error}")
        return 1

    print("Received authorization code. Exchanging for tokens...")
    tokens = exchange_code(CallbackHandler.auth_code, verifier)
    save_tokens(tokens)

    print(f"Saved tokens to: {TOKEN_PATH}")
    print(f"Token type: {tokens.get('token_type')}")
    print(f"Expires in: {tokens.get('expires_in')} seconds")
    access_token = tokens.get("access_token") or ""
    print("Access token preview:", access_token[:24] + "..." if access_token else "<none>")
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    try:
        tokens = load_cached_tokens(required=False)
        manual = False
        if tokens is None:
            import os
            manual = bool(os.getenv("FLASHLIT_AUTH_TOKEN"))
            if not manual:
                print(f"Not authenticated. No token cache found at {TOKEN_PATH}")
                print("Run from the flashlit-books skill directory: python3 scripts/flashlit_auth.py login")
                return 1

        token = get_access_token()
        result = list_books(limit=1)
        metadata = result.get("metadata", {}) if isinstance(result, dict) else {}
        print("Authenticated to Flashlit.")
        print(f"Token source: {'FLASHLIT_AUTH_TOKEN env var' if manual else TOKEN_PATH}")
        if tokens and tokens.get("expires_at"):
            remaining = int(tokens["expires_at"] - time.time())
            print(f"Token expires in: {max(0, remaining)} seconds")
        print(f"Total books visible: {metadata.get('total_count', 'unknown')}")
        print("Access token preview:", token[:24] + "...")
        return 0
    except FlashlitError as e:
        print(str(e))
        return 1


def cmd_token(args: argparse.Namespace) -> int:
    try:
        token = get_access_token()
        if args.full:
            print(token)
        else:
            print(token[:24] + "...")
        return 0
    except FlashlitError as e:
        print(str(e))
        return 1


def cmd_logout(args: argparse.Namespace) -> int:
    if TOKEN_PATH.exists():
        TOKEN_PATH.unlink()
        print(f"Deleted token cache: {TOKEN_PATH}")
    else:
        print(f"No token cache found at: {TOKEN_PATH}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Flashlit Auth0 authentication helper")
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="Log in via Auth0 browser PKCE flow")
    login.set_defaults(func=cmd_login)

    status = sub.add_parser("status", help="Check cached token and Flashlit API access")
    status.set_defaults(func=cmd_status)

    token = sub.add_parser("token", help="Print access token preview")
    token.add_argument("--full", action="store_true", help="Print the full token")
    token.set_defaults(func=cmd_token)

    logout = sub.add_parser("logout", help="Delete cached token")
    logout.set_defaults(func=cmd_logout)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
