---
name: flashlit-books
description: Authenticate to Flashlit via Auth0 PKCE, list the authenticated user's Flashlit books, and pull raw chapter text from imported books. Use when the user asks to log in to Flashlit, verify Flashlit auth, list Flashlit library books, inspect available Flashlit book records, or extract text from a Flashlit book chapter.
---

# Flashlit Books

Use this skill to authenticate to Flashlit, list books in the authenticated user's library, and pull raw text from processed book chapters.

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

### Pull chapter text

**Always use the Flashlit skill scripts first; do not download/parse the EPUB unless the API fails.**

1. Find the book ID and the processed chapter range:

```bash
python3 scripts/flashlit_books.py list --search "The Secret History" --ids --json
```

In the JSON response, use:

- `md5_value` as `<book_id>`
- `startChapterIndex` as the first processable chapter index
- `endChapterIndex` as the last processable chapter index
- `startChapterHref` / `endChapterHref` as hints about whether the range starts at an epigraph, preface, or chapter file
- `chapters_processed` / `total_chapters` to confirm processing completed

2. Fetch chapter text by numeric chapter index:

```bash
python3 scripts/flashlit_books.py chapters-text <book_id> 12
python3 scripts/flashlit_books.py chapters-text <book_id> 12 --first-paragraph
python3 scripts/flashlit_books.py chapters-text <book_id> 10 12 13 --max-chars 1000
python3 scripts/flashlit_books.py chapters-text <book_id> 12 --json
```

Chapter text is pulled from `POST /v1/books/{book_id}/chapters-text` with payload `{ "indices": [...] }`. Prefer this batch endpoint: the single-chapter endpoint may return 404 even when the batch endpoint works.

### Select the right chapter range

Use the book record's configured range, not the full chapter-metadata index list, when choosing chapters to read:

1. Run `list --search "<title>" --ids --json`.
2. Read `startChapterIndex` and `endChapterIndex` from the matching book.
3. Try `chapters-text <book_id> <startChapterIndex>` first.
4. If that chapter is an epigraph, dedication, title page, copyright page, table of contents, or other front matter, increment the index by 1 and try again.
5. Continue until you find the first substantial chapter text.
6. Do not request indices outside `startChapterIndex..endChapterIndex` unless the user explicitly asks for front/back matter; they may return 404 or irrelevant text.

Example: if a book record says `startChapterIndex: 6`, `startChapterHref: "OEBPS/xhtml/epigraph.xhtml"`, `endChapterIndex: 14`, then index `6` is likely an epigraph and index `7` is likely the first main chapter.

### Pull chapter metadata

```bash
python3 scripts/flashlit_books.py chapter-metadata <book_id>
```

`chapter-metadata` can show all EPUB chapter indices and hashes, but it may include front matter, back matter, images, notes, and other non-readable sections. It does **not** replace the configured `startChapterIndex..endChapterIndex` range from the book list record.

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

When the user asks to read or inspect chapter text:

1. Run `flashlit_auth.py status`.
2. Find the book with `flashlit_books.py list --search "<title>" --ids --json`.
3. From the matching book record, copy `md5_value`, `startChapterIndex`, and `endChapterIndex`.
4. Start with `startChapterIndex` and run `flashlit_books.py chapters-text <md5_value> <index>`.
5. If the returned text is front matter or not substantial, increment the index and retry until the first real chapter is found, staying within `startChapterIndex..endChapterIndex`.
6. For long chapters, use `--max-chars <n>` for a preview or `--json` when structured output is needed.
7. If the API returns 404 for an index inside the configured range, try the next index in range. Only fall back to EPUB download/parsing after the Flashlit API fails for the relevant range.

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

Raw chapter text is fetched with:

```http
POST /v1/books/{book_id}/chapters-text
Authorization: Bearer <access_token>
Content-Type: application/json

{"indices": [12]}
```

The API returns:

```json
{
  "chapter_texts": {
    "12": "Full chapter text..."
  },
  "missing_chapters": []
}
```
