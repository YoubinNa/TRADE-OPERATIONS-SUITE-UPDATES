# Distribution-only repository

- This repository is PUBLIC. It contains approved distribution material only.
- Read README.md and DISTRIBUTION_POLICY.md before making changes.
- Never copy private development history, source trees, internal test evidence, business documents, personal mail assets, credentials, or private signing keys here. Never include private credentials in new distribution binaries, source, documentation, or logs.
- Verify complete final package contents before publication; a filename or hash scan alone is insufficient.
- Keep published version bytes immutable. Record new bytes under a new approved version.
- Never publish an unverified or placeholder active update feed. Repository availability is not evidence that an update is ready.
- Preserve explicit Master release approval and do not treat a module commit as integration release approval.
- No end-user login, GitHub token, paid service, or device-registration dependency.
- User instructions take precedence; do not claim unperformed Windows/user-PC testing.

- 2026-10-02 explicit Master instruction: completing requested improvements does NOT authorize sending a Master Signing request. Obtain explicit approval before setting `publisher/current-request.json` to ready or asking the helper to sign, unless the user explicitly instructed sending it after completion. After an approved request is signed and delivered, retain automatic validation and publication without a chat acknowledgment.

- 2026-10-03 Master/User synchronization: after the first paired Beta, require both profiles in every release with identical app/module/rules/core versions. Prepare both update packages together; installers are prepared only upon a separate Master request, send one signing request, verify both profiles and activate one signed feed atomically. Permission/mail/presentation differences remain intentional. Never publish a Master-only update after a paired release or call queued/offline PCs synchronized installations.

- Routine releases publish Master/User updates only; Setup requires a separate explicit request. Shared records/HTML/stock use Supabase directly, with no company server, always-on PC or relay. The former embedded GitHub records-token policy is superseded for new releases. Only the approved project URL and publishable key may be distributed. Never embed a PAT, Supabase secret/service_role, Master password/session or signing key. User connects automatically after updating; Master completes initial storage authentication and keeps a DPAPI-protected session. Server RLS enforces Master stock permissions. Anonymous access does not establish employee identity.
- Validate the exact public Supabase project/configuration digest in both immutable distribution executables, keeping package/hash/version/signature/Windows/download gates. Existing legacy release bytes remain unchanged; historical validation does not authorize new credential distribution.
- Preserve settings, business results, saved authentication and bounded download cache across update/rollback. Refer to DISTRIBUTION_POLICY.md for the current durable policy; do not duplicate changing ready/published state here.
