"""Regression gates using public seq-10/11 signatures and synthetic mutations."""
import base64, copy, json, shutil, tempfile, unittest
from pathlib import Path
from verify import archive, ready, signature, strict_json
ROOT=Path(__file__).resolve().parents[2]
H='7b3d64f24f4f838b4684b5b2ada443e1b43ab3976a2e59150087d268ca748e10'
INBOX=f'publisher/inbox/seq-11-{H}.signed.json'
PREV='publisher/inbox/seq-10-3a9e22a355482fa1f065734697e882f54b06f6efef40bda39f16a3e5dcafdc6d.signed.json'
class Gates(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.put('publisher/current-request.json',(ROOT/'publisher/requests/v0.1.26.json').read_bytes())
        self.put(INBOX,(ROOT/INBOX).read_bytes());self.put('updates/stable-longterm.signed.json',(ROOT/PREV).read_bytes())
        self.put('publisher/plans/seq-11.json',(ROOT/'publisher/plans/seq-11.json').read_bytes())
    def tearDown(self):self.temp.cleanup()
    def put(self,p,b):
        q=self.root/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
    def change(self,p,fn):
        d=json.loads((self.root/p).read_bytes());fn(d);self.put(p,json.dumps(d).encode())
    def test_valid(self):self.assertEqual(ready(self.root)['payload']['catalog']['appVersion'],'0.1.26')
    def test_idle(self):
        self.change('publisher/current-request.json',lambda d:d.update(state='idle'));self.assertIsNone(ready(self.root))
    def test_unsigned_wait(self):
        (self.root/INBOX).unlink();self.assertIsNone(ready(self.root))
    def test_signature_tamper(self):
        self.change(INBOX,lambda d:d.update(signature=base64.b64encode(b'\x00'*384).decode()))
        with self.assertRaises(ValueError):ready(self.root)
    def test_payload_tamper(self):
        self.change(INBOX,lambda d:d.update(payload=base64.b64encode(b'{}').decode()))
        with self.assertRaises(ValueError):ready(self.root)
    def test_untrusted_key(self):
        self.change(INBOX,lambda d:d.update(keyId='0'*64))
        with self.assertRaises(ValueError):ready(self.root)
    def test_different_request(self):
        self.change('publisher/current-request.json',lambda d:d.update(payloadSha256='0'*64))
        with self.assertRaises(ValueError):ready(self.root)
    def test_disabled_plan(self):
        self.change('publisher/plans/seq-11.json',lambda d:d.update(enabled=False))
        with self.assertRaises(ValueError):ready(self.root)
    def test_missing_review(self):
        self.change('publisher/plans/seq-11.json',lambda d:d.update(publicContentReviewed=False))
        with self.assertRaises(ValueError):ready(self.root)
    def test_wrong_transition(self):
        self.change('publisher/plans/seq-11.json',lambda d:d.update(requiredActiveVersion='0.1.26'))
        with self.assertRaises(ValueError):ready(self.root)
    def test_resume_after_feed_commit(self):
        self.put('updates/stable-longterm.signed.json',(self.root/INBOX).read_bytes())
        self.put('publisher/publications/seq-11/previous.signed.json',(ROOT/PREV).read_bytes())
        self.assertTrue(ready(self.root)['resumed'])
    def test_same_sequence_conflict(self):
        raw=(self.root/INBOX).read_bytes();self.put('updates/stable-longterm.signed.json',raw+b' ')
        with self.assertRaises(ValueError):ready(self.root)
    def test_duplicate_json_key(self):
        with self.assertRaises(ValueError):strict_json('{"schema":1,"schema":2}')
    def test_archive_hash_tamper(self):
        r=ready(self.root);p=r['payload']['catalog']['packages'][0]
        altered=self.root/'altered.zip';raw=(ROOT/p['path']).read_bytes();altered.write_bytes(bytes([raw[0]^1])+raw[1:])
        with self.assertRaises(ValueError):archive(altered,p)
    def test_archive_inventory(self):
        p=ready(self.root)['payload']['catalog']['packages'][0]
        self.assertEqual(archive(ROOT/p['path'],p)['appVersion'],'0.1.26')
if __name__=='__main__':unittest.main()
