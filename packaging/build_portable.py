"""Build a portable public payload; no installer compiler or system install."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--bundle', required=True)
    parser.add_argument('--public-source', required=True)
    args = parser.parse_args()
    steps = [
        ['prepare_payload.py', '--source', args.source, '--bundle', args.bundle,
         '--profile', 'public', '--public-source', args.public_source],
        ['clean_payload.py'],
        ['-m', 'PyInstaller', '--noconfirm', '--distpath', 'dist', '--workpath', 'work', 'OpticalDesignStudio.spec'],
        ['augment_native_runtime.py'], ['finalize_payload.py'],
        ['verify_frozen.py', 'dist/Optical Design Studio/Optical Design Studio.exe',
         'portable-1.0.4-verification', '--gpu', '--expect-empty-library'],
    ]
    for step in steps:
        print('Running ' + step[0], flush=True)
        subprocess.run([sys.executable, *step], cwd=ROOT, check=True)

if __name__ == '__main__':
    main()
