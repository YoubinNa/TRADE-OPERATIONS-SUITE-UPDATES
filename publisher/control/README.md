# GitHub connector execution path

The existing candidate, preflight, signing helper and automatic publication engines remain in use. Unchanged Master/User packages are reused.

## Start without a browser
1. Complete and verify the exact paired transfer. Record the exact candidate approval and candidate SHA-256 in the existing shared control. A tool improvement or module commit is not deployment authorization.
2. Through the existing GitHub connector, create **one new file** under `publisher/execution-requests/<request_id>.json` on main. Commit the request last, after candidate bytes and stage authorization are ready. Do not modify an existing request or combine multiple requests in one push.
3. The push starts `prepare-candidate.yml`. The resolver validates the event, new-file status, request schema/path, exact candidate SHA-256 and live stage authorization. Each existing execution stage also re-reads the live operational hold.
4. Query Actions runs filtered by the request commit SHA using the connector, then job/step results. Use `publisher/current-request.json`, `publisher/status.json` and the active signed feed to distinguish readiness from completed publication. Print only stage/count/hash/error summaries.

Request schema (example only; not an executable request):
```json
{
  "schema": 1,
  "request_id": "<unique-public-request-id>",
  "candidate": "publisher/candidates/v0.X.Y.json",
  "candidate_sha256": "<SHA-256 of exact candidate file bytes>",
  "operation": "prepare",
  "job_id": "<existing-public-control-job-id>"
}
```

Only those six keys are allowed. The request ID must match its filename. A changed/deleted/renamed request, multiple request changes, a forced push, a non-main push or a hash mismatch fails closed. Candidate-only/control-only commits do not start preparation. This metadata is public: no private plans, conversations, credentials or internal runtime logs.

## Operations and existing boundaries
- prepare (default for manual dispatch): stage, preflight and preserve verified evidence; no current-request activation.
- stage: stage immutable approved bytes.
- preflight: verify staged bytes and preserve evidence.
- activate: reuse the saved exact request/evidence through existing activation gates.
- full: prepare and activate only with all corresponding explicit permissions.
- inspect: read-only resolution and current hold/allowed-stage report. Runs only the small resolver job with contents:read; the Windows candidate job is skipped. A paused control remains paused.

Manual workflow_dispatch remains available as a fallback. The connector currently has no tool for starting a new workflow_dispatch, so the request-file push is the normal automated path. No browser, extra PAT, custom secret or plugin reconnection is needed for that start.

job_id selects `publisher/control/jobs/<jobId>.json` on this PUBLIC repository's main branch. The built-in github.token reads this common operational hold. Missing/unreadable/malformed control fails closed; actual user authorization is required to unpause. releaseAuthorization binds candidateFileSha256, a public approval reference and allowedStages. Preparation approval never implies activation approval. The private transfer engine still requires its separate exact transfer approval.

The existing master-longterm-publication concurrency group and cancel-in-progress:false serialize execution. A request is not a perpetual retry signal: unrelated later commits do not re-trigger it. After failure inspect remote state; intentionally create a new uniquely named request for the necessary operation only after reconciliation. Existing candidate/predecessor/current-request/activation/signature gates remain authoritative. Do not blindly re-run full or overwrite candidates.

preserve-preflight.py never activates current-request. The shared hold guard applies at stage boundaries and cannot revoke an already in-flight HTTP operation. The unchanged signature-delivery engine still validates and publishes automatically after the approved operational signature arrives; no chat acknowledgment is needed.

## Verification without a deployment
Run the synthetic request/control/workflow contract tests in check-release-control.yml. An inspect request for an existing paused candidate can then confirm the actual connector push route without staging, activating a request, signing or publishing. Keep existing release bytes, active feed and completed-job holds unchanged.
