"""Reusable approved candidate staging and atomic signing-request activation.

No private-repository access or signing key. Public candidate specifications contain
only reviewed distribution metadata and an explicit, candidate-specific approval.
"""
import base64
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from verify import archive, require, sha, signature, strict_json, update_mode, REPO

ROOT = Path(__file__).resolve().parents[2]

def run(*args):
    return subprocess.check_output([str(x) for x in args], cwd=ROOT).decode('utf-8').strip()

def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8', newline='\n')

def validate_spec(s):
    require(s.get('schema') == 1 and re.fullmatch(r'0\.\d+\.\d+', s.get('version', '')), 'Candidate version/schema')
    require(type(s.get('sequence')) is int and s['sequence'] > 0, 'Sequence')
    require(s.get('publicContentReviewed') is True and s.get('windowsCandidateVerified') is True, 'Review incomplete')
    require(bool(s.get('candidateVerificationRuns')), 'Verification evidence required')
    require(len(s.get('assets', [])) == 1, 'Only Master supported')
    p = s['assets'][0]
    require(p['profile'] == 'master' and p['path'] == f"packages/v{s['version']}/TRADE_OPERATIONS_SUITE_Master_v{s['version']}.ecuss-update.zip", 'Package scope')
    require(re.fullmatch('[0-9a-f]{64}', p['sha256']) and type(p['bytes']) is int and 0 < p['bytes'] <= 100*1024*1024, 'Package identity')
    a = s.get('approval', {})
    require(a.get('explicit') is True and a.get('scope') == 'master-release' and bool(a.get('approvedAt')), 'Explicit release approval missing')
    require(a.get('packageSha256') == p['sha256'] and a.get('version') == s['version'] and a.get('sequence') == s['sequence'], 'Approval belongs to another candidate')
    require(isinstance(s.get('notes'), list) and len(s['notes']) > 0, 'User-facing changes required')
    require(s.get('updateMode', 'online') in ('online', 'legacy-import-once'), 'Update mode')
    return s

def load_spec(path):
    require(re.fullmatch(r'publisher/candidates/v0\.\d+\.\d+\.json', path) is not None, 'Candidate path')
    s = validate_spec(strict_json((ROOT/path).read_bytes()))
    require(path == f"publisher/candidates/v{s['version']}.json", 'Candidate filename/version mismatch')
    return s

def decode_transfer(root, s):
    p = s['assets'][0]
    path = root/p['path']
    if path.exists():
        archive(path, dict(p, appVersion=s['version']))
        return
    folder = root/f"releases/v{s['version']}/transfer"
    index = strict_json((folder/'index.json').read_bytes())
    require(index['packageSha256'] == p['sha256'] and index['bytes'] == p['bytes'], 'Transfer does not match approved package')
    chunks = []
    require(0 < len(index['parts']) <= 200, 'Part count')
    for i, part in enumerate(index['parts']):
        require(part['name'] == f'master-{i:03d}.b64', 'Unexpected transfer path/order')
        raw = base64.b64decode((folder/part['name']).read_bytes(), validate=True)
        require(len(raw) == part['bytes'] and sha(raw) == part['sha256'], 'Transfer fragment changed')
        chunks.append(raw)
    raw = b''.join(chunks)
    require(len(raw) == p['bytes'] and sha(raw) == p['sha256'], 'Transfer package changed')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    archive(path, dict(p, appVersion=s['version']))

def check_predecessor(s, previous):
    require(previous['catalog']['appVersion'] == s['requiredActiveVersion'], 'Active predecessor changed')
    require(s['sequence'] > previous['sequence'], 'Sequence rollback')
    version = lambda x: tuple(map(int, x.split('.')))
    require(version(s['version']) > version(previous['catalog']['appVersion']), 'Version rollback')

def check_slot(current, request=None):
    require(current['state'] == 'idle' or (request is not None and current == request), 'Another signing request is pending')

def commit(paths, message):
    run('git', 'config', 'user.name', 'github-actions[bot]')
    run('git', 'config', 'user.email', '41898282+github-actions[bot]@users.noreply.github.com')
    run('git', 'add', '--', *paths)
    if run('git', 'diff', '--cached', '--name-only'):
        run('git', 'commit', '-m', message)
        run('git', 'push', 'origin', 'HEAD:refs/heads/main')  # Never force a concurrent change.

