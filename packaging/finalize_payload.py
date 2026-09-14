"""Add shareable source, dependency notices and inventory to the frozen folder."""
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import re
import shutil
import sys

from build_version import release_info

ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT/'dist'/'Optical Design Studio'
SOURCE = ROOT/'build_input'/'source'

def copy_tree(source, destination):
    """Copy contents without carrying Conda cache read-only directory flags."""
    source, destination = Path(source), Path(destination)
    for directory, folders, files in os.walk(source, followlinks=False):
        directory = Path(directory)
        folders[:] = [name for name in folders if name not in {'__pycache__', '.git'}
                      and not (directory/name).is_symlink()]
        target = destination/directory.relative_to(source)
        target.mkdir(parents=True, exist_ok=True)
        for name in files:
            path = directory/name
            if not path.is_symlink() and path.suffix != '.pyc':
                shutil.copyfile(path, target/name)

def main():
    if not (PAYLOAD/'Optical Design Studio.exe').is_file():
        raise FileNotFoundError('Build the PyInstaller payload first.')
    release = release_info(SOURCE)
    copy_tree(SOURCE, PAYLOAD/'_internal'/'source')
    shutil.copy2(ROOT/'build_input'/'S4_Studio.ico', PAYLOAD/'S4_Studio.ico')
    shutil.copy2(ROOT/'INSTALLATION.md', PAYLOAD/'INSTALLATION.md')
    rebuild = PAYLOAD/'_internal'/'source'/'packaging'
    rebuild.mkdir(exist_ok=True)
    for path in ROOT.iterdir():
        if path.is_file() and path.suffix in {'.py', '.ps1', '.spec', '.iss', '.md', '.txt'}:
            shutil.copy2(path, rebuild/path.name)
    copy_tree(ROOT/'assets', rebuild/'assets')
    shutil.copyfile(ROOT/'installation-template.json', rebuild/'installation-template.json')
    licenses = PAYLOAD/'THIRD_PARTY_LICENSES'
    licenses.mkdir(exist_ok=True)
    copy_tree(SOURCE/'third-party-licenses', licenses/'S4-and-native-build')
    copy_tree(ROOT/'build_input'/'gpu_licenses', licenses/'NVIDIA')
    distributions = {}
    paths = [str(Path(sys.prefix)/'Lib'/'site-packages'), str(SOURCE/'ml_dependencies')]
    for dist in metadata.distributions(path=paths):
        name = dist.metadata.get('Name', 'unknown')
        if name in distributions:
            continue
        distributions[name] = {'version': dist.version, 'license': dist.metadata.get('License-Expression') or dist.metadata.get('License', ''),
                               'home_page': dist.metadata.get('Home-page', ''), 'project_urls': dist.metadata.get_all('Project-URL') or []}
        dest = licenses/re.sub(r'[^A-Za-z0-9_.-]', '_', name)
        dest.mkdir(exist_ok=True)
        (dest/'PACKAGE-METADATA.txt').write_text(dist.read_text('METADATA') or dist.read_text('PKG-INFO') or name, encoding='utf-8')
        for entry in dist.files or []:
            if not any(part.lower().startswith(('license', 'licence', 'copying', 'notice')) for part in entry.parts):
                continue
            file = Path(dist.locate_file(entry))
            if file.is_file():
                target = dest/str(entry).replace('..', '_').replace('/', '__').replace('\\', '__')
                shutil.copy2(file, target)
    conda_packages = Path(sys.prefix).parent.parent/'pkgs'
    for record_path in (Path(sys.prefix)/'conda-meta').glob('*.json'):
        record = json.loads(record_path.read_text(encoding='utf-8'))
        name = f"{record['name']}-{record['version']}-{record['build']}"
        path = conda_packages/name/'info'/'licenses'
        if path.is_dir():
            copy_tree(path, licenses/name)
    for pattern in ('mkl-2023.1.0-*', 'intel-openmp-2023.1.0-*', 'python-3.12.*', 'libffi-*', 'vc14_runtime-*', 'vs2015_runtime-*'):
        for package in conda_packages.glob(pattern):
            path = package/'info'/'licenses'
            if path.is_dir():
                copy_tree(path, licenses/package.name)
    (licenses/'DEPENDENCIES.json').write_text(json.dumps(distributions, indent=2), encoding='utf-8')
    (licenses/'README.txt').write_text(
        'Optical Design Studio bundles third-party software under its respective licenses.\n'
        'The Python application and S4 native source are in _internal/source.\n'
        'Package metadata here records upstream project/source URLs and versions.\n'
        'PyQt6 is the GPLv3 distribution; Qt and all other components retain their own terms.\n'
        'GPU libraries are NVIDIA redistributables; the NVIDIA display driver is not included.\n'
        'This folder includes notices from the build environment; some packages are build tools only.\n', encoding='utf-8')
    inventory = {}
    files = sorted(path for path in PAYLOAD.rglob('*') if path.is_file() and path.name != 'PAYLOAD-MANIFEST.json')
    print(f'Hashing {len(files)} packaged files...', flush=True)
    for number, file in enumerate(files, 1):
        if file.is_file() and file.name != 'PAYLOAD-MANIFEST.json':
            digest = hashlib.sha256()
            with file.open('rb') as stream:
                for chunk in iter(lambda: stream.read(4*1024**2), b''):
                    digest.update(chunk)
            inventory[file.relative_to(PAYLOAD).as_posix()] = {'size': file.stat().st_size, 'sha256': digest.hexdigest()}
        if number % 1000 == 0:
            print(f'Verified {number}/{len(files)} files', flush=True)
    summary = {**release, 'architecture': 'Windows x64',
               'updates': {'repository': 'Wgeshow/optical-design-studio-updates',
                           'private': True, 'authenticated_check': True,
                           'authenticated_download': True, 'automatic_check': False,
                           'automatic_install': False, 'release_channel': 'stable'},
               'build_input': json.loads((ROOT/'build_input'/'build_input.json').read_text()),
               'files': inventory}
    (PAYLOAD/'PAYLOAD-MANIFEST.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps({'payload': str(PAYLOAD), 'files': len(inventory), 'bytes': sum(v['size'] for v in inventory.values())}, indent=2))

if __name__ == '__main__':
    main()
