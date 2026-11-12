# Scoped preparation using existing GitHub authorization
The existing candidate, preflight, signing helper and automatic publication engines remain in use. Unchanged Master/User packages are reused.

prepare-candidate.yml is manual dispatch only:
- prepare (default): stage plus preflight and save verified evidence, without activating current-request.
- stage: stage immutable bytes only.
- preflight: verify staged bytes and save evidence.
- activate: reuse saved exact request/evidence through the existing activation gates.
- full: prepare and activate within explicit approval.

job_id selects publisher/control/jobs/<jobId>.json on this PUBLIC repository's main branch.
This file is the common operational hold for the connector and public preparation stages. Keep only schema, paused, and public candidate-scoped releaseAuthorization metadata here; never copy private plans, user conversations, credentials or runtime evidence.
The workflow reads it using the built-in github.token. A separate RELEASE_CONTROL_TOKEN secret is no longer required.
A missing/unreadable/malformed file or paused state fails closed. Unpausing requires actual user authorization.
releaseAuthorization binds candidateFileSha256, a non-sensitive approval reference, and allowedStages to exact candidate bytes. Preparation approval never implies activation approval.
The connector also checks the private job's exact transfer approval; public stage authorization does not authorize transfer.

Transfer runs through the existing ChatGPT GitHub connector and paired engine in the private integration repository. No new user token or reconnection is required.
Preparation/publication retain master-longterm-publication concurrency. Connector transfer uses a private CAS checkpoint plus non-forced staging ref updates; it does not inherit an Actions lock.
preserve-preflight.py commits only verified request/evidence and never activates current-request.
The shared hold guard operates at stage boundaries, cannot revoke an HTTP request already in flight, and does not retrofit the unchanged automatic signing publication engine.
