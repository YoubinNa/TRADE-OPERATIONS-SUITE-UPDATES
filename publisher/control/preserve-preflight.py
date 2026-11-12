"""Persist verified request/evidence for a later activate run; never activate here."""
import sys, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'publisher/automation'))
import candidate

def preserve(spec_path):
    s=candidate.load_spec(spec_path)
    request_path=f"publisher/requests/v{s['version']}.json"
    evidence_path=f"releases/v{s['version']}/PREFLIGHT.json"
    req=candidate.strict_json((ROOT/request_path).read_bytes())
    evidence=candidate.strict_json((ROOT/evidence_path).read_bytes())
    _,previous,_=candidate.signature((ROOT/'updates/stable-longterm.signed.json').read_bytes())
    current_path=ROOT/'publisher/current-request.json'
    before=current_path.read_bytes()
    current=candidate.strict_json(before)
    candidate.activation(s,req,evidence,previous,current)  # Existing immutable pair, signature and Windows evidence gates.
    subprocess.run(['node',str(ROOT/'publisher/control/execution-control-guard.cjs'),spec_path,'preflight'],cwd=ROOT,check=True)
    if current_path.read_bytes()!=before:
        raise RuntimeError('CURRENT_REQUEST_CHANGED')
    candidate.commit([request_path,evidence_path],f"publisher: preserve verified preflight for v{s['version']} without activation")

if __name__=='__main__':
    preserve(sys.argv[1])
