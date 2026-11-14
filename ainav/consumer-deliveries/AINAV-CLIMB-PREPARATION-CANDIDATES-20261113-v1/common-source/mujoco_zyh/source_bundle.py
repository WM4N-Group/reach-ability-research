"""Fetch/verify the exact published zyh MuJoCo package, including LFS payloads.

No installation, simulator import, actor load or physics. The downloaded bundle
is external to Git and never edited by the collector. Updates require new pins.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path, PurePosixPath
import urllib.request

REPOSITORY = 'WM4N-Group/go2-piper-RL-Sim2Sim2Real'
COMMIT = '340d7d8b0fffbf3c566e503a919c8a92393c5cbe'
SUMS_SHA256 = 'aa97f14736885648f99853385c145de30a34b753903d9a51a872f7d407653150'
MANIFEST_SHA256 = 'b7669886794092acb6ed17a2f6428b1bf4a9e218de601c860207d6c367ed09be'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(ok, message):
    if not ok:
        raise ValueError(message)


def parse_checksums(text):
    result = {}
    for line in text.splitlines():
        if not line.strip():
            continue
        sha, name = line.split(maxsplit=1)
        name = name.lstrip('*')
        p = PurePosixPath(name)
        require(not p.is_absolute() and '..' not in p.parts and str(p) == name and '\\' not in name,
            'Unsafe source path: ' + name)
        require(len(sha) == 64 and all(c in '0123456789abcdef' for c in sha) and name not in result,
            'Invalid/duplicate source checksum: ' + name)
        result[name] = sha
    require(bool(result), 'Empty source manifest')
    return result


def fetch_bytes(name, *, lfs=False):
    domain = 'media.githubusercontent.com/media' if lfs else 'raw.githubusercontent.com'
    url = f'https://{domain}/{REPOSITORY}/{COMMIT}/mujoco/{name}'
    request = urllib.request.Request(url, headers={'User-Agent': 'Piper-WM-pinned-source-fetch'})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read()
    if not lfs and data.startswith(b'version https://git-lfs.github.com/spec/v1\n'):
        return fetch_bytes(name, lfs=True)
    return data


def verify_bundle(root):
    root = Path(root).resolve(strict=True)
    data = (root / 'SHA256SUMS').read_bytes()
    require(digest(data) == SUMS_SHA256, 'Published checksum manifest changed')
    require(digest((root / 'MANIFEST.json').read_bytes()) == MANIFEST_SHA256, 'Published manifest changed')
    checksums = parse_checksums(data.decode())
    for name, expected in checksums.items():
        path = root / name
        require(path.resolve().is_relative_to(root), 'Source path escapes bundle')
        require(path.is_file() and not path.is_symlink() and digest(path.read_bytes()) == expected,
            'Frozen zyh source/policy/asset mismatch: ' + name)
    actual = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()
        and '__pycache__' not in p.parts}
    require(actual == set(checksums) | {'SHA256SUMS'}, 'Unexpected/unfrozen file in source bundle')
    return dict(schema='pinned-zyh-mujoco-source-v1', repository=REPOSITORY, commit=COMMIT,
        sha256sums_sha256=SUMS_SHA256, manifest_sha256=MANIFEST_SHA256,
        verified_files=len(checksums), root=str(root), skills=dict(nav='original210D', climb='V1/900', push='v212-dual'),
        original_source_or_weights_modified=False, formal_skill_acceptance=False)


def download_bundle(root, *, complete_partial=False):
    root = Path(root)
    require(not root.exists() or complete_partial, 'Never overwrite an existing source bundle')
    data = fetch_bytes('SHA256SUMS')
    require(digest(data) == SUMS_SHA256, 'Remote source manifest is not pinned version')
    checksums = parse_checksums(data.decode())
    root.mkdir(parents=True, exist_ok=complete_partial)
    if (root / 'SHA256SUMS').exists():
        require((root / 'SHA256SUMS').read_bytes() == data, 'Partial bundle manifest differs')
    else:
        (root / 'SHA256SUMS').write_bytes(data)
    def fetch(item):
        name, expected = item
        if (root / name).exists():
            require(digest((root / name).read_bytes()) == expected, 'Existing partial file is corrupt: ' + name)
            return
        content = fetch_bytes(name)
        require(digest(content) == expected, 'Remote source/LFS hash mismatch: ' + name)
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as out:
            out.write(content)
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(fetch, checksums.items()))
    return verify_bundle(root)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bundle', type=Path, required=True)
    p.add_argument('--download', action='store_true')
    p.add_argument('--complete-partial', action='store_true', help='Fill missing files only, never overwrite existing bytes')
    a = p.parse_args()
    result = download_bundle(a.bundle, complete_partial=a.complete_partial) if a.download else verify_bundle(a.bundle)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
