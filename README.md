# Flashlit Books Skill for Pi

A self-contained capability package for Pi that allows the agent to authenticate with Flashlit (via Auth0 PKCE) and list books from the authenticated user's library.

## Features

- **OAuth2/PKCE Authentication:** Secure browser-based login flow.
- **Library Access:** List books, inspect book metadata, and check library status.

## Prerequisites

- Node.js installed.
- Pi agent installed and configured.

## Installation

1. Copy this skill directory to your Pi skills path (e.g., `~/.pi/agent/skills/flashlit-books`).
2. Install dependencies:
   ```bash
   cd ~/.pi/agent/skills/flashlit-books
   npm install
   ```

## Usage

You can invoke this skill as an agent tool or directly via command line:

```bash
# Check authentication status
node scripts/auth.mjs status

# Login
node scripts/auth.mjs login

# List books
node scripts/books.mjs list
```

## Security Note

- **Tokens:** Access tokens are cached locally at `~/.config/flashlit-pi/auth.json` with restricted permissions (0600). Do not commit this file to version control.
- **Privacy:** Only metadata for the authenticated user's books is retrieved and surfaced to the agent.
