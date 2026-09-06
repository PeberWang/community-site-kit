# Module patterns

## Bundles

| Bundle | Enable | Delay |
|---|---|---|
| Minimum knowledge loop | guides, contributions, feedback | articles, events, plaza |
| Publishing community | guides, articles, contributions, feedback | plaza until moderators exist |
| Active organization | guides, articles, events, contributions, feedback | plaza until conduct rules exist |
| Read-only showcase | guides, articles, events | contributions and plaza |

Authentication and administration remain core because permissions and review cannot be optional on a governed site.

## Module contracts

- `home`: surface only already-published recent items and current announcements.
- `guides`: maintain evolving Markdown truth sources; AI prepares candidates; humans publish.
- `articles`: preserve authored long-form work; review before publication.
- `events`: carry time, place/link, organizer, reason, and lifecycle; review before publication.
- `plaza`: allow immediate conversation with post-publication moderation and deletion audit.
- `contributions`: require a tag plus either context text or attachments; never accept context-free empty submissions.
- `feedback`: attach likes and comments to a stable content target.
- `admin`: expose least-privilege queues, accounts, tags, moderation, and revision diffs.

## Selection test

Enable a module only if the user can name a current recurring situation, an owner, a governance rule, and a measurable two-week signal. Otherwise record it in the roadmap.

Avoid routing a contribution into an article through content inspection. These are different user intents and should have distinct entry points.
