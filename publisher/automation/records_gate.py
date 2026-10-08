"""Fail closed on invalid records credentials in new public distribution bytes."""

def required(version):
    # Historical immutable reviews stay historical; all following updates need
    # fresh public-time checks, not a copied private-build result.
    return tuple(map(int, version.split('.'))) >= (0, 1, 46)

def check_pair(version, work, cc, compile_probe, run, phase):
    if not required(version):
        return []
    passed = []
    for profile in ('master', 'user'):
        folder = work / ('records-' + phase + '-' + profile)
        exe = compile_probe(cc, work / ('next-' + profile), folder, 'RecordsConnectionProbe.cs')
        result = run(exe, folder / 'settings')
        if 'RECORDS_LIVE_CHECKS=2' not in result:
            raise ValueError('Public packaged records connection gate incomplete')
        passed.append(profile)
    return passed

def require_pair(version, profiles):
    if required(version) and profiles != ['master', 'user']:
        raise ValueError('Both live public records connection checks are required')
