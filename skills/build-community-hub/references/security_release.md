# Security and release gates

## Public repository gate

Create a clean-history repository if the source ever held private data. Include only code, blank configuration, fictional examples, tests, and approved documentation.

Run `scripts/audit_public.py` on the exact publication directory. Also inspect Git tracked files and history, document/image metadata, test fixtures, generated build artifacts, deployment samples, remotes, issues, and screenshots manually.

Block publication on any credential, private key, real invite, member record, personal contact, internal URL, server address, storage bucket, source-community name, unlicensed content, or ambiguous artifact.

## Production gate

- Use HTTPS and Secure cookies.
- Generate a unique random session secret of at least 32 characters.
- Keep object storage private and issue short-lived download URLs after authorization.
- Use least-privilege service identities; rotate and revoke credentials.
- Back up metadata, guides, and attachments; test restoration.
- Log security events without logging secrets or unnecessary personal data.
- Test every role against every write path.
- Pin an exact reviewed revision for deployment and retain rollback instructions.

## External action rule

Before creating a public repository or live service, show the user the exact name, visibility, included path, scan result, and excluded private categories. Obtain explicit authority if it was not already given. Never infer authority to publish runtime data from authority to publish code.

## Handoff evidence

Report repository and service URLs, commit or revision, test commands and results, scan result, enabled modules, storage locations, backup/restore status, known limitations, responsible maintainers, and next review date.
