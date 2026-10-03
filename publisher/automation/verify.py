"""Public distribution checks. No private repository, signing key or user data inputs."""
import base64, hashlib, json, re, zipfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

REPO = 'YoubinNa/TRADE-OPERATIONS-SUITE-UPDATES'
KEY_ID = 'bdbfbeb117243191a5a53327504b6537e7bef131b37fcef7dc7e43dfcfa2945e'
MODULUS = '2BfgMYlc+MEPrEhguLFsJ2kWuZ5iqzUwfgUbnDDD6ZjzQY0jBX14uj/HvJNn+0ejPVuJzN33JLmNvNGCgX1bQcZCrgNEVmtOxachze9ut8P4kA9fOVmJpKZIfnQlKi12awPwDwhpPlPNt0pbOl8UhSXsgI44jilfqpbHXpNPiaY2uJFlBMw4Z0TpgUSwM9ATUvVFYDR544+3HkxKsqvPZWCy4fVF8bPOMp88wX+kxp3pViNFnp7cH9Cor632ERfZQqEscvW4McGhiZ7GtzDcOj6HzTpHv3EZJ50wUjuWrTiwuYF5Zo5Z2ueibIAfVOINl+pCbMzQOWGqTQ2xovyEcyM+L4RuS5FlAsARSOlW6hJoT4MylgCUPce614UBYBw11BnnIOo0MF4EnqmUZSBPF8YlC4jjYwH7Ktp+pa999Wcl7WFk1qgHkKNZLHSQynBFZwirsUx3m3z3jOSDUrgEOD8KYY/2F6KLRuzU2fPPC1BS5IdzlbHXe0aMprB/qLvZ'

def require(ok, message):
    if not ok: raise ValueError(message)

def sha(raw): return hashlib.sha256(raw).hexdigest()

def strict_json(raw):
    def pairs(items):
        d = {}
        for k, v in items:
            require(k not in d, 'Duplicate JSON key')
            d[k] = v
        return d
    return json.loads(raw, object_pairs_hook=pairs)

def signature(raw, check_time=True):
    require(0 < len(raw) <= 1048576, 'Envelope size')
    e = strict_json(raw)
    require(e['schema'] == 1 and e['keyId'] == KEY_ID, 'Untrusted key or schema')
    data = base64.b64decode(e['payload'], validate=True)
    sig = base64.b64decode(e['signature'], validate=True)
    require(len(sig) == 384 and 0 < len(data) <= 524288, 'RSA/payload size')
    n = int.from_bytes(base64.b64decode(MODULUS), 'big')
    s = int.from_bytes(sig, 'big')
    require(s < n, 'RSA signature range')
    # Strict EMSA-PKCS1-v1_5 verification with SHA-256 DigestInfo, fixed RSA-3072 key.
    digest_info = bytes.fromhex('3031300d060960864801650304020105000420') + hashlib.sha256(data).digest()
    expected = b'\x00\x01' + b'\xff' * (384-len(digest_info)-3) + b'\x00' + digest_info
    require(pow(s, 65537, n).to_bytes(384, 'big') == expected, 'Invalid production signature')
    d = strict_json(data)
    require(d['schema'] == 1 and d['product'] == 'ECUSS.ValidationSuite' and d['channel'] == 'stable', 'Wrong signed product')
    require(type(d['sequence']) is int and d['sequence'] > 0, 'Invalid sequence')
    if check_time:
        now = datetime.now(timezone.utc)
        require(datetime.fromisoformat(d['issuedAt']) <= now + timedelta(minutes=5), 'Future issue date')
        require(datetime.fromisoformat(d['expiresAt']) > now, 'Expired signature')
    c = d['catalog']
    require(c['schema'] == 1 and c['product'] == d['product'], 'Catalog schema/product')
    require(re.fullmatch(r'\d+\.\d+\.\d+', c['appVersion']), 'Invalid version')
    catalog_identity(c)
    return e, d, sha(data)

def catalog_identity(c):
    require(c['profiles'] in (['master'], ['master','user']), 'Unsupported distribution profiles')
    require([p['profile'] for p in c['packages']]==c['profiles'], 'Incomplete or duplicate paired packages')
    for p in c['packages']:
        require(p['repository']==REPO and p['appVersion']==c['appVersion'], 'Package identity')
        require(re.fullmatch('[0-9a-f]{40}',p['commit']) and re.fullmatch('[0-9a-f]{64}',p['sha256']), 'Invalid immutable identity')
        require(type(p['bytes']) is int and 0<p['bytes']<=64*1024*1024, 'Package size')
        require(p['path']==f"packages/v{c['appVersion']}/TRADE_OPERATIONS_SUITE_{p['profile'].title()}_v{c['appVersion']}.ecuss-update.zip", 'Unexpected package path')
        require(p['launcherApi']==4, 'Unsupported launcher API')
    if len(c['profiles'])==2:
        require(len({p['commit'] for p in c['packages']})==1, 'Paired packages require one immutable commit')

