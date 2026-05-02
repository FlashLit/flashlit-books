---
name: flashlit-books
description: Authenticate to Flashlit via Auth0 PKCE and list the authenticated user's Flashlit books. Use when the user asks to log in to Flashlit, verify Flashlit auth, list Flashlit library books, or inspect available Flashlit book records.
---

# Flashlit Books

Use this skill to authenticate to Flashlit and list books in the authenticated user's library.

## Safety and privacy

- Never print full access tokens, refresh tokens, or ID tokens unless the user explicitly asks.
- Tokens are cached at `~/.config/flashlit-pi/auth.json` with `0600` permissions.
- Use browser-based Auth0 PKCE login; do not ask for or store the user's password.

## Configuration

Defaults are built into the scripts:

- Auth0 domain: `dev-ypldsmybqxh0wmid.us.auth0.com`
- Auth0 client ID: `TXj8I6oAsTurU6sBzxVS8CC2pARBQ6uR`
- Auth0 audience: `https://api.flashlit.ai:7400`
- Flashlit API base: `https://api.flashlit.ai`
- Local callback: `http://localhost:8765/callback`

Optional environment overrides:

```bash
export FLASHLIT_AUTH0_DOMAIN="dev-ypldsmybqxh0wmid.us.auth0.com"
export FLASHLIT_AUTH0_CLIENT_ID="TXj8I6oAsTurU6sBzxVS8CC2pARBQ6uR"
export FLASHLIT_AUTH0_AUDIENCE="https://api.flashlit.ai:7400"
export FLASHLIT_API_BASE="https://api.flashlit.ai"
export FLASHLIT_AUTH_CALLBACK_PORT="8765"
export FLASHLIT_AUTH_CACHE="~/.config/flashlit-pi/auth.json"
```

A manual token can be used as a fallback:

```bash
export FLASHLIT_AUTH_TOKEN="<access-token>"
```

## Commands

Commands below assume the current directory is this skill directory (`~/.pi/agent/skills/flashlit-books`). You can also use absolute paths.

### Login

```bash
python3 scripts/flashlit_auth.py login
```

This opens the browser, completes Auth0 login via PKCE, and saves the token cache.

If Auth0 rejects the callback, add this allowed callback URL to the Auth0 app:

```text
http://localhost:8765/callback
```

### Check auth status

```bash
python3 scripts/flashlit_auth.py status
```

This verifies the cached token by calling the Flashlit books endpoint.

### List books

```bash
python3 scripts/flashlit_books.py list --limit 10
```

Useful options:

```bash
python3 scripts/flashlit_books.py list --limit 25
python3 scripts/flashlit_books.py list --search "plato" --limit 20
python3 scripts/flashlit_books.py list --json --limit 5
python3 scripts/flashlit_books.py list --not-imported --limit 10
```

### Logout

```bash
python3 scripts/flashlit_auth.py logout
```

Deletes the cached token file.

## Workflow

When the user asks to list Flashlit books:

1. Run `flashlit_auth.py status`.
2. If not authenticated, run `flashlit_auth.py login` or ask the user to run it if browser interaction is required.
3. Run `flashlit_books.py list` with the requested filters/limit.
4. Summarize the returned book titles, authors, activation state, and processing state.

## Endpoint details

Books are listed with:

```http
GET /v1/books/?skip=0&limit=20&sort_by=created_at&sort_order=-1&show_imported=true
Authorization: Bearer <access_token>
```

The API returns paginated data:

```json
{
  "data": [
    {
      "title": "...",
      "author": "...",
      "md5_value": "...",
      "isFlashlitActivated": true,
      "processing_status": "completed"
    }
  ],
  "metadata": {
    "total_count": 119,
    "page_size": 10
  }
}
```
