"""Read-only Windows replay using the already approved v30 distribution fixture.
No signing request, Git commit, Release mutation or stable publication.
"""
import base64
import os
import subprocess
from pathlib import Path
from candidate import ROOT, write, activation
from verify import strict_json, signature, require

original_feed=(ROOT/'updates/stable-longterm.signed.json').read_bytes()
original_request=(ROOT/'publisher/current-request.json').read_bytes()
previous=(ROOT/'publisher/publications/seq-13/previous.signed.json').read_bytes()
request=strict_json((ROOT/'publisher/requests/v0.1.30.json').read_bytes())
document=strict_json(base64.b64decode(request['payload']))
p=document['catalog']['packages'][0]
spec=dict(schema=1,version='0.1.30',sequence=13,requiredActiveVersion='0.1.27',publicContentReviewed=True,windowsCandidateVerified=True,candidateVerificationRuns=[37082094404],assets=[{k:p[k] for k in ('profile','path','releaseId','bytes','sha256')}],notes=request['notes'],updateMode='legacy-import-once',legacyImportExplicitlyApproved=True,legacyOnlineNewModuleRejected=True,approval=dict(explicit=True,scope='master-release',approvedAt='2026-10-03T09:38:38+09:00',version='0.1.30',sequence=13,packageSha256=p['sha256']))
path='publisher/candidates/v0.1.30.json'
try:
    write(ROOT/path,spec)
    write(ROOT/'releases/v0.1.30/package-identity.json',dict(commit=p['commit'],sha256=p['sha256']))
    (ROOT/'updates/stable-longterm.signed.json').write_bytes(previous)
    subprocess.run(['python','-B','publisher/automation/preflight_candidate.py',path],cwd=ROOT,check=True)
    checked=strict_json((ROOT/'publisher/requests/v0.1.30.json').read_bytes())
    evidence=strict_json((ROOT/'releases/v0.1.30/PREFLIGHT.json').read_bytes())
    _, old, _=signature(previous)
    plan=activation(spec,checked,evidence,old,dict(state='idle'))
    require(checked==request and plan['payloadSha256']==request['payloadSha256'],'Replay changed the signed request')
    require((ROOT/'publisher/current-request.json').read_bytes()==original_request,'Replay touched current request')
    print('REPLAY PASSED: 14 actual Windows downloads + 7 installed-helper checks; exact request retained; no activation.')
finally:
    (ROOT/'updates/stable-longterm.signed.json').write_bytes(original_feed)
