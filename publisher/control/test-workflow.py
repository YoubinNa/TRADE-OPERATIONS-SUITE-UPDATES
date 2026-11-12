import json,re,yaml
from pathlib import Path
data=yaml.load(Path('.github/workflows/prepare-candidate.yml').read_text(encoding='utf-8'),Loader=yaml.BaseLoader)
assert list(data['on'])==['workflow_dispatch']
assert data['on']['workflow_dispatch']['inputs']['operation']['default']=='prepare'
assert data['concurrency']['group']=='master-longterm-publication'
assert data['concurrency']['cancel-in-progress']=='false'
steps=data['jobs']['candidate']['steps']
for start,modes,guard in [('Verify approval',['prepare','stage','full'],'public-stage'),('Verify public',['prepare','preflight','full'],'preflight'),('Send exact',['activate','full'],'activate')]:
    s=next(s for s in steps if s.get('name','').startswith(start))
    assert json.loads(re.search(r"fromJSON\('(.+)'\)",s['if']).group(1))==modes
    assert 'execution-control-guard.cjs $env:SPEC '+guard in s['run']
save=next(s for s in steps if s.get('name','').startswith('Preserve exact'))
activation=next(s for s in steps if s.get('name','').startswith('Send exact'))
assert steps.index(save)<steps.index(activation)
assert 'preserve-preflight.py' in save['run']
assert 'gh auth setup-git' in activation['run']
for name in ['test_verify.py','test_release_speed.py','test_paired_candidate.py','preflight_candidate.py']:
    assert name in next(s for s in steps if s.get('name','').startswith('Verify public'))['run']
print('Public workflow contracts passed; no live stage executed')
