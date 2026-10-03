"""Receive -> validate immutable signed candidate -> Windows probe -> CAS publication."""
import json, os, re, shutil, subprocess, sys, time, urllib.request
from pathlib import Path
from verify import REPO, archive, ready, require, sha, signature, strict_json, update_mode, registry_matches
ROOT=Path(__file__).resolve().parents[2]
WORK=Path(os.environ.get('RUNNER_TEMP', str(ROOT.parent/'auto-publish-temp')))/'suite-auto-publish'
FEED='updates/stable-longterm.signed.json'

def run(*args, **kw):
    try:
        return subprocess.check_output([str(a) for a in args], **kw).decode('utf-8').strip()
    except subprocess.CalledProcessError as e:
        print(e.output.decode('utf-8', errors='replace'))
        raise

def write(p,d):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes((json.dumps(d,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))

def output(name,value):
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a',encoding='utf-8') as f:f.write(f'{name}={value}\n')

def prepare():
    r=ready(ROOT)
    if r is None:output('ready','false');print('No pending current signed request.');return
    require(os.name=='nt','Windows production verification required')
    require(not WORK.exists(),'Clean workspace required');WORK.mkdir(parents=True)
    (WORK/'candidate.json').write_bytes(r['envelope']);(WORK/'previous.json').write_bytes(r['previous'])
    for label,d in [('old',r['previousPayload']),('next',r['payload'])]:
        p=d['catalog']['packages'][0]
        # A signed commit/path must point to exactly the staged bytes. No moving package refs.
        raw=subprocess.check_output(['git','show',p['commit']+':'+p['path']],cwd=ROOT)
        require(len(raw)==p['bytes'] and sha(raw)==p['sha256'],'Immutable git package mismatch')
        local=ROOT/p['path'];require(local.read_bytes()==raw,'Working package changed')
        archive(local,p,WORK/label)
        registry_matches(WORK/label,d['catalog'])
    version=r['payload']['catalog']['appVersion']
    public=strict_json((ROOT/f'releases/v{version}/publish.json').read_bytes())
    p=r['payload']['catalog']['packages'][0]
    require(public['version']==version and len(public['assets'])==1,'Public candidate review record')
    a=public['assets'][0]
    require(all(a[k]==p[k] for k in ['profile','path','releaseId','bytes','sha256']),'Public reviewed bytes mismatch')
    metadata=dict(head=run('git','rev-parse','HEAD',cwd=ROOT),version=version,sequence=r['payload']['sequence'],requestSha256=sha(r['requestRaw']),envelopeSha256=sha(r['envelope']),resumed=r['resumed'],updateMode=update_mode(r['plan'],r['payload']['catalog']))
    write(WORK/'state.json',metadata)
    output('ready','true');output('version',version)
    print('Production signature, exact request, enabled plan and complete immutable inventories verified.')

def probe():
    require(os.name=='nt','Windows only')
    dotnet=shutil.which('dotnet');require(dotnet,'SDK required')
    candidates=[]
    for line in run(dotnet,'--list-sdks').splitlines():
        m=re.match(r'([0-9.]+) \[(.+)\]',line)
        if m:
            p=Path(m[2])/m[1]/'Roslyn/bincore/csc.dll'
            if p.exists():candidates.append((tuple(map(int,m[1].split('.'))),p))
    require(candidates,'Roslyn required')
    refs=Path(os.environ['ProgramFiles(x86)'])/'Reference Assemblies/Microsoft/Framework/.NETFramework/v4.8'
    names=['mscorlib','System','System.Core','System.Net.Http','System.Web.Extensions','System.IO.Compression','System.Xml','System.Security']
    count=0
    state=strict_json((WORK/'state.json').read_bytes())
    for label in ['old','next']:
        h=WORK/('probe-'+label);h.mkdir()
        shutil.copyfile(WORK/label/'Ecuss.Desktop.exe',h/'Ecuss.Desktop.exe')
        exe=h/'PackageProbe.exe'
        shutil.copyfile(WORK/label/'Ecuss.Desktop.exe.config',Path(str(exe)+'.config'))
        cmd=[dotnet,sorted(candidates)[-1][1],'-nologo','-target:exe','-platform:x64','-langversion:7.3','-nostdlib+','-warn:4','-warnaserror+']+['-reference:'+str(refs/(n+'.dll')) for n in names]
        source='LegacyImportProbe.cs' if label=='old' and state['updateMode']=='legacy-import-once' else 'PackageProbe.cs'
        print(run(*cmd,'-out:'+str(exe),'-reference:'+str(h/'Ecuss.Desktop.exe'),ROOT/'publisher/automation'/source))
        result=run(exe,WORK/'old',WORK/'next',WORK/'candidate.json',WORK/'previous.json')
        print(label+': '+result)
        require('CHECKS=18' in result,'Incomplete production probe');count+=18
    state=strict_json((WORK/'state.json').read_bytes());state['windowsChecks']=count;write(WORK/'state.json',state)

def github(*args):return run('gh',*args,cwd=ROOT)

def guard(state):
    run('git','fetch','origin','main',cwd=ROOT)
    require(run('git','rev-parse','origin/main',cwd=ROOT)==state['head'],'Repository advanced; retry against latest reviewed request')
    r=ready(ROOT)
    require(r is not None and sha(r['requestRaw'])==state['requestSha256'] and sha(r['envelope'])==state['envelopeSha256'],'Request changed')
    return r

def commit(paths,message):
    run('git','config','user.name','github-actions[bot]',cwd=ROOT)
    run('git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com',cwd=ROOT)
    run('git','add','--',*paths,cwd=ROOT)
    run('git','commit','-m',message,cwd=ROOT)
    # Normal push (never force) is the compare-and-swap: a concurrent change fails closed.
    run('git','push','origin','HEAD:refs/heads/main',cwd=ROOT)

def publish():
    state=strict_json((WORK/'state.json').read_bytes());require(state.get('windowsChecks')==36,'Windows gate missing')
    r=guard(state);p=r['payload']['catalog']['packages'][0];v=state['version'];seq=state['sequence']
    release=strict_json(github('api',f'repos/{REPO}/releases/tags/v{v}'))
    require(not release['draft'] and len(release['assets'])==1,'Public candidate release missing')
    a=release['assets'][0]
    require(a['name']==Path(p['path']).name and a['size']==p['bytes'] and a['digest']=='sha256:'+p['sha256'],'Release asset mismatch')
    base=f'publisher/publications/seq-{seq}'
    if not r['resumed']:
        (ROOT/base).mkdir(parents=True,exist_ok=True)
        (ROOT/base/'previous.signed.json').write_bytes(r['previous'])
        (ROOT/FEED).write_bytes(r['envelope'])
        write(ROOT/base/'status.json',dict(schema=1,state='feed-published',version=v,sequence=seq,windowsChecks=36,updateMode=state['updateMode'],runUrl=os.environ['RUN_URL'],userPcVerified=False))
        commit([FEED,base],f'publish: verified Master v{v} sequence {seq}')
        state['head']=run('git','rev-parse','HEAD',cwd=ROOT);write(WORK/'state.json',state)
    print('Verified feed published. Public retrieval and release promotion follow.')

def finish():
    state=strict_json((WORK/'state.json').read_bytes());r=guard(state)
    require((ROOT/FEED).read_bytes()==r['envelope'],'Active feed mismatch')
    # Both the public API and raw URL are read anonymously. CDN propagation gets a bounded retry.
    url=f'https://raw.githubusercontent.com/{REPO}/main/{FEED}'
    matched=False
    for attempt in range(12):
        with urllib.request.urlopen(url,timeout=30) as response:raw=response.read(1048577)
        if raw==r['envelope']:matched=True;break
        time.sleep(10)
    require(matched,'Public feed propagation not yet confirmed; rerun safely resumes')
    signature(raw)
    v=state['version'];seq=state['sequence'];base=f'publisher/publications/seq-{seq}'
    github('release','edit',f'v{v}','--prerelease=false','--latest','--title',f'TRADE OPERATIONS SUITE — Master v{v}','--notes-file',f'releases/v{v}/NOTES.md')
    release=strict_json(github('api',f'repos/{REPO}/releases/tags/v{v}'))
    require(not release['prerelease'] and not release['draft'],'Release promotion incomplete')
    # Recheck branch immediately before writing completion; any different request is never cleared.
    guard(state)
    status=dict(schema=1,state='completed',version=v,sequence=seq,windowsChecks=36,productionSignatureVerified=True,anonymousPackageDownloads=2,publicFeedVerified=True,applyRollbackAndDataPreservation=True,updateMode=state['updateMode'],legacyImportRequired=state['updateMode']=='legacy-import-once',runUrl=os.environ['RUN_URL'],userPcVerified=False)
    write(ROOT/base/'status.json',status);write(ROOT/'publisher/status.json',status)
    write(ROOT/'publisher/current-request.json',dict(schema=1,product='TRADE-OPERATIONS-SUITE-PUBLISHER',channel='longterm',state='idle',lastPublishedVersion=v,lastPublishedSequence=seq,statusUrl=f'https://github.com/{REPO}/blob/main/publisher/status.json'))
    commit([base,'publisher/status.json','publisher/current-request.json'],f'publisher: automatic delivery completed for v{v}')
    print('COMPLETE: signed receipt -> Windows checks -> public activation. No chat acknowledgement required.')

if __name__=='__main__':
    {'prepare':prepare,'probe':probe,'publish':publish,'finish':finish}[sys.argv[1]]()
