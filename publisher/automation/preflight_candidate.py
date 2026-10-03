"""Public Windows preflight. Does not sign, activate a feed, or set the current request."""
import base64,json,os,shutil,subprocess,sys,zipfile,re,time
from candidate import load_spec, check_predecessor
from pathlib import Path
from datetime import datetime,timezone
from verify import archive,signature,sha,require,REPO,KEY_ID
ROOT=Path(__file__).resolve().parents[2]
WORK=Path(os.environ['RUNNER_TEMP'])/'suite-candidate-preflight'
def run(*args):
    r=subprocess.run([str(x) for x in args],capture_output=True,text=True,encoding='utf-8');print(r.stdout);print(r.stderr)
    require(r.returncode==0,'Public preflight command failed');return r.stdout
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def main():
    started=time.monotonic()
    spec=load_spec(sys.argv[1]);version=spec['version'];sequence=spec['sequence']
    if len(spec['assets'])==2:
        from paired_candidate import preflight_pair
        return preflight_pair(spec)
    require(os.name=='nt' and not WORK.exists(),'Fresh Windows preflight required');WORK.mkdir()
    previous=(ROOT/'updates/stable-longterm.signed.json').read_bytes();_,old,_=signature(previous)
    check_predecessor(spec,old)
    p=spec['assets'][0]
    identity=json.loads((ROOT/f'releases/v{version}/package-identity.json').read_bytes())
    p=dict(p,repository=REPO,commit=identity['commit'],appVersion=version,launcherApi=4)
    m=archive(ROOT/p['path'],p,WORK/'next');oldp=old['catalog']['packages'][0];archive(ROOT/oldp['path'],oldp,WORK/'old')
    source=json.loads((WORK/'next/module-sources.json').read_bytes());identity=lambda r:{k:r.get(k) for k in ['moduleId','repository','repositoryId','defaultBranch']}
    catalog=dict(schema=1,product='ECUSS.ValidationSuite',appVersion=version,profiles=['master'],modules=[dict(id=x['id'],repository=next(s['repository'] for s in source['modules'] if s['moduleId']==x['id']),version=x['version'],rulesVersion=x['rulesVersion']) for x in m['modules']],packages=[p],removedModules=spec.get('removedModules',[]),repositoryRegistry=dict(schema=1,suite=identity(source['suite']),modules=[identity(s) for s in source['modules']]))
    write(WORK/'catalog.json',catalog)
    dotnet=shutil.which('dotnet');candidates=[]
    for line in run(dotnet,'--list-sdks').splitlines():
        match=re.match(r'([0-9.]+) \[(.+)\]',line)
        if match:
            csc=Path(match[2])/match[1]/'Roslyn/bincore/csc.dll'
            if csc.exists():candidates.append((tuple(map(int,match[1].split('.'))),csc))
    refs=Path(os.environ['ProgramFiles(x86)'])/'Reference Assemblies/Microsoft/Framework/.NETFramework/v4.8'
    names=['mscorlib','System','System.Core','System.Net.Http','System.Web.Extensions','System.IO.Compression','System.Xml','System.Security']
    cc=[dotnet,sorted(candidates)[-1][1],'-nologo','-target:exe','-platform:x64','-langversion:7.3','-nostdlib+','-warn:4','-warnaserror+']+['-reference:'+str(refs/(n+'.dll')) for n in names]
    for label in ['old','next']:
        harness=WORK/('harness-'+label);harness.mkdir();shutil.copyfile(WORK/label/'Ecuss.Desktop.exe',harness/'Ecuss.Desktop.exe')
        exe=harness/'Preflight.exe';shutil.copyfile(WORK/label/'Ecuss.Desktop.exe.config',Path(str(exe)+'.config'))
        run(*cc,'-out:'+str(exe),'-reference:'+str(harness/'Ecuss.Desktop.exe'),ROOT/'publisher/automation/CandidateDownloadProbe.cs')
        require('Checks: 7;' in run(exe,WORK/label,WORK/'catalog.json'),'Incomplete download preflight')
        # Compile the exact post-signature gate before exposing a signing request.
        gate='LegacyImportProbe.cs' if label=='old' and spec.get('updateMode','online')=='legacy-import-once' else 'PackageProbe.cs'
        run(*cc,'-out:'+str(harness/'SignedGate.exe'),'-reference:'+str(harness/'Ecuss.Desktop.exe'),ROOT/'publisher/automation'/gate)
    payload=dict(schema=1,product='ECUSS.ValidationSuite',channel='stable',sequence=sequence,issuedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.0000000+00:00'),expiresAt='2099-12-31T23:59:59.0000000+00:00',catalog=catalog)
    raw=(json.dumps(payload,ensure_ascii=False,indent=2)+'\n').encode()
    notes=spec['notes']
    request=dict(schema=1,product='TRADE-OPERATIONS-SUITE-PUBLISHER',channel='longterm',state='ready',minimumAssistantVersion='1.1.1',keyId=KEY_ID,payload=base64.b64encode(raw).decode(),payloadSha256=sha(raw),notes=notes)
    saved=ROOT/f'publisher/requests/v{version}.json'
    if saved.exists():
        existing=json.loads(saved.read_bytes()); prior=json.loads(base64.b64decode(existing['payload'],validate=True))
        require(prior['catalog']==catalog and prior['sequence']==sequence and existing['notes']==notes,'Archived request belongs to different candidate')
        request=existing;raw=base64.b64decode(existing['payload'],validate=True)
        require(request['payloadSha256']==sha(raw),'Archived request hash mismatch')
    request_path=WORK/'request.json';write(request_path,request)
    with zipfile.ZipFile(ROOT/'publisher/assistant-v1.1.1/TRADE_OPERATIONS_SUITE_Master_Signing_Assistant_v1.1.1.zip') as z:z.extractall(WORK/'helper')
    helper=WORK/'helper/TRADE_OPERATIONS_SUITE_Master_Signing_Assistant_v1.1.1/Publisher.Core.psm1'
    require('HELPER_CHECKS=7' in run('powershell','-NoProfile','-File',ROOT/'publisher/automation/CheckCandidateRequest.ps1',helper,request_path,ROOT/'updates/stable-longterm.signed.json',WORK/'history',version,str(sequence),p['sha256']),'Helper request validation incomplete')
    write(ROOT/f'publisher/requests/v{version}.json',request)
    write(ROOT/f'releases/v{version}/PREFLIGHT.json',dict(schema=1,version=version,sequence=sequence,packageCommit=p['commit'],packageSha256=p['sha256'],payloadSha256=sha(raw),windowsPublicDownloadChecks=14,helperRequestChecks=7,publicationGateCompiledAgainstActualOldAndNew=True,productionSignaturePending=True,currentRequestActivated=False,stablePublished=False,runUrl=os.environ['RUN_URL'],preflightElapsedSeconds=round(time.monotonic()-started,3)))
    print('PUBLIC PREFLIGHT COMPLETE; activate step sends this exact request under the recorded approval.')
if __name__=='__main__':main()
