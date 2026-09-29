# SafeBooks Instructions for Claude Code

Before planning or editing, read `knowledge.md` and follow every applicable rule in `AGENTS.md`.

SafeBooks is a Django financial-management application. Keep changes narrow and preserve existing behavior unless the user explicitly requests a broader change.

## Required safeguards

- Preserve bookkeeper ownership of clients and financial records.
- Do not expose secrets, passwords, recovery codes, client credentials, or `.env` values.
- Do not alter database models, migrations, API contracts, authentication, authorization, financial calculations, audit history, or deployment settings unless the request requires it.
- Inspect the relevant view, service, model, template, browser-side code, and tests before changing a feature.
- Keep unrelated files and user changes untouched.
- Run appropriate Django checks or focused tests, and report only completed verification.

For project architecture, workflows, configuration, and file locations, use `knowledge.md` as the source of truth.
