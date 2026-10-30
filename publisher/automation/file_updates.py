"""Deterministic signed file-update sidecars for an already verified full ZIP.

Reuse the ZIP's raw DEFLATE stream in gzip wrappers: no recompression, platform
or zlib-version dependency. The full ZIP remains the legacy/offline artifact.
"""
from pathlib import Path
import hashlib, json, struct, zipfile, gzip, re

def sha(data): return hashlib.sha256(data).hexdigest()

def build(package, output):
    package, output = Path(package), Path(output)
    raw = package.read_bytes()
    if len(raw) > 67108864: raise ValueError('Full package exceeds limit')
    with zipfile.ZipFile(package) as z:
        names = z.namelist()
        if len(names) != len(set(n.lower() for n in names)): raise ValueError('Duplicate ZIP path')
        manifest_raw = z.read('manifest.json')
        if len(manifest_raw) > 1048576: raise ValueError('Manifest too large')
        manifest_text = manifest_raw.decode('utf-8')
        m = json.loads(manifest_text)
        if m['profile'] not in ('master', 'user') or not re.fullmatch(r'\d+\.\d+\.\d+', m['appVersion']): raise ValueError('Identity')
        if not 3 <= len(m['files']) <= 3000: raise ValueError('Inventory size')
        expected = [f['path'] for f in m['files']]
        if len(expected) != len(set(x.lower() for x in expected)) or set(names) != set(expected) | {'manifest.json'}: raise ValueError('Inventory')
        output.mkdir(parents=True, exist_ok=True)
        objects, assets, total, expanded = [], {}, 0, 0
        for f in m['files']:
            info = z.getinfo(f['path'])
            if info.compress_type != zipfile.ZIP_DEFLATED or info.flag_bits & 1: raise ValueError('Expected unencrypted DEFLATE')
            data = z.read(info)
            if len(data) != f['size'] or sha(data) != f['sha256']: raise ValueError('Payload integrity')
            expanded += len(data)
            if expanded > 268435456: raise ValueError('Expanded size limit')
            start = info.header_offset
            if raw[start:start+4] != b'PK\x03\x04': raise ValueError('Local ZIP header')
            name_len, extra_len = struct.unpack_from('<HH', raw, start+26)
            start += 30 + name_len + extra_len
            compressed = b'\x1f\x8b\x08\x00\x00\x00\x00\x00\x00\xff' + raw[start:start+info.compress_size] + struct.pack('<II', info.CRC, info.file_size)
            if gzip.decompress(compressed) != data: raise ValueError('Gzip reconstruction')
            digest = sha(compressed)
            name = 'ecuss-file-' + digest + '.gz'
            target = output/name
            if target.exists() and target.read_bytes() != compressed: raise ValueError('Immutable file object conflict')
            target.write_bytes(compressed)
            obj = dict(path=f['path'], bytes=len(compressed), sha256=digest)
            objects.append(obj); assets[name] = dict(name=name, bytes=len(compressed), sha256=digest)
            total += len(compressed)
        if total > 67108864: raise ValueError('Download limit')
        index = (json.dumps(dict(schema=1, manifest=manifest_text, objects=objects), ensure_ascii=False, separators=(',', ':'))+'\n').encode('utf-8')
        if len(index) > 2097152: raise ValueError('Index size limit')
        name = f"TRADE_OPERATIONS_SUITE_{m['profile'].title()}_v{m['appVersion']}.files.json"
        target = output/name
        if target.exists() and target.read_bytes() != index: raise ValueError('Immutable index conflict')
        target.write_bytes(index)
        assets[name] = dict(name=name, bytes=len(index), sha256=sha(index))
        return dict(schema=1, bytes=len(index), sha256=sha(index)), sorted(assets.values(), key=lambda x:x['name'])

def estimate(index_path, current):
    index = json.loads(Path(index_path).read_bytes()); m = json.loads(index['manifest'])
    objects = {x['path']:x for x in index['objects']}; changed = []
    for f in m['files']:
        path = Path(current)/f['path']
        if not path.is_file() or path.stat().st_size != f['size'] or sha(path.read_bytes()) != f['sha256']: changed.append(f['path'])
    return dict(downloadBytes=Path(index_path).stat().st_size + sum(o['bytes'] for o in {objects[p]['sha256']:objects[p] for p in changed}.values()), changed=changed, reusedFiles=len(m['files'])-len(changed))

if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser(); p.add_argument('package',type=Path);p.add_argument('output',type=Path);p.add_argument('--current',type=Path)
    a=p.parse_args(); ref,assets=build(a.package,a.output)
    result=dict(fileUpdate=ref,assets=assets)
    if a.current:
        index=next(x for x in assets if x['name'].endswith('.files.json'))
        result['estimate']=estimate(a.output/index['name'],a.current)
    print(json.dumps(result,ensure_ascii=False,indent=2))
