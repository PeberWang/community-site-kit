# Governance patterns

## Default roles

- `admin`: configure structure, manage invitations, review formal content, moderate discussion, and restore revisions.
- `user`: submit and edit own eligible content, participate in enabled discussion, and send feedback.
- `observer`: read permitted content only; use for guests, partners, reviewers, or demonstrations.

Do not create more roles until a real permission difference is identified. Never use a job title as a role if its permissions are identical.

## Publication lanes

Use pre-publication review for contributions, articles, events, and changes to formal guides. Use post-publication moderation for the plaza. Keep announcements administrator-only.

For each lane, define service time, rejection reason, correction, withdrawal, appeal, and incident handling. Visible rules should match actual code behavior.

## AI boundary

Treat models as drafting tools, not authorities. Supply the current human-edited guide as the base. Save generated text as a candidate with base version and hash. Validate structure, size, links, locked passages, and conflicts. Show a diff. Publish only after administrator approval. Preserve immutable revisions; restoring an old revision creates a new revision.

## Participation

Ask for the minimum context that makes a contribution usable. Let contributors choose an appropriate display name. Make attribution, correction, and withdrawal possible. Reward useful maintenance and synthesis, not raw upload volume.

## Succession

Keep two trained maintainers, a current operations runbook, periodic exports, credential ownership records, and a tested recovery path. A community system that only one founder can run is not complete.
