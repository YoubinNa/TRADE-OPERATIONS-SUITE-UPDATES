"""One reviewed Master/User candidate, one signing payload and one activation gate."""
import base64,json,os,re,shutil,subprocess,time,urllib.request,zipfile
from datetime import datetime,timezone
from pathlib import Path
from verify import require,sha,strict_json,signature,archive,REPO,KEY_ID,catalog_identity
ROOT=Path(__file__).resolve().parents[2]
RUNTIME_URL='https://msedge.sf.dl.delivery.mp.microsoft.com/filestreamingservice/files/06fb6ad8-1976-4e78-9ceb-3ae170edebde/MicrosoftEdgeWebView2RuntimeInstallerX64.exe'
RUNTIME_SHA='771042db15cb5c463bac51a8408e70183d7130e8ac946709384c2223da582c1b'
def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode())
def run(*args):
 result=subprocess.run([str(x) for x in args],cwd=ROOT,capture_output=True,text=True,encoding='utf-8');print(result.stdout);print(result.stderr);require(result.returncode==0,'Paired candidate command failed');return result.stdout.strip()
def asset_hashes(s):return {Path(x['path']).name:x['sha256'] for x in s['assets']}|{x['name']:x['sha256'] for x in s['installers']}
def validate_pair(s):
 require(s.get('schema')==1 and re.fullmatch(r'0\.\d+\.\d+',s.get('version','')),'Paired version/schema')
 require(type(s.get('sequence')) is int and s['sequence']>0,'Paired sequence')
 require(s.get('releaseStage') in ('beta','stable') and s.get('updateMode')=='online','Paired release stage/mode')
 require(s.get('publicContentReviewed') is True and s.get('windowsCandidateVerified') is True and bool(s.get('candidateVerificationRuns')),'Paired review incomplete')
 require([x['profile'] for x in s.get('assets',[])]==['master','user'],'Both exact package profiles required')
 installers=s.setdefault('installers',[])
 require(isinstance(installers,list),'Installer list required')
 legacy=tuple(map(int,s['version'].split('.')))<=(0,1,40)
 mode=s.get('distributionMode','legacy-paired' if legacy else 'update-only')
 require(mode in ('legacy-paired','update-only','requested-setup'),'Unknown distribution mode')
 if mode=='legacy-paired':
  require(legacy and [x['profile'] for x in installers]==['master','user'],'Legacy paired installers required')
 elif mode=='update-only':
  require(not installers,'Routine updates must not include Setup')
 else:
  require(s.get('setupRequested') is True and bool(installers),'Separate Master Setup request required')
  profiles=[x['profile'] for x in installers]
  require(profiles in (['master'],['user'],['master','user']),'Invalid requested Setup profiles')
 for p in s['assets']:
  require(p['path']==f"packages/v{s['version']}/TRADE_OPERATIONS_SUITE_{p['profile'].title()}_v{s['version']}.ecuss-update.zip",'Paired package path')
  require(re.fullmatch('[0-9a-f]{64}',p['sha256']) and type(p['bytes']) is int and 0<p['bytes']<=64*1024*1024,'Paired package hash/size')
  require(p['releaseId'].startswith('desktop-'+s['version']+'-'+p['profile']+'-'),'Paired release ID')
 for p in s['installers']:
  require(p['name']==f"TRADE_OPERATIONS_SUITE_{p['profile'].title()}_Setup_v{s['version']}.exe",'Installer name')
  require(re.fullmatch('[0-9a-f]{64}',p['sha256']) and type(p['bytes']) is int and 0<p['bytes']<=400*1024*1024,'Installer hash/size')
 a=s.get('approval',{})
 require(a.get('explicit') is True and a.get('scope')=='master-user-beta-release' and bool(a.get('approvedAt')),'Explicit paired release approval required')
 require(a.get('version')==s['version'] and a.get('sequence')==s['sequence'] and a.get('assetSha256')==asset_hashes(s),'Approval belongs to other bytes')
 require(isinstance(s.get('notes'),list) and len(s['notes'])>0,'Paired user-facing notes required')
 return s
