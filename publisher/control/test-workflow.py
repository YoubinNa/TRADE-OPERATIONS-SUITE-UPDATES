import json,re,yaml
from pathlib import Path
data=yaml.load(Path('.github/workflows/prepare-candidate.yml').read_text(encoding='utf-8'),Loader=yaml.BaseLoader)
assert set(data['on'])=={'push','workflow_dispatch'}
assert data['on']['push']=={'branches':['main'],'paths':['publisher/execution-requests/*.json']}
assert 'inspect' in data['on']['workflow_dispatch']['inputs']['operation']['options']
resolver=data['jobs']['resolve']
assert resolver['permissions']=={'contents':'read'}
assert resolver['outputs']=={k:'${{ steps.scope.outputs.'+k+' }}' for k in ['candidate','operation','job_id']}
assert data['jobs']['candidate']['needs']=='resolve'
assert data['jobs']['candidate']['if']=="needs.resolve.outputs.operation != 'inspect'"
assert next(s for s in resolver['steps'] if s.get('id')=='scope')['run']=='node publisher/control/resolve-execution.cjs'
assert next(s for s in resolver['steps'] if s.get('id')=='scope')['env']['RELEASE_CONTROL_TOKEN']=='${{ github.token }}'
assert not any('candidate.py' in s.get('run','') or 'gh auth' in s.get('run','') for s in resolver['steps'])
assert data['on']['workflow_dispatch']['inputs']['operation']['default']=='prepare'
assert data['concurrency']['group']=='master-longterm-publication'
assert data['concurrency']['cancel-in-progress']=='false'
steps=data['jobs']['candidate']['steps']
for start,modes,guard in [('Verify approval',['prepare','stage','full'],'public-stage'),('Verify public',['prepare','preflight','full'],'preflight'),('Send exact',['activate','full'],'activate')]:
    s=next(s for s in steps if s.get('name','').startswith(start))
    assert json.loads(re.search(r"fromJSON\('(.+)'\)",s['if']).group(1))==modes
    assert 'execution-control-guard.cjs $env:SPEC '+guard in s['run']
    assert 'needs.resolve.outputs.operation' in s['if']
    assert s['env']['SPEC']=='${{ needs.resolve.outputs.candidate }}'
save=next(s for s in steps if s.get('name','').startswith('Preserve exact'))
activation=next(s for s in steps if s.get('name','').startswith('Send exact'))
assert steps.index(save)<steps.index(activation)
assert 'preserve-preflight.py' in save['run']
assert 'gh auth setup-git' in activation['run']
for name in ['test_verify.py','test_release_speed.py','test_paired_candidate.py','preflight_candidate.py']:
    assert name in next(s for s in steps if s.get('name','').startswith('Verify public'))['run']
print('Public workflow contracts passed; no live stage executed')

assert data['jobs']['candidate']['env']['RELEASE_CONTROL_TOKEN']=='${{ github.token }}'
assert 'secrets.RELEASE_CONTROL_TOKEN' not in Path('.github/workflows/prepare-candidate.yml').read_text()
assert 'TRADE-OPERATIONS-SUITE-UPDATES/contents/publisher/control/jobs/' in Path('publisher/control/shared-control.cjs').read_text()

assert data['jobs']['candidate']['env']['RELEASE_CONTROL_JOB_ID']=='${{ needs.resolve.outputs.job_id }}'
print('Connector push and inspect-only workflow contracts passed')
