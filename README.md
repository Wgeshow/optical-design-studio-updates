# Optical Design Studio

Private source and release repository for Optical Design Studio **1.0.2**.
The application provides a shared multilayer structure editor, wavelength-dependent
materials, S4 spectra and electric fields, constrained design searches, and saved work.
The native PyQt6 interface supports dark and light appearances.

## Install or update

Approved repository users can download the Windows x64 installer from the repository’s
**Releases** page. The release provides its SHA-256 checksum and a matching source archive.
Run the installer to choose an installation directory. Native runtime dependencies are
included in the installer; compatible NVIDIA hardware and its driver are required for GPU use.

Version 1.0.2 adds **About** with the installed version, recorded update date, and update
status. **Check for updates** accesses this private repository only when requested.
**Download update** appears for a newer compatible stable release and saves a package
only after verifying its SHA-256 digest. It opens the containing folder on request;
it does not run the installer or replace a running application automatically.
Versions before 1.0.2 require an installer upgrade before these controls are available.

Use your own GitHub token with repository read access. The repository owner can select
this repository in a fine-grained token with **Contents: Read-only**. Invited collaborators
must follow [GitHub’s current token limitations](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).
The application keeps access in memory unless **Remember on this computer** is selected;
supported OS credential storage is used for remembering. It never writes tokens into
project exports or library bundles. No shared access token belongs in this repository.
Removing account access prevents future private downloads; it does not deactivate an
existing offline installation.

Installed user data is separate from application files, normally at
`%LOCALAPPDATA%/Optical Design Studio/User Data` on Windows. Keep a backup of valuable
work before changing versions. The updater does not upload projects, materials, or results.

## Source layout

- `src/`: application modules, launchers, requirements, and usage guides.
- `src/tests/`: Python test source; tests generate their own temporary inputs.
- `src/pcs_s4_runtime/`: Python runtime and multiprocessing glue.
- `src/S4-source/`: native S4 C/C++ code, build tools, upstream examples/documentation,
  and embedded dependency headers with their notices.
- `src/third-party-licenses/`: supplied third-party notices.
- `packaging/`: Windows PyInstaller and Inno Setup recipes plus original icon assets.

This source tree excludes native Python extensions, DLLs, executables, Python dependency
payloads, access credentials, installation receipts, optical-constant datasets, saved
projects/results, and local build logs. Those are not required in Git history. Original
license and copyright notices remain beside their source. No new blanket license has
been assigned to third-party code.

## Run from source

Use **Python 3.12** and a native S4 build matching the operating system, architecture,
Python ABI, and BLAS/LAPACK runtime. Installing the Python requirements alone does not
build or supply that native extension. Launch with `python src/qt_app.py` after completing
the relevant native setup. The legacy browser interface remains available through the
`launch_web_gui` scripts.

### Windows x64

The tested installer environment uses NumPy 1.26.4 and MKL 2023.1. Create or activate an
appropriate environment, for example with the supplied `src/environment.yml`, then install
the desktop requirements. Optional ML packages can be installed into the separate source
dependency directory so the existing NumPy/MKL pair is retained:

```powershell
conda env create -f src/environment.yml
conda activate s4_updated
python -m pip install -r src/requirements-desktop.txt
python -m pip install --target src/ml_dependencies --no-deps -r src/requirements-ml.txt
```

Build the native extension using the supplied LLVM-MinGW helper. Supply an installed
64-bit LLVM-MinGW compiler and the matching LP64 MKL/OpenBLAS library; these tools and
binaries are not in this source repository:

```powershell
python src/S4-source/tools/build_windows.py --compiler 'C:\path\to\llvm-mingw\bin\clang.exe' --blas 'C:\path\to\mkl_rt.2.dll' --output src/pcs_s4_runtime
python src/qt_app.py
```

The BLAS DLL and required runtime DLLs must be discoverable by the application. A Conda
environment’s `Library/bin` is configured automatically. Optional GPU support requires a
compatible CUDA toolkit at build time; see `src/S4-source/OPTIMIZATION_NOTES.md` and the
helper’s `--cuda-include` argument. Verify CPU operation before enabling GPU workloads.

### Linux

Install Python 3.12 development headers, a C/C++ toolchain, CMake, and OpenBLAS development
libraries using your distribution’s package manager. Then run:

```bash
cd src
bash setup_linux.sh
bash launch_qt_gui.sh
```

The setup creates `.venv`, installs `requirements-linux.txt`, and builds the matching S4
extension with CMake. `bash setup_linux.sh --cuda` additionally requires a compatible CUDA
toolkit. Windows DLLs and the Windows installer do not run natively on Linux. Linux-native
execution and a Linux update package require separate validation; this Windows release
does not claim to provide a tested Linux installer.

## Tests and installer rebuilds

Run focused native UI and updater tests without repository credentials or real network calls:

```powershell
cd src
python -m unittest discover -s tests -p test_update_client.py -v
python -m unittest discover -s tests -p test_update_credentials.py -v
python -m unittest discover -s tests -p test_qt_about.py -v
```

Solver/integration tests need the native S4 runtime and the appropriate numerical packages.
See [`packaging/BUILDING.md`](packaging/BUILDING.md) for the release build and verification.
The current Windows packager requires an explicitly supplied application library/source
bundle containing native and ML dependencies, official NVIDIA redistributable wheels,
PyInstaller, and Inno Setup. A source checkout alone is not a complete installer payload.
Only use data approved for distribution in that bundle. Preserve the Inno application ID
so upgrades continue to use the existing installation.

## Stable and experimental work

Use **`main`** for reviewed stable source and **`test`** for experimental changes.
Open a pull request from `test` to `main`, review the diff, and run appropriate checks before
merging. This repository does not automatically publish or install updates from either branch.
Do not publish experimental builds as stable releases.

For a stable release, update `APP_VERSION` and `BUILD_DATE` in `src/app_version.py`, build
and verify the application/installer, then create a version tag such as `v1.0.2` from the
reviewed stable commit. Attach:

- `OpticalDesignStudio-Setup-1.0.2-Windows-x64.exe`
- Its `.sha256` checksum file.
- The matching source archive.

Use a draft while assembling a release. Publish only after validation and review. The app
ignores drafts and prereleases, compares numeric versions, and requires a compatible
asset with an available SHA-256 digest. Windows package names must use the exact pattern
`OpticalDesignStudio-Setup-<version>-Windows-x64.exe`. Future Linux packages require their
own build and validation. Do not upload access tokens, OS credential-store data, signing
keys, installation receipts, or unapproved research data with a release.
