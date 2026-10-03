"""Public Windows preflight. Does not sign, activate a feed, or set the current request."""
import base64,json,os,shutil,subprocess,sys,zipfile,re
from pathlib import Path
from datetime import datetime,timezone
from verify import archive,signature,sha,require,REPO,KEY_ID
ROOT=Path(__file__).resolve().parents[2]
WORK=Path(os.environ['RUNNER_TEMP'])/'suite-v030-public-preflight'
def run(*args):
    r=subprocess.run([str(x) for x in args],capture_output=True,text=True,encoding='utf-8');print(r.stdout);print(r.stderr)
    require(r.returncode==0,'Public preflight command failed');return r.stdout
def write(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def main():
    require(os.name=='nt' and not WORK.exists(),'Fresh Windows preflight required');WORK.mkdir()
    previous=(ROOT/'updates/stable-longterm.signed.json').read_bytes();_,old,_=signature(previous)
    require(old['catalog']['appVersion']=='0.1.27' and old['sequence']==12,'Unexpected current release')
    p=json.loads((ROOT/'releases/v0.1.30/publish.json').read_bytes())['assets'][0]
    p=dict(p,repository=REPO,commit=run('git','rev-parse','HEAD').strip(),appVersion='0.1.30',launcherApi=4)
    m=archive(ROOT/p['path'],p,WORK/'next');oldp=old['catalog']['packages'][0];archive(ROOT/oldp['path'],oldp,WORK/'old')
    source=json.loads((WORK/'next/module-sources.json').read_bytes());identity=lambda r:{k:r.get(k) for k in ['moduleId','repository','repositoryId','defaultBranch']}
    catalog=dict(schema=1,product='ECUSS.ValidationSuite',appVersion='0.1.30',profiles=['master'],modules=[dict(id=x['id'],repository=next(s['repository'] for s in source['modules'] if s['moduleId']==x['id']),version=x['version'],rulesVersion=x['rulesVersion']) for x in m['modules']],packages=[p],removedModules=[],repositoryRegistry=dict(schema=1,suite=identity(source['suite']),modules=[identity(s) for s in source['modules']]))
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
        run(*cc,'-out:'+str(exe),'-reference:'+str(harness/'Ecuss.Desktop.exe'),ROOT/'publisher/automation/PreflightV030Probe.cs')
        require('Checks: 7;' in run(exe,WORK/label,WORK/'catalog.json'),'Incomplete download preflight')
        # Compile the exact post-signature gate before exposing a signing request.
        gate='LegacyImportProbe.cs' if label=='old' else 'PackageProbe.cs'
        run(*cc,'-out:'+str(harness/'SignedGate.exe'),'-reference:'+str(harness/'Ecuss.Desktop.exe'),ROOT/'publisher/automation'/gate)
    payload=dict(schema=1,product='ECUSS.ValidationSuite',channel='stable',sequence=13,issuedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.0000000+00:00'),expiresAt='2099-12-31T23:59:59.0000000+00:00',catalog=catalog)
    raw=(json.dumps(payload,ensure_ascii=False,indent=2)+'\n').encode()
    notes=['업무 도구 Glass UI 통일, 세관 제시 금액 명칭, 승인된 PSR VN/KR 실행 연결을 한 업데이트에 포함합니다.',
           '기존 v0.1.27에서는 업데이트 파일 가져오기 한 번이 필요합니다. 중간 버전과 새 Setup 없이 v0.1.30으로 바로 적용합니다.',
           '번역 오류 수정과 기존 검증·재고 기준을 유지합니다. AMOVINA REVIEW18 / AMOGREEN VINA V1.0.3 기준입니다.',
           '개선본부터 서명된 새 모듈의 누적 온라인 업데이트를 지원합니다. Windows 315개 검사와 공개 다운로드 검사를 통과했습니다.',
           '승인·서명·전달 후 자동 운영 서명 검증·Windows 적용/복구 검사·배포가 진행됩니다. 대화에 완료 메시지를 입력할 필요가 없습니다.']
    request=dict(schema=1,product='TRADE-OPERATIONS-SUITE-PUBLISHER',channel='longterm',state='ready',minimumAssistantVersion='1.1.1',keyId=KEY_ID,payload=base64.b64encode(raw).decode(),payloadSha256=sha(raw),notes=notes)
    request_path=WORK/'request.json';write(request_path,request)
    with zipfile.ZipFile(ROOT/'publisher/assistant-v1.1.1/TRADE_OPERATIONS_SUITE_Master_Signing_Assistant_v1.1.1.zip') as z:z.extractall(WORK/'helper')
    helper=WORK/'helper/TRADE_OPERATIONS_SUITE_Master_Signing_Assistant_v1.1.1/Publisher.Core.psm1'
    require('HELPER_CHECKS=7' in run('powershell','-NoProfile','-File',ROOT/'publisher/automation/CheckV030Request.ps1',helper,request_path,ROOT/'updates/stable-longterm.signed.json',WORK/'history'),'Helper request validation incomplete')
    write(ROOT/'publisher/requests/v0.1.30.json',request)
    write(ROOT/'releases/v0.1.30/PREFLIGHT.json',dict(schema=1,version='0.1.30',sequence=13,packageCommit=p['commit'],packageSha256=p['sha256'],payloadSha256=sha(raw),windowsPublicDownloadChecks=14,helperRequestChecks=7,publicationGateCompiledAgainstActualOldAndNew=True,productionSignaturePending=True,currentRequestActivated=False,stablePublished=False,runUrl=os.environ['RUN_URL']))
    print('PUBLIC PREFLIGHT COMPLETE; archived request only; current request and active feed unchanged.')
if __name__=='__main__':main()
