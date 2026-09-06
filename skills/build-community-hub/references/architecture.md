# Starter architecture

## Layers

```text
app/       HTTP, guards, templates, static UI
  ↓
glue/      workflows spanning multiple domains
  ↓
services/  domain rules and repository operations
  ↓
libs/      file, Markdown, LLM, OCR, and storage adapters
  ↓
third-party packages
```

Use absolute project imports. A service must not call another service; compose them in `glue` or a thin router. A service constructor receives settings only. Wrap third-party SDKs in `libs`.

## Data contracts

- `config/community.json`: public identity, vocabulary, theme, and feature switches.
- `.env`: secrets and environment-specific endpoints; never commit.
- `data/db/*.json`: lightweight metadata and private identifiers.
- `data/guides/<slug>.md`: current formal guide truth sources.
- `data/guides/history/`: immutable guide revisions.
- local stub or object storage: attachments, article bodies, OCR, and summaries.

## Safe customization order

Prefer configuration and template wording first. Change schema only when the community's objects truly differ. Add a module as a vertical slice: model, service, router/template, permissions, tests, configuration switch, documentation, and export behavior.

Keep configuration loading deterministic and fail clearly on invalid JSON or unknown module names. Disabled modules must disappear from navigation and reject their routes, not merely hide buttons.

## Core invariants

- All web writes pass writer or administrator guards.
- Runtime paths come from settings.
- Files use UTF-8 and newline `\n`.
- Heavy bytes stay outside JSON metadata.
- Downloads require authentication and short-lived authorization.
- Human changes outrank candidates generated from older versions.
- Runtime data is never overwritten by a code deployment.