def stage(s):
    _, previous, _ = signature((ROOT/'updates/stable-longterm.signed.json').read_bytes())
    check_predecessor(s, previous)
    current = strict_json((ROOT/'publisher/current-request.json').read_bytes())
    saved = ROOT/f"publisher/requests/v{s['version']}.json"
    check_slot(current, strict_json(saved.read_bytes()) if saved.exists() else None)
    decode_transfer(ROOT, s)
    folder = ROOT/f"releases/v{s['version']}"
    write(folder/'publish.json', s)
    (folder/'NOTES.md').write_text('\n'.join(['# Master v'+s['version'], '']+['- '+x for x in s['notes']])+'\n', encoding='utf-8')
    transfer = folder/'transfer'
    if transfer.exists(): shutil.rmtree(transfer)
    commit([s['assets'][0]['path'], folder.relative_to(ROOT).as_posix()], f"release: stage audited Master v{s['version']}")
    p = s['assets'][0]
    # Reuse the package identity on retries; never make a new signing payload for the same staged version.
    identity = ROOT/f"releases/v{s['version']}/package-identity.json"
    if identity.exists():
        package_commit = strict_json(identity.read_bytes())['commit']
        require(sha(subprocess.check_output(['git', 'show', package_commit+':'+p['path']], cwd=ROOT)) == p['sha256'], 'Saved package identity changed')
    else:
        package_commit = run('git', 'rev-parse', 'HEAD')
        write(identity, dict(commit=package_commit, sha256=p['sha256']))
        commit([identity.relative_to(ROOT).as_posix()], f"release: pin v{s['version']} package identity")
    result = subprocess.run(['gh','api',f"repos/{REPO}/releases/tags/v{s['version']}"], cwd=ROOT, capture_output=True)
    if result.returncode == 0:
        assets = strict_json(result.stdout)['assets']
        require(len(assets) == 1 and assets[0]['name'] == Path(p['path']).name and assets[0]['size'] == p['bytes'] and assets[0]['digest'] == 'sha256:'+p['sha256'], 'Existing release bytes differ')
    else:
        run('gh', 'release', 'create', 'v'+s['version'], p['path'], '--target', package_commit, '--title', 'Master v'+s['version']+' — signing candidate', '--notes-file', str(folder/'NOTES.md'), '--prerelease', '--latest=false')

def activation(s, request, evidence, previous, current):
    validate_spec(s); check_predecessor(s, previous); check_slot(current, request)
    payload = base64.b64decode(request['payload'], validate=True)
    require(request['payloadSha256'] == sha(payload) == evidence['payloadSha256'], 'Checked request changed')
    d = strict_json(payload); p = d['catalog']['packages'][0]
    require(request['state'] == 'ready' and d['sequence'] == s['sequence'] and d['catalog']['appVersion'] == s['version'], 'Request candidate identity')
    require(all(p[k] == s['assets'][0][k] for k in ('profile','path','releaseId','bytes','sha256')), 'Approval package mismatch')
    require(evidence['version'] == s['version'] and evidence['sequence'] == s['sequence'] and evidence['packageCommit'] == p['commit'] and evidence['packageSha256'] == p['sha256'], 'Evidence identity mismatch')
    require(evidence['windowsPublicDownloadChecks'] == 14 and evidence['helperRequestChecks'] == 7 and evidence['publicationGateCompiledAgainstActualOldAndNew'] is True, 'Windows preflight incomplete')
    plan = dict(schema=1, enabled=True, payloadSha256=sha(payload), requiredActiveVersion=s['requiredActiveVersion'], publicContentReviewed=True, windowsCandidateVerified=True, candidateVerificationRuns=s['candidateVerificationRuns'], masterReleaseApprovedAt=s['approval']['approvedAt'], updateMode=s.get('updateMode','online'), legacyImportExplicitlyApproved=s.get('legacyImportExplicitlyApproved',False), legacyOnlineNewModuleRejected=s.get('legacyOnlineNewModuleRejected',False), scope='Approved Master release only; User formal release excluded')
    update_mode(plan, d['catalog'])
    return plan

def activate(s):
    version = s['version']; seq = s['sequence']
    request_path = f'publisher/requests/v{version}.json'
    evidence_path = f'releases/v{version}/PREFLIGHT.json'
    req = strict_json((ROOT/request_path).read_bytes()); evidence = strict_json((ROOT/evidence_path).read_bytes())
    _, previous, _ = signature((ROOT/'updates/stable-longterm.signed.json').read_bytes())
    current = strict_json((ROOT/'publisher/current-request.json').read_bytes())
    plan = activation(s, req, evidence, previous, current)
    plan_path = f'publisher/plans/seq-{seq}.json'
    write(ROOT/plan_path, plan)
    # Copy exact helper-tested bytes; do not serialize or regenerate the signed payload.
    (ROOT/'publisher/current-request.json').write_bytes((ROOT/request_path).read_bytes())
    evidence['currentRequestActivated'] = True
    evidence['requestReadyAt'] = datetime.now(timezone.utc).isoformat()
    evidence['masterReleaseApprovedAt'] = s['approval']['approvedAt']
    write(ROOT/evidence_path, evidence)
    commit([request_path,evidence_path,plan_path,'publisher/current-request.json'], f'publisher: checked approved request ready for v{version}')
    print('SIGNING REQUEST READY; no extra chat acknowledgement required.', flush=True)

if __name__ == '__main__':
    spec = load_spec(sys.argv[2])
    {'stage': stage, 'activate': activate}[sys.argv[1]](spec)
