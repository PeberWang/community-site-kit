# Content migration

## Inventory before import

List each source, owner, format, size, sensitivity, copyright status, identifiers, and update frequency. Decide whether to import, link, summarize, archive privately, or discard.

## Adapter workflow

1. Export without modifying the source.
2. Keep the raw export private and checksum it.
3. Parse through a source-specific adapter in `libs`.
4. Normalize into public project schemas.
5. Dry-run and report counts, unmapped items, duplicates, and rejected records.
6. Review a representative sample with fictional or redacted data.
7. Import into a backup copy before production.
8. Reconcile counts and record provenance.

Never commit raw exports or access tokens. Never infer missing ownership, consent, or publication rights. An item being accessible in an old tool does not authorize making it public.

Use stable IDs and content hashes so reruns are idempotent and same-named files do not overwrite one another. Preserve original attribution and an explicit withdrawal path.
