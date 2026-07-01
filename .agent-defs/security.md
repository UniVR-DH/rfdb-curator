# Security

## Never Commit Secrets

- ❌ Never commit passwords, API keys, or tokens
- ❌ Never store credentials in `.env` files committed to git
- ❌ Never log sensitive data

## Credential Handling

- All secrets must remain in uncommitted `.env` files or environment variables.
- Use `.env.example` with placeholder values to document required variables.
- Rotate any credential that may have been exposed.

## Logging

- Never include API keys, tokens, passwords, or other sensitive values in log output.
- Sanitize error messages before they reach users or logs.

## Third-party Services

- Oxigraph and other backend services run internally; no external credential exposure expected.
- Ensure `.env` files are listed in `.gitignore` at the repository root and in sub-projects.