def decode_parts(folder,record):
 chunks=[];parts=record['parts'];require(0<len(parts)<=400,'Paired fragment count')
 for i,part in enumerate(parts):
  require(part['name']==f"{record['profile']}-{record['kind']}-{i:03d}.b64",'Paired fragment path/order')
  raw=base64.b64decode((folder/part['name']).read_bytes(),validate=True)
  require(len(raw)==part['bytes'] and sha(raw)==part['sha256'],'Paired fragment corruption');chunks.append(raw)
 raw=b''.join(chunks);require(len(raw)==record['transferBytes'] and sha(raw)==record['transferSha256'],'Paired compact bytes changed');return raw
def restore_pair(s):
 if s.get('packageTransport')=='git-binary':
  # Approved distribution ZIPs are Git binary blobs, never base64 source fragments.
  require(s.get('distributionMode')=='update-only' and not s['installers'],'Binary transport is update-only')
  require(not (ROOT/f"releases/v{s['version']}/transfer").exists(),'No duplicate text-encoded bootstrap archive')
  outputs=[]
  for approved in s['assets']:
   target=ROOT/approved['path'];raw=target.read_bytes()
   require(len(raw)==approved['bytes'] and sha(raw)==approved['sha256'],'Exact reviewed binary changed')
   manifest=archive(target,dict(approved,appVersion=s['version']))
   if manifest.get('recordsBootstrap','none')!='none':
    require(s['version']=='0.1.41' and manifest['recordsBootstrap']=='initial-update' and s.get('recordsBootstrapApproval')=='YoubinNa/TRADE-OPERATIONS-WORK-RECORDS','Only approved one-time records bootstrap is permitted')
   outputs.append(target)
  return outputs
 require(s.get('packageTransport','base64-text')=='base64-text','Unknown package transport')
 folder=ROOT/f"releases/v{s['version']}/transfer";index=strict_json((folder/'index.json').read_bytes())
 require(index['schema']==2 and index['version']==s['version'] and index['encoding']=='base64-text','Paired transfer identity')
 records=index['assets'];require([(x['kind'],x['profile']) for x in records]==[('package','master'),('package','user')]+[('setup',x['profile']) for x in s['installers']],'Complete paired transfer required')
 cache=Path(os.environ.get('RUNNER_TEMP',str(ROOT/'_candidate-temp')))/'paired-assets';cache.mkdir(parents=True,exist_ok=True)
 runtime=None;outputs=[]
 for record in records:
  approved=next(x for x in (s['assets'] if record['kind']=='package' else s['installers']) if x['profile']==record['profile'])
  name=Path(approved['path']).name if record['kind']=='package' else approved['name']
  require(record['name']==name and record['sha256']==approved['sha256'] and record['bytes']==approved['bytes'],'Unapproved transfer asset')
  data=decode_parts(folder,record)
  if record['kind']=='setup':
   r=record['runtime'];require(r['url']==RUNTIME_URL and r['sha256']==RUNTIME_SHA and type(r['offset']) is int and 0<=r['offset']<=len(data),'Pinned runtime identity')
   if runtime is None:
    path=cache/'MicrosoftWebView2.exe'
    if not path.exists():urllib.request.urlretrieve(RUNTIME_URL,path)
    runtime=path.read_bytes();require(sha(runtime)==RUNTIME_SHA,'Microsoft runtime changed')
   require(len(runtime)==r['bytes'],'Runtime length');data=data[:r['offset']]+runtime+data[r['offset']:]
  require(len(data)==approved['bytes'] and sha(data)==approved['sha256'],'Exact reviewed reconstruction failed')
  target=ROOT/approved['path'] if record['kind']=='package' else cache/name
  require(not target.exists() or target.read_bytes()==data,'Immutable paired asset already differs');target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
  if record['kind']=='package':archive(target,dict(approved,appVersion=s['version']))
  else:require(data[:2]==b'MZ','Setup PE required')
  outputs.append(target)
 return outputs
