"""Anonymous exact-byte publication checks with bounded, observable propagation waits."""
import time
import urllib.request
from urllib.error import HTTPError, URLError
from verify import require, sha

def read(url):
    request = urllib.request.Request(url, headers={'Cache-Control': 'no-cache', 'User-Agent': 'Suite-Publication-Check'})
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.read(1048577)

def verify_public_feed(repo, path, commit, expected, verify_signature, fetch=read, pause=time.sleep):
    started = time.monotonic()
    base = f'https://raw.githubusercontent.com/{repo}'
    # The immutable commit proves origin availability, but never substitutes for the moving channel.
    fixed = fetch(f'{base}/{commit}/{path}')
    require(fixed == expected, 'Immutable public feed differs from approved signature')
    verify_signature(fixed)
    digest = sha(expected)
    for attempt in range(4):
        try:
            actual = fetch(f'{base}/main/{path}?publication={digest}&attempt={attempt}')
            if actual == expected:
                verify_signature(actual)
                return dict(immutableCommit=True, movingChannel=True, anonymous=True,
                            attempts=attempt+1, elapsedSeconds=round(time.monotonic()-started, 3))
            print(f'Public channel still propagating, attempt {attempt+1}/4', flush=True)
        except (HTTPError, URLError, TimeoutError) as error:
            print(f'Public channel temporarily unavailable: {type(error).__name__}', flush=True)
        if attempt < 3:
            pause(2)
    raise ValueError('Public channel not confirmed; retry completion with the same signature')
