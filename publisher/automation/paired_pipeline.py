"""Atomic Master/User publication after one exact production signing request."""
import os,subprocess
from pathlib import Path
import pipeline as base
from paired_candidate import validate_pair,asset_hashes,compare_modules,compiler,compile_probe,release_assets_match
from verify import ready,require,strict_json,signature,sha,archive,registry_matches,REPO
from records_gate import check_pair as check_records_pair, require_pair as require_records_pair
ROOT,WORK,FEED=base.ROOT,base.WORK,base.FEED

def prepare():
 r=ready(ROOT)
 if r is None:base.output('ready','false');print('No signed paired request.');return
 require(os.name=='nt' and not WORK.exists(),'Clean Windows paired workspace required');WORK.mkdir(parents=True)
 (WORK/'candidate.json').write_bytes(r['envelope']);(WORK/'previous.json').write_bytes(r['previous'])
 c=r['payload']['catalog'];v=c['appVersion'];s=validate_pair(strict_json((ROOT/f'releases/v{v}/publish.json').read_bytes()))
 require(c['profiles']==['master','user'] and c.get('installers')==s['installers'] and c.get('releaseStage')==s['releaseStage'],'Paired signed scope changed')
 require(r['plan'].get('profiles')==['master','user'] and r['plan'].get('assetSha256')==asset_hashes(s),'Paired approval changed')
 for p,a in zip(c['packages'],s['assets']):require(all(p[k]==a[k] for k in ('profile','path','releaseId','bytes','sha256')),'Signed pair differs from reviewed bytes')
 manifests={}
 for label,payload in [('old',r['previousPayload']),('next',r['payload'])]:
  for p in payload['catalog']['packages']:
   raw=subprocess.check_output(['git','show',p['commit']+':'+p['path']],cwd=ROOT)
   require(len(raw)==p['bytes'] and sha(raw)==p['sha256'] and (ROOT/p['path']).read_bytes()==raw,'Immutable paired package changed')
   target=WORK/(label+'-'+p['profile']);manifests[label+'-'+p['profile']]=archive(ROOT/p['path'],p,target);registry_matches(target,payload['catalog'])
 compare_modules(manifests['next-master'],manifests['next-user'])
 state=dict(head=base.run('git','rev-parse','HEAD',cwd=ROOT),version=v,sequence=r['payload']['sequence'],requestSha256=sha(r['requestRaw']),envelopeSha256=sha(r['envelope']),resumed=r['resumed'],updateMode='online',profiles=['master','user'],releaseStage=s['releaseStage'],oldProfiles=r['previousPayload']['catalog']['profiles'])
 base.write(WORK/'state.json',state);base.output('ready','true');base.output('version',v)

def probe():
 require(os.name=='nt','Windows paired gate required');state=strict_json((WORK/'state.json').read_bytes());cc=compiler();counts={};downloads=0
 for profile in ['master','user']:
  if profile in state['oldProfiles']:
   counts[profile]=0
   for label in ['old','next']:
    exe=compile_probe(cc,WORK/(label+'-'+profile),WORK/('gate-'+label+'-'+profile),'PackageProbe.cs')
    result=base.run(exe,WORK/('old-'+profile),WORK/('next-'+profile),WORK/'candidate.json',WORK/'previous.json');print(result)
    require('CHECKS=18' in result,'Paired update/apply/rollback gate incomplete');counts[profile]+=18;downloads+=1
  else:
   require(profile=='user','Master predecessor missing');exe=compile_probe(cc,WORK/'next-user',WORK/'gate-next-user','UserBootstrapProbe.cs')
   result=base.run(exe,WORK/'next-user',WORK/'candidate.json',WORK/'previous.json');print(result);require('CHECKS=15' in result,'User bootstrap gate incomplete');counts[profile]=15;downloads+=1
 records_profiles=check_records_pair(state['version'],WORK,cc,compile_probe,base.run,'signed')
 state.update(recordsConnectionProfiles=records_profiles,windowsChecksByProfile=counts,windowsChecks=sum(counts.values()),anonymousPackageDownloads=downloads,pairedModulesIdentical=True)
 base.write(WORK/'state.json',state)

