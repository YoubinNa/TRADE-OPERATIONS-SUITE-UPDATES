# Changed-file update transport

New clients prefer `packages[].fileUpdate`, a schema-1 descriptor containing the exact byte length and SHA-256 of a per-profile `.files.json` release asset. The existing signed full ZIP fields and release assets remain available to legacy clients and offline recovery.

The index contains the exact target manifest text and one compressed object record per manifest path. Object names are `ecuss-file-<compressed-sha256>.gz`; URLs are derived from the fixed public repository and signed version. The client verifies the index against the production signature, verifies reused local files against target hashes, downloads missing or changed objects, and verifies every reconstructed file before switching releases. It supports skipped versions without an installed-version delta chain. Removed files never enter the new staging folder. Failures do not silently download the full ZIP.

`file_updates.py` creates deterministic gzip wrappers around the already verified full ZIP's DEFLATE streams without recompression. Candidate `fileUpdateAssets` must exactly match regenerated objects. Shared assets are deduplicated by name and digest. The explicit approval hash inventory includes the indexes and objects. The signed catalog includes only the index descriptor, not the auxiliary asset list.

Preparation requires anonymous file-download probes for both profiles, in addition to existing full-package and signing-helper checks. Production publication requires both signed file-update application/rollback probes, the existing full-package gates, all exact release assets, and one paired production signature. The active feed and signing request are not changed by the review workflow.

The first update from a client without file-update support uses the full ZIP once. Subsequent compatible releases use changed-file downloads. A changed large file still requires that file's complete compressed content; this is file-level reuse, not binary patching. Existing approved module payloads and runtime dependencies are not split or rewritten.