def release_assets_match(release,s):
 expected={Path(x['path']).name:(x['bytes'],x['sha256']) for x in s['assets']}|{x['name']:(x['bytes'],x['sha256']) for x in s['installers']}
 require(not release['draft'] and len(release['assets'])==len(expected),'All paired release assets required')
 for asset in release['assets']:
  require(asset['name'] in expected and (asset['size'],asset['digest'])==(expected[asset['name']][0],'sha256:'+expected[asset['name']][1]),'Paired release asset differs')
def stage_pair(s):
 from candidate import check_predecessor,check_slot,commit
 validate_pair(s);_,previous,_=signature((ROOT/'updates/stable-longterm.signed.json').read_bytes());check_predecessor(s,previous)
 saved=ROOT/f"publisher/requests/v{s['version']}.json";check_slot(strict_json((ROOT/'publisher/current-request.json').read_bytes()),strict_json(saved.read_bytes()) if saved.exists() else None)
 outputs=restore_pair(s);folder=ROOT/f"releases/v{s['version']}";write(folder/'publish.json',s)
 (folder/'NOTES.md').write_bytes(('\n'.join(['# Master / User v'+s['version']+' '+s['releaseStage'].title(),'']+['- '+n for n in s['notes']])+'\n').encode())
 commit([x['path'] for x in s['assets']]+[folder.relative_to(ROOT).as_posix()],f"release: stage audited paired v{s['version']} Beta")
 identity=folder/'package-identity.json'
 if identity.exists():
  data=strict_json(identity.read_bytes());require(data['assetSha256']==asset_hashes(s),'Paired identity differs')
  for p in s['assets']:require(sha(subprocess.check_output(['git','show',data['commit']+':'+p['path']],cwd=ROOT))==p['sha256'],'Pinned package differs')
 else:
  data=dict(commit=run('git','rev-parse','HEAD'),assetSha256=asset_hashes(s));write(identity,data);commit([identity.relative_to(ROOT).as_posix()],f"release: pin exact paired v{s['version']} assets")
 existing=subprocess.run(['gh','api',f"repos/{REPO}/releases/tags/v{s['version']}"],cwd=ROOT,capture_output=True)
 if existing.returncode==0:release_assets_match(strict_json(existing.stdout),s)
 else:run('gh','release','create','v'+s['version'],*outputs,'--target',data['commit'],'--title','Master / User v'+s['version']+' Beta — signing candidate','--notes-file',folder/'NOTES.md','--prerelease','--latest=false')
def compiler():
 dotnet=shutil.which('dotnet');candidates=[]
 for line in run(dotnet,'--list-sdks').splitlines():
  m=re.match(r'([0-9.]+) \[(.+)\]',line)
  if m:
   csc=Path(m[2])/m[1]/'Roslyn/bincore/csc.dll'
   if csc.exists():candidates.append((tuple(map(int,m[1].split('.'))),csc))
 refs=Path(os.environ['ProgramFiles(x86)'])/'Reference Assemblies/Microsoft/Framework/.NETFramework/v4.8'
 return [dotnet,sorted(candidates)[-1][1],'-nologo','-target:exe','-platform:x64','-langversion:7.3','-nostdlib+','-warn:4','-warnaserror+']+['-reference:'+str(refs/(n+'.dll')) for n in ['mscorlib','System','System.Core','System.Net.Http','System.Web.Extensions','System.IO.Compression','System.Xml','System.Security']]
