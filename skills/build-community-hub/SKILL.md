---
name: build-community-hub
description: Interview a non-technical community organizer, turn social and governance needs into a scoped product brief, bootstrap and customize a privacy-first knowledge-sharing website, validate it, and prepare a safe deployment and handoff. Use when someone wants to build or adapt a website for a major, department, reading group, student organization, alumni network, mutual-aid group, or other community; when they ask to import this resource pack; or when an existing Community Site Kit project needs modules, roles, workflows, branding, governance, privacy, deployment, or maintenance changes.
---

# Build Community Hub

Guide the user from community intent to a maintainable website. Treat the user as the authority on people, norms, harms, and tradeoffs. Translate their decisions into artifacts and code.

## Working rules

- Ask one short, answerable question at a time when discovery is needed. Explain what each answer changes.
- Use plain language first. Define technical terms only when they affect a decision.
- Keep an assumptions list. Distinguish confirmed facts, proposals, and unknowns.
- Start with the smallest loop that can create value. Do not enable every module by default.
- Use fictional data until the user explicitly authorizes real data.
- Never put credentials, member data, private content, internal URLs, or production snapshots in Git.
- Never let an LLM publish or overwrite a formal guide automatically. Preserve human edits and require review of a candidate diff.
- Do not deploy, buy services, create public resources, or contact members without explicit authority.

## Route the task

- For a new community, follow all phases below.
- For an existing project, inspect `docs/product_brief.md`, `config/community.json`, Git status, tests, and privacy inventory; then resume at the earliest incomplete gate.
- For a module choice, read `references/module_patterns.md`.
- For social rules, moderation, succession, or incentives, read `references/governance.md`.
- For code or architecture changes, read `references/architecture.md`.
- For importing existing content, read `references/migration.md`.
- For release, repository publication, or deployment, always read `references/security_release.md`.

## Phase 1: Discover the community

Read `references/discovery.md`. Interview for:

1. people and power;
2. recurring situations and current workarounds;
3. content types and lifecycle;
4. publication, moderation, correction, and appeal;
5. privacy, copyright, safety, and model-use boundaries;
6. ownership, budget, maintenance, succession, and exit.

Write `docs/product_brief.md` and `docs/privacy_inventory.md` in the target project. Include non-goals, assumptions, unresolved questions, and concrete acceptance scenarios.

Gate: ask the user to confirm the brief and privacy boundaries before building with real scope.

## Phase 2: Choose the minimum system

Read `references/module_patterns.md` and `references/governance.md`. Recommend one minimum bundle and a later roadmap. For every enabled module, name:

- the user problem it solves;
- who owns it;
- who can read, submit, publish, edit, remove, and appeal;
- its data retention and exit path;
- a testable success signal.

Record decisions in `docs/decision_log.md`. Prefer configuration over forks or copy-pasted variants.

Gate: verify that every enabled module has an owner and governance rule.

## Phase 3: Bootstrap safely

Create a new project from the bundled starter:

```bash
python scripts/bootstrap_project.py \
  --destination /absolute/path/to/project \
  --name "Site name" \
  --community "Community name" \
  --modules guides,contributions,feedback
```

Run the command from this skill directory, or use an absolute path to the script. Refuse to overwrite a non-empty destination. Preserve user changes if adapting an existing project.

Edit `config/community.json` for identity, vocabulary, modules, taxonomy, and theme. Keep secrets in `.env`; keep runtime content under `data/`. Initialize Git only after the privacy audit passes.

## Phase 4: Customize in layers

Read `references/architecture.md`. Work in this order:

1. identity, wording, taxonomy, and theme;
2. enabled modules and navigation;
3. roles, review paths, and moderation;
4. content schemas and import adapters;
5. storage, model, OCR, and hosting adapters.

Keep `app → glue → services → libs → third_party` dependencies one-way. Put HTTP and rendering in `app`, cross-domain orchestration in `glue`, rules in `services`, and external integrations in `libs`. Do not add a dependency without documenting why a mature existing library is preferable to a local implementation.

After each layer, run relevant tests and show the user what changed in ordinary language.

## Phase 5: Validate with scenarios

Run:

```bash
python -m pytest -q
python ../../scripts/validate_project.py .
python ../../scripts/audit_public.py .
```

Adjust relative paths if the project is outside the starter. Test at least:

- anonymous visitor;
- observer attempting a write;
- member submitting each enabled content type;
- administrator approving, rejecting, correcting, and restoring;
- stale AI candidate attempting to overwrite a human edit;
- backup export and recovery on fictional data;
- mobile viewport and keyboard navigation.

Gate: report failures and residual risks. Do not call a site ready because it merely starts.

## Phase 6: Release and hand off

Read `references/security_release.md`. Separate three deliverables:

- public code repository: code, blank config, fictional fixtures, documentation;
- private runtime data: accounts, invites, content, feedback, files, logs;
- operator secrets: environment variables and infrastructure credentials.

For a source repository that ever contained private material, create a clean repository with fresh history instead of deleting only the latest copy. Audit files and history before any public push.

Write an operations runbook covering start, stop, health checks, backup, restore, rollback, credential rotation, moderation, data export, incident response, and succession. Require at least two maintainers to rehearse recovery.

Gate: obtain explicit user approval for the exact public repository and deployment target, then publish. Finish with URLs, verification evidence, unresolved risks, and the next maintenance date.
