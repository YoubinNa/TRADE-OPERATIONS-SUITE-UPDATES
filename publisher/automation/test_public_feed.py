import unittest
from public_feed import verify_public_feed

class PublicFeedTests(unittest.TestCase):
    def check(self, replies):
        calls=[]; pauses=[]; verified=[]
        def fetch(url):
            calls.append(url)
            result=replies.pop(0)
            if isinstance(result,Exception):raise result
            return result
        result=verify_public_feed('owner/repo','updates/feed.json','a'*40,b'expected',verified.append,fetch,pauses.append)
        return result,calls,pauses,verified

    def test_current_channel_still_required(self):
        with self.assertRaises(ValueError):self.check([b'expected']+[b'old']*4)

    def test_immutable_mismatch_rejected(self):
        with self.assertRaises(ValueError):self.check([b'wrong'])

    def test_no_sleep_on_success(self):
        result,calls,pauses,verified=self.check([b'expected',b'expected'])
        self.assertEqual(result['attempts'],1);self.assertEqual(pauses,[])
        self.assertEqual(verified,[b'expected',b'expected'])
        self.assertIn('/'+'a'*40+'/',calls[0]);self.assertIn('/main/',calls[1])

    def test_stale_cache_gets_new_key_and_short_retry(self):
        result,calls,pauses,_=self.check([b'expected',b'old',b'expected'])
        self.assertEqual(result['attempts'],2);self.assertEqual(pauses,[2])
        self.assertNotEqual(calls[1],calls[2])

    def test_network_timeout_retries(self):
        result,_,pauses,_=self.check([b'expected',TimeoutError(),b'expected'])
        self.assertEqual(result['attempts'],2);self.assertEqual(pauses,[2])

    def test_signature_failure_never_accepted(self):
        def reject(_):raise ValueError('Bad signature')
        with self.assertRaises(ValueError):verify_public_feed('o/r','f','a'*40,b'expected',reject,lambda _:b'expected')

if __name__=='__main__':unittest.main()