def compile_probe(cc,seed,folder,source):
 folder.mkdir(parents=True,exist_ok=True);shutil.copyfile(seed/'Ecuss.Desktop.exe',folder/'Ecuss.Desktop.exe');exe=folder/(Path(source).stem+'.exe');shutil.copyfile(seed/'Ecuss.Desktop.exe.config',Path(str(exe)+'.config'))
 run(*cc,'-out:'+str(exe),'-reference:'+str(folder/'Ecuss.Desktop.exe'),ROOT/'publisher/automation'/source);return exe
def compare_modules(master,user):
 clean=lambda m:[{k:v for k,v in x.items() if k!='capabilities'} for x in m['modules']]
 require(master['appVersion']==user['appVersion'] and clean(master)==clean(user),'Master/User module/rules/core versions differ')
def preflight_pair(s):
 from candidate import check_predecessor
 started=time.monotonic();require(os.name=='nt','Windows paired preflight required');work=Path(os.environ['RUNNER_TEMP'])/'paired-preflight';require(not work.exists(),'Fresh paired preflight');work.mkdir()
 _,old,_=signature((ROOT/'updates/stable-longterm.signed.json').read_bytes());check_predecessor(s,old)
 identity=strict_json((ROOT/f"releases/v{s['version']}/package-identity.json").read_bytes());packages=[dict(x,repository=REPO,commit=identity['commit'],appVersion=s['version'],launcherApi=4) for x in s['assets']]
 manifests={}
 for p in packages:manifests[p['profile']]=archive(ROOT/p['path'],p,work/('next-'+p['profile']))
 compare_modules(manifests['master'],manifests['user'])
 for oldp in old['catalog']['packages']:archive(ROOT/oldp['path'],oldp,work/('old-'+oldp['profile']))
 source=strict_json((work/'next-master/module-sources.json').read_bytes());identity_source=lambda r:{k:r.get(k) for k in ['moduleId','repository','repositoryId','defaultBranch']}
 catalog=dict(schema=1,product='ECUSS.ValidationSuite',appVersion=s['version'],releaseStage=s['releaseStage'],profiles=['master','user'],modules=[dict(id=m['id'],repository=next(r['repository'] for r in source['modules'] if r['moduleId']==m['id']),version=m['version'],rulesVersion=m['rulesVersion']) for m in manifests['master']['modules']],packages=packages,installers=s['installers'],removedModules=s.get('removedModules',[]),repositoryRegistry=dict(schema=1,suite=identity_source(source['suite']),modules=[identity_source(r) for r in source['modules']]))
 catalog_identity(catalog);write(work/'catalog.json',catalog);cc=compiler()
 labels=['old-'+p for p in old['catalog']['profiles']]+['next-master','next-user']
 for label in labels:
  exe=compile_probe(cc,work/label,work/('probe-'+label),'CandidateDownloadProbe.cs');require('Checks: 7;' in run(exe,work/label,work/'catalog.json'),'Paired public download probe incomplete')
  compile_probe(cc,work/label,work/('gate-'+label),'UserBootstrapProbe.cs' if label=='next-user' and 'user' not in old['catalog']['profiles'] else 'PackageProbe.cs')
 for setup in s['installers']:
  url=f"https://github.com/{REPO}/releases/download/v{s['version']}/{setup['name']}";dest=work/setup['name'];urllib.request.urlretrieve(url,dest);require(dest.stat().st_size==setup['bytes'] and sha(dest.read_bytes())==setup['sha256'],'Anonymous exact Setup download failed')
 payload=dict(schema=1,product='ECUSS.ValidationSuite',channel='stable',sequence=s['sequence'],issuedAt=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.0000000+00:00'),expiresAt='2099-12-31T23:59:59.0000000+00:00',catalog=catalog)
 raw=(json.dumps(payload,ensure_ascii=False,indent=2)+'\n').encode();req=dict(schema=1,product='TRADE-OPERATIONS-SUITE-PUBLISHER',channel='longterm',state='ready',minimumAssistantVersion='1.1.1',keyId=KEY_ID,payload=base64.b64encode(raw).decode(),payloadSha256=sha(raw),notes=s['notes'])
 saved=ROOT/f"publisher/requests/v{s['version']}.json"
 if saved.exists():
  req=strict_json(saved.read_bytes());raw=base64.b64decode(req['payload'],validate=True);prior=strict_json(raw);require(prior['catalog']==catalog and prior['sequence']==s['sequence'] and req['notes']==s['notes'] and req['payloadSha256']==sha(raw),'Paired retry differs')
 write(work/'request.json',req)
 with zipfile.ZipFile(ROOT/'publisher/assistant-v1.1.1/TRADE_OPERATIONS_SUITE_Master_Signing_Assistant_v1.1.1.zip') as z:z.extractall(work/'helper')
 helper=work/'helper/TRADE_OPERATIONS_SUITE_Master_Signing_Assistant_v1.1.1/Publisher.Core.psm1'
 require('HELPER_CHECKS=8' in run('powershell','-NoProfile','-File',ROOT/'publisher/automation/CheckPairedRequest.ps1',helper,work/'request.json',ROOT/'updates/stable-longterm.signed.json',work/'history',s['version'],s['sequence'],packages[0]['sha256'],packages[1]['sha256']),'Existing helper rejects paired request')
 write(saved,req);write(ROOT/f"releases/v{s['version']}/PREFLIGHT.json",dict(schema=2,version=s['version'],sequence=s['sequence'],packageCommit=packages[0]['commit'],assetSha256=asset_hashes(s),payloadSha256=sha(raw),profiles=['master','user'],windowsPublicDownloadChecks=7*len(labels),anonymousSetupDownloads=len(s['installers']),helperRequestChecks=8,pairedModulesIdentical=True,publicationGateCompiledAgainstActualOldAndNew=True,productionSignaturePending=True,currentRequestActivated=False,stablePublished=False,runUrl=os.environ['RUN_URL'],preflightElapsedSeconds=round(time.monotonic()-started,3)))
def activation_pair(s,request,evidence,previous,current):
 from candidate import check_predecessor,check_slot
 validate_pair(s);check_predecessor(s,previous);check_slot(current,request);raw=base64.b64decode(request['payload'],validate=True)
 require(request['payloadSha256']==sha(raw)==evidence['payloadSha256'],'Paired checked payload differs');d=strict_json(raw);c=d['catalog'];catalog_identity(c)
 require(request['state']=='ready' and c['profiles']==['master','user'] and d['sequence']==s['sequence'] and c['appVersion']==s['version'],'Paired request identity')
 require(c.get('installers')==s['installers'] and c.get('releaseStage')==s['releaseStage'],'Paired Setup/stage identity')
 for p,a in zip(c['packages'],s['assets']):require(all(p[k]==a[k] for k in ['profile','path','releaseId','bytes','sha256']) and p['commit']==evidence['packageCommit'],'Paired approved package differs')
 require(evidence['version']==s['version'] and evidence['sequence']==s['sequence'] and evidence['assetSha256']==asset_hashes(s),'Paired evidence identity')
 require(evidence.get('profiles')==['master','user'] and evidence.get('windowsPublicDownloadChecks')==7*(2+len(previous['catalog']['profiles'])) and evidence.get('anonymousSetupDownloads')==len(s['installers']) and evidence.get('helperRequestChecks')==8 and evidence.get('pairedModulesIdentical') is True and evidence.get('publicationGateCompiledAgainstActualOldAndNew') is True,'Paired Windows gates incomplete')
 return dict(schema=1,enabled=True,payloadSha256=sha(raw),requiredActiveVersion=s['requiredActiveVersion'],publicContentReviewed=True,windowsCandidateVerified=True,candidateVerificationRuns=s['candidateVerificationRuns'],masterReleaseApprovedAt=s['approval']['approvedAt'],updateMode='online',scope='Master/User same version, one approved Beta release',profiles=['master','user'],releaseStage=s['releaseStage'],assetSha256=asset_hashes(s))
