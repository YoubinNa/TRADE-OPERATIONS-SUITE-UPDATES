# Distribution-only repository

- This repository is PUBLIC. It contains approved distribution material only.
- Read README.md and DISTRIBUTION_POLICY.md before making changes.
- Never copy private development history, source trees, internal test evidence, business documents, personal mail assets, credentials, or private signing keys here, except for the narrowly approved work-records bootstrap credential in designated distribution binaries as specified in DISTRIBUTION_POLICY.md. Never commit the credential as source, documentation, or logs.
- Verify complete final package contents before publication; a filename or hash scan alone is insufficient.
- Keep published version bytes immutable. Record new bytes under a new approved version.
- Never publish an unverified or placeholder active update feed. Repository availability is not evidence that an update is ready.
- Preserve explicit Master release approval and do not treat a module commit as integration release approval.
- No end-user login, GitHub token, paid service, or device-registration dependency.
- User instructions take precedence; do not claim unperformed Windows/user-PC testing.

- 2026-10-02 explicit Master instruction: completing requested improvements does NOT authorize sending a Master Signing request. Obtain explicit approval before setting `publisher/current-request.json` to ready or asking the helper to sign, unless the user explicitly instructed sending it after completion. After an approved request is signed and delivered, retain automatic validation and publication without a chat acknowledgment.

- 2026-10-03 Master/User synchronization: after the first paired Beta, require both profiles in every release with identical app/module/rules/core versions. Prepare both update packages together; installers are prepared only upon a separate Master request, send one signing request, verify both profiles and activate one signed feed atomically. Permission/mail/presentation differences remain intentional. Never publish a Master-only update after a paired release or call queued/offline PCs synchronized installations.

- Routine releases publish updates only. Do not generate or publish Setup automatically. A separately requested new-install Setup includes only the approved records-repository credential and imports it automatically; the initial existing-PC bootstrap update is the one-time update exception. Later routine updates contain no credential and preserve the protected local setting. This policy change does not authorize deleting old assets or sending a new signing request.
