"""Reject incomplete pairs, changed installers and partial publication gates."""
import base64,copy,json,tempfile,unittest
from pathlib import Path
from candidate import check_predecessor
from paired_candidate import validate_pair,asset_hashes,activation_pair,compare_modules,decode_parts,release_assets_match
from paired_pipeline import require_gates
from verify import catalog_identity,sha,REPO
class Pair(unittest.TestCase):
 def setUp(self):
  self.s=dict(schema=1,version='0.1.35',sequence=17,requiredActiveVersion='0.1.34',releaseStage='beta',updateMode='online',publicContentReviewed=True,windowsCandidateVerified=True,candidateVerificationRuns=['https://example.invalid/verified'],notes=['Synthetic test'],assets=[dict(profile=p,path=f'packages/v0.1.35/TRADE_OPERATIONS_SUITE_{p.title()}_v0.1.35.ecuss-update.zip',releaseId='desktop-0.1.35-'+p+'-synthetic',bytes=100,sha256=str(i)*64) for i,p in enumerate(['master','user'],1)],installers=[dict(profile=p,name=f'TRADE_OPERATIONS_SUITE_{p.title()}_Setup_v0.1.35.exe',bytes=200,sha256=str(i)*64) for i,p in enumerate(['master','user'],3)])
  self.s['approval']=dict(explicit=True,scope='master-user-beta-release',approvedAt='2026-10-03T14:01:10Z',version='0.1.35',sequence=17,assetSha256=asset_hashes(self.s))
  self.c=dict(schema=1,product='ECUSS.ValidationSuite',appVersion='0.1.35',profiles=['master','user'],releaseStage='beta',installers=self.s['installers'],packages=[dict(x,repository=REPO,appVersion='0.1.35',commit='a'*40,launcherApi=4) for x in self.s['assets']])
  raw=json.dumps(dict(sequence=17,catalog=self.c)).encode();self.req=dict(state='ready',payload=base64.b64encode(raw).decode(),payloadSha256=sha(raw));self.prev=dict(sequence=16,catalog=dict(appVersion='0.1.34',profiles=['master']))
  self.e=dict(version='0.1.35',sequence=17,payloadSha256=sha(raw),packageCommit='a'*40,assetSha256=asset_hashes(self.s),profiles=['master','user'],windowsPublicDownloadChecks=21,anonymousSetupDownloads=2,helperRequestChecks=8,pairedModulesIdentical=True,publicationGateCompiledAgainstActualOldAndNew=True)
 def activate(self):return activation_pair(self.s,self.req,self.e,self.prev,{'state':'idle'})
 def test_complete(self):self.assertEqual(self.activate()['profiles'],['master','user']);catalog_identity(self.c)
 def test_update_only_requires_no_setup(self):
  self.s['distributionMode']='update-only';self.s['installers']=[]
  self.s['approval']['assetSha256']=asset_hashes(self.s)
  self.assertEqual(validate_pair(self.s)['installers'],[])
 def test_routine_update_rejects_setup(self):
  self.s['distributionMode']='update-only'
  with self.assertRaises(ValueError):validate_pair(self.s)
 def test_requested_setup_requires_explicit_request(self):
  self.s['distributionMode']='requested-setup'
  with self.assertRaises(ValueError):validate_pair(self.s)
  self.s['setupRequested']=True
  self.assertEqual(len(validate_pair(self.s)['installers']),2)
 def test_update_only_activation_keeps_all_other_gates(self):
  self.s['distributionMode']='update-only';self.s['installers']=[];self.c['installers']=[]
  self.s['approval']['assetSha256']=asset_hashes(self.s)
  raw=json.dumps(dict(sequence=17,catalog=self.c)).encode()
  self.req['payload']=base64.b64encode(raw).decode();self.req['payloadSha256']=sha(raw)
  self.e.update(payloadSha256=sha(raw),assetSha256=asset_hashes(self.s),anonymousSetupDownloads=0)
  self.assertEqual(self.activate()['profiles'],['master','user'])
  self.e['windowsPublicDownloadChecks']=0
  with self.assertRaises(ValueError):self.activate()
 def test_missing_user(self):
  self.s['assets'].pop()
  with self.assertRaises(ValueError):validate_pair(self.s)
 def test_duplicate_profile(self):
  self.c['packages'][1]['profile']='master'
  with self.assertRaises(ValueError):catalog_identity(self.c)
 def test_different_commit(self):
  self.c['packages'][1]['commit']='b'*40
  with self.assertRaises(ValueError):catalog_identity(self.c)
 def test_different_version(self):
  self.c['packages'][1]['appVersion']='0.1.36'
  with self.assertRaises(ValueError):catalog_identity(self.c)
 def test_changed_installer(self):
  self.s['installers'][1]['sha256']='f'*64
  with self.assertRaises(ValueError):validate_pair(self.s)
 def test_missing_installer(self):
  self.s['installers'].pop()
  with self.assertRaises(ValueError):validate_pair(self.s)
 def test_missing_review(self):
  self.s['windowsCandidateVerified']=False
  with self.assertRaises(ValueError):self.activate()
 def test_partial_preflight(self):
  for key,value in [('windowsPublicDownloadChecks',14),('anonymousSetupDownloads',1),('helperRequestChecks',7),('pairedModulesIdentical',False)]:
   old=self.e[key];self.e[key]=value
   with self.assertRaises(ValueError):self.activate()
   self.e[key]=old
 def test_future_update_cannot_drop_user(self):
  self.prev['catalog']['profiles']=['master','user'];self.s['assets'].pop()
  with self.assertRaises(ValueError):check_predecessor(self.s,self.prev)
 def test_different_modules(self):
  m=dict(appVersion='0.1.35',modules=[dict(id='psr',version='1',rulesVersion='2',capabilities=['a'])]);u=copy.deepcopy(m);u['modules'][0]['capabilities']=[];compare_modules(m,u);u['modules'][0]['rulesVersion']='3'
  with self.assertRaises(ValueError):compare_modules(m,u)
 def test_partial_postsignature_gate(self):
  s=dict(oldProfiles=['master'],windowsChecksByProfile=dict(master=36,user=15),windowsChecks=51,pairedModulesIdentical=True);require_gates(s);s['windowsChecksByProfile'].pop('user')
  with self.assertRaises(ValueError):require_gates(s)
 def test_future_both_upgrade_gates(self):
  s=dict(oldProfiles=['master','user'],windowsChecksByProfile=dict(master=36,user=36),windowsChecks=72,pairedModulesIdentical=True);require_gates(s);s['windowsChecksByProfile']['user']=15
  with self.assertRaises(ValueError):require_gates(s)
 def test_missing_release_asset(self):
  assets=[dict(name=Path(x['path']).name,size=x['bytes'],digest='sha256:'+x['sha256']) for x in self.s['assets']]+[dict(name=x['name'],size=x['bytes'],digest='sha256:'+x['sha256']) for x in self.s['installers']];r=dict(draft=False,assets=assets);release_assets_match(r,self.s);r['assets'].pop()
  with self.assertRaises(ValueError):release_assets_match(r,self.s)
 def test_transfer_tamper(self):
  with tempfile.TemporaryDirectory() as t:
   folder=Path(t);raw=b'synthetic';(folder/'user-package-000.b64').write_bytes(base64.b64encode(raw));p=dict(name='user-package-000.b64',bytes=len(raw),sha256=sha(raw));r=dict(profile='user',kind='package',parts=[p],transferBytes=len(raw),transferSha256=sha(raw));self.assertEqual(decode_parts(folder,r),raw);(folder/p['name']).write_bytes(base64.b64encode(b'changed'))
   with self.assertRaises(ValueError):decode_parts(folder,r)
if __name__=='__main__':unittest.main()

