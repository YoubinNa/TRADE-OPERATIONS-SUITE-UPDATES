# Scoped preparation and activation
The existing candidate, Windows preflight, signing helper and automatic publication engines remain in use. Unchanged paired packages are reused.

prepare-candidate.yml is manual dispatch only:
- prepare (default): stage plus preflight, save verified request/evidence; no current-request activation.
- stage: stage immutable public bytes only.
- preflight: check already staged bytes and save evidence.
- activate: reuse saved exact request/evidence; existing candidate.activation gates still apply.
- full: prepare and activate within explicitly approved scope.

job_id selects the private Suite tools/release/jobs/<jobId>/control.json on main.
RELEASE_CONTROL_TOKEN is an Actions secret restricted to reading that private repository; it is never printed or distributed.
Missing/unavailable control blocks execution. Configure/verify this credential before an authorized live run; installation alone does not demonstrate credential readiness.
Control requires schema=1, paused=false and releaseAuthorization with the exact raw candidateFileSha256, approval reference, and allowedStages (public-stage, preflight, activate as applicable).
Transfer has its own exact plan authorization; neither approval automatically implies the other.
The guard runs at stage boundaries, including before preserving preflight evidence. It cannot revoke an HTTP request already in flight.
Public preparation/publication retain the existing master-longterm-publication concurrency; private transfer concurrency is separate.

preserve-preflight.py reuses candidate.activation for all existing approval/pair/Windows evidence checks, commits only the candidate request and PREFLIGHT.json, and never writes current-request.json or a publication plan.
The new control checker runs synthetic tests only. It does not stage packages, send a signing request or publish.
The existing auto-publish-signed workflow remains unchanged and continues only through its existing signature/approval gates after an approved signature is delivered.
Current user holds must be respected before initiating the signing helper; the new shared-control guard does not retrofit the automatic publication engine.
