import base64
import copy
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from candidate import activation, validate_spec, decode_transfer, check_slot, check_predecessor
from verify import sha

def fixture():
    p=dict(profile='master',path='packages/v0.1.30/TRADE_OPERATIONS_SUITE_Master_v0.1.30.ecuss-update.zip',releaseId='test',bytes=10,sha256='a'*64)
    s=dict(schema=1,version='0.1.30',sequence=13,requiredActiveVersion='0.1.27',publicContentReviewed=True,windowsCandidateVerified=True,candidateVerificationRuns=[123],assets=[p],notes=['Approved changes'],approval=dict(explicit=True,scope='master-release',approvedAt='2026-10-03T09:38:38+09:00',version='0.1.30',sequence=13,packageSha256=p['sha256']))
    payload=dict(sequence=13,catalog=dict(appVersion='0.1.30',packages=[dict(p,commit='b'*40)]))
    raw=json.dumps(payload).encode()
    request=dict(state='ready',payload=base64.b64encode(raw).decode(),payloadSha256=sha(raw))
    evidence=dict(version='0.1.30',sequence=13,packageCommit='b'*40,packageSha256=p['sha256'],payloadSha256=sha(raw),windowsPublicDownloadChecks=14,helperRequestChecks=7,publicationGateCompiledAgainstActualOldAndNew=True)
    previous=dict(sequence=12,catalog=dict(appVersion='0.1.27'))
    return s,request,evidence,previous,dict(state='idle')

class CandidateTests(unittest.TestCase):
    def test_approved_checked_request_activates(self):
        data=fixture();plan=activation(*data)
        self.assertEqual(plan['payloadSha256'],data[1]['payloadSha256']);self.assertTrue(plan['enabled'])
    def test_no_explicit_approval_rejected(self):
        d=fixture();d[0]['approval']['explicit']=False
        with self.assertRaises(ValueError):activation(*d)
    def test_approval_cannot_be_reused_for_other_bytes(self):
        d=fixture();d[0]['approval']['packageSha256']='c'*64
        with self.assertRaises(ValueError):activation(*d)
    def test_unreviewed_candidate_rejected(self):
        d=fixture();d[0]['publicContentReviewed']=False
        with self.assertRaises(ValueError):activation(*d)
    def test_predecessor_changed_rejected(self):
        d=fixture();d[3]['catalog']['appVersion']='0.1.28'
        with self.assertRaises(ValueError):activation(*d)
    def test_request_content_changed_rejected(self):
        d=fixture();d[1]['payload']=base64.b64encode(b'{}').decode()
        with self.assertRaises(ValueError):activation(*d)
    def test_windows_failure_prevents_request(self):
        d=fixture();d[2]['helperRequestChecks']=6
        with self.assertRaises(ValueError):activation(*d)
    def test_other_pending_request_not_overwritten(self):
        d=fixture();d[4]['state']='ready'
        with self.assertRaises(ValueError):activation(*d)
    def test_same_request_retry_is_allowed(self):
        d=list(fixture());d[4]=copy.deepcopy(d[1]);activation(*d)
    def test_completed_version_cannot_be_requested_again(self):
        d=fixture();d[3]['catalog']['appVersion']='0.1.30';d[3]['sequence']=13
        with self.assertRaises(ValueError):activation(*d)
    def test_evidence_for_other_package_rejected(self):
        d=fixture();d[2]['packageCommit']='c'*40
        with self.assertRaises(ValueError):activation(*d)
    def test_legacy_mode_requires_specific_approval(self):
        d=fixture();d[0]['updateMode']='legacy-import-once'
        with self.assertRaises(ValueError):activation(*d)
    def test_fragment_corruption_rejected_before_zip_write(self):
        s=fixture()[0]
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);folder=root/'releases/v0.1.30/transfer';folder.mkdir(parents=True)
            (folder/'master-000.b64').write_bytes(base64.b64encode(b'corrupt'))
            (folder/'index.json').write_text(json.dumps(dict(packageSha256=s['assets'][0]['sha256'],bytes=10,parts=[dict(name='master-000.b64',bytes=10,sha256='a'*64)])))
            with self.assertRaises(ValueError):decode_transfer(root,s)
            self.assertFalse((root/s['assets'][0]['path']).exists())

if __name__=='__main__':unittest.main()
