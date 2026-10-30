import copy,gzip,hashlib,json,tempfile,unittest,zipfile
from pathlib import Path
from file_updates import build,estimate,sha
from paired_candidate import validate_file_updates,sidecar_assets,asset_hashes,package_catalog,release_assets_match
from paired_pipeline import require_gates
from verify import catalog_identity,REPO
class FileUpdates(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);self.old=self.root/'old';self.old.mkdir()
  self.payload={'ui/large.bin':b'OCR fixture'*200000,'ui/home.html':b'new home','ui/add.txt':b'added'}
  (self.old/'ui').mkdir();(self.old/'ui/large.bin').write_bytes(self.payload['ui/large.bin']);(self.old/'ui/home.html').write_bytes(b'old home');(self.old/'ui/removed.txt').write_bytes(b'old only')
  self.m=dict(appVersion='0.1.101',profile='master',files=[dict(path=p,size=len(v),sha256=sha(v)) for p,v in self.payload.items()])
  self.zip=self.root/'full.zip';self.write_zip();self.ref,self.assets=build(self.zip,self.root/'assets')
  self.p=dict(profile='master',path='packages/v0.1.101/TRADE_OPERATIONS_SUITE_Master_v0.1.101.ecuss-update.zip',releaseId='desktop-0.1.101-master-test',bytes=self.zip.stat().st_size,sha256=sha(self.zip.read_bytes()),fileUpdate=self.ref,fileUpdateAssets=self.assets)
 def write_zip(self):
  with zipfile.ZipFile(self.zip,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
   z.writestr('manifest.json',json.dumps(self.m));
   for name,data in self.payload.items():z.writestr(name,data)
 def spec(self):
  user=copy.deepcopy(self.p);user['profile']='user';user['path']=user['path'].replace('Master','User');user['releaseId']=user['releaseId'].replace('master','user')
  index=next(x for x in user['fileUpdateAssets'] if x['name'].endswith('.json'));index['name']=index['name'].replace('Master','User')
  return dict(version='0.1.101',assets=[self.p,user],installers=[])
 def test_reconstruct_all_gzip(self):
  index=json.loads(next((self.root/'assets').glob('*.json')).read_bytes())
  for o in index['objects']:
   raw=(self.root/'assets'/('ecuss-file-'+o['sha256']+'.gz')).read_bytes();self.assertEqual(gzip.decompress(raw),self.payload[o['path']]);self.assertEqual(len(raw),o['bytes'])
 def test_deterministic_without_recompression(self):self.assertEqual(build(self.zip,self.root/'again'),(self.ref,self.assets))
 def test_exact_manifest(self):self.assertEqual(json.loads(next((self.root/'assets').glob('*.json')).read_bytes())['manifest'],json.dumps(self.m))
 def test_only_changed_and_added(self):
  e=estimate(next((self.root/'assets').glob('*.json')),self.old);self.assertEqual(e['changed'],['ui/home.html','ui/add.txt']);self.assertEqual(e['reusedFiles'],1)
 def test_repair_corrupt_existing(self):
  (self.old/'ui/large.bin').write_bytes(b'corrupted');self.assertEqual(estimate(next((self.root/'assets').glob('*.json')),self.old)['reusedFiles'],0)
 def test_immutable_object(self):
  next((self.root/'assets').glob('*.gz')).write_bytes(b'changed')
  with self.assertRaises(ValueError):build(self.zip,self.root/'assets')
 def test_payload_hash(self):
  self.m['files'][0]['sha256']='a'*64;self.write_zip()
  with self.assertRaises(ValueError):build(self.zip,self.root/'bad')
 def test_extra_zip_file(self):
  with zipfile.ZipFile(self.zip,'a') as z:z.writestr('extra.txt','unlisted')
  with self.assertRaises(ValueError):build(self.zip,self.root/'bad')
 def test_index_reference_validation(self):
  s=self.spec();validate_file_updates(s);s['assets'][0]['fileUpdate']['bytes']=2097153
  with self.assertRaises(ValueError):validate_file_updates(s)
 def test_both_profiles_required(self):
  s=self.spec();s['assets'][1].pop('fileUpdate')
  with self.assertRaises(ValueError):validate_file_updates(s)
 def test_future_missing_rejected(self):
  s=self.spec()
  for p in s['assets']:p.pop('fileUpdate');p.pop('fileUpdateAssets')
  with self.assertRaises(ValueError):validate_file_updates(s)
 def test_sidecar_path_rejected(self):
  s=self.spec();s['assets'][0]['fileUpdateAssets'][0]['name']='../outside'
  with self.assertRaises(ValueError):validate_file_updates(s)
 def test_all_assets_bound_to_approval(self):
  s=self.spec();self.assertEqual(len(asset_hashes(s)),len(sidecar_assets(s))+2)
 def test_catalog_only_binds_descriptor(self):
  s=self.spec();packages=package_catalog(s,'a'*40);self.assertNotIn('fileUpdateAssets',packages[0]);self.assertEqual(packages[0]['fileUpdate'],self.ref)
  catalog_identity(dict(profiles=['master','user'],appVersion='0.1.101',packages=packages))
 def test_missing_release_object(self):
  s=self.spec();allassets=[dict(name=Path(p['path']).name,size=p['bytes'],digest='sha256:'+p['sha256']) for p in s['assets']]+[dict(name=a['name'],size=a['bytes'],digest='sha256:'+a['sha256']) for a in sidecar_assets(s).values()]
  release_assets_match(dict(draft=False,assets=allassets),s)
  with self.assertRaises(ValueError):release_assets_match(dict(draft=False,assets=allassets[:-1]),s)
 def test_signed_application_gates_mandatory(self):
  state=dict(oldProfiles=['master','user'],windowsChecksByProfile=dict(master=36,user=36),windowsChecks=72,pairedModulesIdentical=True,fileUpdates=True)
  with self.assertRaises(ValueError):require_gates(state)
  state['fileUpdateChecks']=28;require_gates(state)
if __name__=='__main__':unittest.main()