def ready(root):
    request_raw = (root/'publisher/current-request.json').read_bytes()
    req = strict_json(request_raw)
    if req['state'] == 'idle': return None
    require(req['state'] == 'ready' and req['product'] == 'TRADE-OPERATIONS-SUITE-PUBLISHER' and req['channel'] == 'longterm', 'Invalid request')
    payload = base64.b64decode(req['payload'], validate=True)
    h = sha(payload)
    require(req['payloadSha256'] == h and req['keyId'] == KEY_ID, 'Request hash/key')
    seq = strict_json(payload)['sequence']
    require(type(seq) is int and seq > 0, 'Invalid request sequence')
    inbox = root/f'publisher/inbox/seq-{seq}-{h}.signed.json'
    if not inbox.exists(): return None
    raw = inbox.read_bytes()
    e, d, _ = signature(raw)
    require(e['payload'] == req['payload'] and sha(payload) == h, 'Signature is not for current request')
    plan = strict_json((root/f'publisher/plans/seq-{seq}.json').read_bytes())
    require(plan['schema'] == 1 and plan['enabled'] is True and plan['payloadSha256'] == h, 'Not enabled for automatic publication')
    require(plan['publicContentReviewed'] is True and plan['windowsCandidateVerified'] is True, 'Candidate review incomplete')
    update_mode(plan, d['catalog'])
    active_raw = (root/'updates/stable-longterm.signed.json').read_bytes()
    _, active, _ = signature(active_raw)
    resumed = active_raw == raw
    if resumed:
        previous_raw = (root/f'publisher/publications/seq-{seq}/previous.signed.json').read_bytes()
        _, previous, _ = signature(previous_raw)
    else:
        previous_raw, previous = active_raw, active
    require(d['sequence'] > previous['sequence'], 'Rollback or same-sequence conflict')
    require(previous['catalog']['appVersion'] == plan['requiredActiveVersion'], 'Required transition not active')
    require(tuple(map(int,d['catalog']['appVersion'].split('.'))) > tuple(map(int,previous['catalog']['appVersion'].split('.'))), 'Version must advance')
    return dict(requestRaw=request_raw, envelope=raw, previous=previous_raw, payload=d, previousPayload=previous, plan=plan, resumed=resumed, inbox=inbox.relative_to(root).as_posix())

def update_mode(plan, catalog):
    mode=plan.get('updateMode','online')
    require(mode in ('online','legacy-import-once'),'Unsupported update mode')
    if mode=='legacy-import-once':
        require(plan.get('legacyImportExplicitlyApproved') is True and plan.get('legacyOnlineNewModuleRejected') is True,'Legacy import requires explicit reviewed approval')
        r=catalog.get('repositoryRegistry')
        require(isinstance(r,dict) and r.get('schema')==1 and isinstance(r.get('suite'),dict) and isinstance(r.get('modules'),list),'Signed cumulative registry required')
        require(0<len(r['modules'])<=30 and len({m['moduleId'] for m in r['modules']})==len(r['modules']),'Invalid cumulative registry modules')
        require(all(any(s['moduleId']==m['id'] and s['repository']==m['repository'] for s in r['modules']) for m in catalog['modules']),'Cumulative module/source mismatch')
    return mode

def registry_matches(root, catalog):
    if 'repositoryRegistry' not in catalog:return
    actual=strict_json((root/'module-sources.json').read_bytes());approved=catalog['repositoryRegistry']
    def source(r):return tuple(r.get(k) for k in ('moduleId','repository','repositoryId','defaultBranch'))
    require(actual['schema']==approved['schema'] and source(actual['suite'])==source(approved['suite']),'Packaged suite registry mismatch')
    require(len(actual['modules'])==len(approved['modules']) and sorted(map(source,actual['modules']))==sorted(map(source,approved['modules'])),'Packaged module registry mismatch')

def archive(path, p, target=None):
    raw = path.read_bytes()
    require(len(raw) == p['bytes'] and sha(raw) == p['sha256'], 'Archive hash/length')
    with zipfile.ZipFile(path) as z:
        names=z.namelist()
        require(len(names)==len(set(names)) and len(names)==len({n.lower() for n in names}), 'Duplicate ZIP entry')
        require(all(n and not n.startswith('/') and '\\' not in n and ':' not in n and '..' not in n.split('/') for n in names), 'Unsafe ZIP path')
        require(sum(x.file_size for x in z.infolist()) < 512*1024*1024, 'Expanded size')
        require(z.testzip() is None, 'ZIP CRC')
        m=strict_json(z.read('manifest.json'))
        require(m['appVersion']==p['appVersion'] and m['releaseId']==p['releaseId'] and m['profile']==p['profile'], 'Manifest identity')
        require(set(names)=={f['path'] for f in m['files']}|{'manifest.json'}, 'Manifest inventory')
        require(len(m['files'])==len(names)-1, 'Duplicate manifest record')
        require(not any(n.startswith('modules/balance-ecuss/') or n.lower().endswith(('.pfx','.p12','.msg','.xlsx','.xls')) for n in names), 'Excluded personal/business assets')
        for f in m['files']:
            b=z.read(f['path'])
            require(len(b)==f['size'] and sha(b)==f['sha256'], 'Manifest file mismatch')
        if target:
            require(not target.exists(), 'Extraction destination exists')
            z.extractall(target)
    return m