def require_gates(state):
 require_records_pair(state['version'],state.get('recordsConnectionProfiles'))
 expected={p:(36 if p in state['oldProfiles'] else 15) for p in ['master','user']}
 require(state.get('windowsChecksByProfile')==expected and state.get('windowsChecks')==sum(expected.values()) and state.get('pairedModulesIdentical') is True,'Both profile gates required')

def publish():
 state=strict_json((WORK/'state.json').read_bytes());require_gates(state);r=base.guard(state);v=state['version'];seq=state['sequence']
 s=validate_pair(strict_json((ROOT/f'releases/v{v}/publish.json').read_bytes()));release_assets_match(strict_json(base.github('api',f'repos/{REPO}/releases/tags/v{v}')),s)
 folder=f'publisher/publications/seq-{seq}'
 if not r['resumed']:
  (ROOT/folder).mkdir(parents=True,exist_ok=True);(ROOT/folder/'previous.signed.json').write_bytes(r['previous']);(ROOT/FEED).write_bytes(r['envelope'])
  base.write(ROOT/folder/'status.json',dict(schema=2,state='feed-published',version=v,sequence=seq,profiles=['master','user'],releaseStage=s['releaseStage'],windowsChecksByProfile=state['windowsChecksByProfile'],windowsChecks=state['windowsChecks'],runUrl=os.environ['RUN_URL'],userPcVerified=False))
  base.commit([FEED,folder],f'publish: atomic Master/User v{v} sequence {seq}');state['head']=base.run('git','rev-parse','HEAD',cwd=ROOT);base.write(WORK/'state.json',state)

def finish():
 state=strict_json((WORK/'state.json').read_bytes());require_gates(state);r=base.guard(state);require((ROOT/FEED).read_bytes()==r['envelope'],'Paired feed mismatch')
 feed_checks=base.verify_public_feed(REPO,FEED,state['head'],r['envelope'],signature);v=state['version'];seq=state['sequence'];folder=f'publisher/publications/seq-{seq}';beta=state['releaseStage']=='beta'
 base.github('release','edit',f'v{v}','--prerelease='+str(beta).lower(),'--latest='+str(not beta).lower(),'--title',f'TRADE OPERATIONS SUITE — Master / User v{v}'+(' Beta' if beta else ''),'--notes-file',f'releases/v{v}/NOTES.md')
 release=strict_json(base.github('api',f'repos/{REPO}/releases/tags/v{v}'));require(release['prerelease']==beta,'Release stage changed');release_assets_match(release,strict_json((ROOT/f'releases/v{v}/publish.json').read_bytes()));base.guard(state)
 records_profiles=check_records_pair(state['version'],WORK,compiler(),compile_probe,base.run,'published')
 status=dict(recordsConnectionProfiles=records_profiles,schema=2,state='completed',version=v,sequence=seq,profiles=['master','user'],releaseStage=state['releaseStage'],oneSignedPayload=True,pairedModulesIdentical=True,windowsChecks=state['windowsChecks'],windowsChecksByProfile=state['windowsChecksByProfile'],productionSignatureVerified=True,anonymousPackageDownloads=state['anonymousPackageDownloads'],publicFeedVerified=True,publicFeedChecks=feed_checks,applyRollbackProfiles=state['oldProfiles'],firstPublicInstallProfiles=[p for p in ['master','user'] if p not in state['oldProfiles']],settingsAndResultsPreserved=True,updateMode='online',runUrl=os.environ['RUN_URL'],userPcVerified=False)
 base.write(ROOT/folder/'status.json',status);base.write(ROOT/'publisher/status.json',status);base.write(ROOT/'publisher/current-request.json',dict(schema=1,product='TRADE-OPERATIONS-SUITE-PUBLISHER',channel='longterm',state='idle',lastPublishedVersion=v,lastPublishedSequence=seq,profiles=['master','user'],statusUrl=f'https://github.com/{REPO}/blob/main/publisher/status.json'))
 base.commit([folder,'publisher/status.json','publisher/current-request.json'],f'publisher: synchronized Master/User v{v} complete');print('COMPLETE: one signed payload, both profiles verified, one public feed activated.')

