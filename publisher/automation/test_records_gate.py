import unittest
from pathlib import Path
from records_gate import check_pair, require_pair

class RecordsGateTests(unittest.TestCase):
    def test_both_profiles(self):
        compiled=[]
        def compile_probe(*args): compiled.append(args); return 'probe.exe'
        result=check_pair('0.1.46',Path('work'),[],compile_probe,lambda *a:'RECORDS_LIVE_CHECKS=2','preflight')
        require_pair('0.1.46',result)
        self.assertEqual([str(x[1]) for x in compiled],['work/next-master','work/next-user'])
    def test_401_blocks(self):
        def failed(*args): raise RuntimeError('http_401')
        with self.assertRaises(RuntimeError):check_pair('0.1.46',Path('work'),[],lambda *a:'probe',failed,'signed')
    def test_incomplete_probe_blocks(self):
        with self.assertRaises(ValueError):check_pair('0.1.46',Path('work'),[],lambda *a:'probe',lambda *a:'','signed')
    def test_evidence_cannot_be_omitted_or_one_profile(self):
        for profiles in (None,[],['master'],['user'],['user','master']):
            with self.assertRaises(ValueError):require_pair('0.1.46',profiles)
    def test_old_immutable_history_unchanged(self):
        self.assertEqual(check_pair('0.1.45',None,None,None,None,'old'),[])
        require_pair('0.1.45',None)
if __name__=='__main__':unittest.main()
