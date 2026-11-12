import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import subprocess
spec=importlib.util.spec_from_file_location('preserve',Path(__file__).with_name('preserve-preflight.py'))
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class PreserveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for name,data in [('publisher/requests/v0.1.999.json',{}),('releases/v0.1.999/PREFLIGHT.json',{}),('publisher/current-request.json',{'state':'idle'}),('updates/stable-longterm.signed.json',{})]:
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data))
        self.original=(self.root/'publisher/current-request.json').read_bytes()
    def invoke(self,gate_error=None,activation_error=None):
        with patch.object(module,'ROOT',self.root), patch.object(module.candidate,'load_spec',return_value={'version':'0.1.999'}), patch.object(module.candidate,'signature',return_value=(None,{},None)), patch.object(module.candidate,'activation',side_effect=activation_error) as activation, patch.object(module.subprocess,'run',side_effect=gate_error) as guard, patch.object(module.candidate,'commit') as commit:
            if gate_error or activation_error:
                with self.assertRaises(Exception): module.preserve('publisher/candidates/v0.1.999.json')
                commit.assert_not_called()
            else:
                module.preserve('publisher/candidates/v0.1.999.json')
                activation.assert_called_once();guard.assert_called_once()
                self.assertEqual(commit.call_args.args[0],['publisher/requests/v0.1.999.json','releases/v0.1.999/PREFLIGHT.json'])
            self.assertEqual((self.root/'publisher/current-request.json').read_bytes(),self.original)
    def test_saved_evidence_without_activation(self): self.invoke()
    def test_hold_blocks_checkpoint(self): self.invoke(gate_error=subprocess.CalledProcessError(1,'node'))
    def test_existing_candidate_gate_failure_blocks_checkpoint(self): self.invoke(activation_error=ValueError('invalid pair'))

if __name__=='__main__': unittest.main()
