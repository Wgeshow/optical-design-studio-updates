# Optical Design Studio

Private development repository for Optical Design Studio **1.0.3**. Use `test`
for experiments and reviewed pull requests into `main` for stable source.
The application provides shared multilayer structures, wavelength-dependent
materials, S4 spectra and electric fields, constrained design searches, and
saved work in a native PyQt6 interface with dark and light appearances.

## Install or update

Version 1.0.3 uses the separate public download repository
[Wgeshow/optical-design-studio-downloads](https://github.com/Wgeshow/optical-design-studio-downloads).
Once an approved release is published there, anyone can download its installer
and checksum. This private repository retains the development tree and history.
A private branch cannot provide anonymous downloads, so the two repositories
have separate roles.

**About** shows the installed version, recorded installation/update date, and
update status. **Check for updates** contacts the public update service only when
requested, with no GitHub account, access token, sign-in, or saved-credential
access. **Download update** appears beside Check for a newer compatible stable
release. The app checks the package size and SHA-256 digest before saving it.
It offers to open the containing folder; it does not run an installer or replace
a running application automatically. Versions 1.0.2 and earlier need an installer
upgrade to receive this anonymous updater.

The installer lets the user choose an application directory and includes the
native runtime dependencies. Compatible NVIDIA hardware and its driver are
required for GPU use. Installed research data remains separate, normally at
`%LOCALAPPDATA%/Optical Design Studio/User Data` on Windows. The update client
does not upload projects, materials, optical constants, fields, or results.

## Distribution review

The **public packaging profile starts with an empty research-data seed**. It
excludes research libraries, saved sessions, credentials, previews, and local
build reports. It retains the readable application/native source and third-party
notices required by the current distribution. S4’s supplied `COPYRIGHT` identifies
its GNU GPL version 2-or-later terms; preserve `src/S4-source/COPYRIGHT` and
`src/S4-source/COPYING` with that code. Other dependency notices remain beside
their source or in the packaged license folder.

A private GitHub development repository does not make source embedded in a
public installer private. **Public distribution of this package and its bundled
source remains pending the owner’s approval.** Do not publish a public release
merely because its source has been prepared or merged privately. The private
source archive and draft release do not publish the installer or enable anonymous
downloads by themselves.

## Source layout

- `src/`: application modules, launchers, dependency requirements, and guides.
- `src/tests/`: test source; inputs are generated in temporary directories.
- `src/pcs_s4_runtime/`: Python runtime and multiprocessing glue.
- `src/S4-source/`: native S4 C/C++ code, build tools, upstream documentation
  and examples, and embedded dependency headers with their notices.
- `src/third-party-licenses/`: supplied third-party notices.
- `packaging/`: PyInstaller and Inno Setup recipes with the original icon assets.

The source archive excludes native extensions, DLLs, executables, dependency
payloads, credentials, installation receipts, research datasets, saved projects,
and build logs. It preserves existing license notices; no new blanket license
has been assigned to third-party code.

## Run from source

Use **Python 3.12** with a native S4 build matching the operating system,
architecture, Python ABI, and BLAS/LAPACK runtime. Installing Python requirements
alone does not build or supply the native extension. After the relevant native
setup, launch `python src/qt_app.py`. The previous browser interface remains
available through the `launch_web_gui` scripts.

### Windows x64

The tested Windows runtime uses NumPy 1.26.4 and MKL 2023.1. Create or activate an
appropriate environment, for example using `src/environment.yml`, then install
the desktop requirements. Put the optional ML packages in the separate source
dependency directory to preserve the existing NumPy/MKL pair:

```powershell
conda env create -f src/environment.yml
conda activate s4_updated
python -m pip install -r src/requirements-desktop.txt
python -m pip install --target src/ml_dependencies --no-deps -r src/requirements-ml.txt
```

Build S4 using the supplied LLVM-MinGW helper and an installed 64-bit toolchain
plus the matching LP64 MKL/OpenBLAS library. These toolchains and runtime binaries
are not stored in this source repository:

```powershell
python src/S4-source/tools/build_windows.py --compiler 'C:\path\to\llvm-mingw\bin\clang.exe' --blas 'C:\path\to\mkl_rt.2.dll' --output src/pcs_s4_runtime
python src/qt_app.py
```

The required BLAS/runtime DLLs must be discoverable; a Conda environment’s
`Library/bin` is configured automatically. Optional GPU support needs a compatible
CUDA toolkit at build time. See `src/S4-source/OPTIMIZATION_NOTES.md` and the
helper’s `--cuda-include` argument. Verify CPU operation before enabling GPU work.

### Linux

Install Python 3.12 development headers, a C/C++ toolchain, CMake, and OpenBLAS
development libraries using the distribution’s package manager, then run:

```bash
cd src
bash setup_linux.sh
bash launch_qt_gui.sh
```

Setup creates `.venv`, installs `requirements-linux.txt`, and builds the matching
S4 extension with CMake. `bash setup_linux.sh --cuda` additionally needs a
compatible CUDA toolkit. Windows DLLs and installers do not run natively on Linux.
Linux execution and a Linux update package require separate validation; this
Windows release does not claim to provide a tested Linux installer.

## Tests and installer builds

The standard-library workflow checks run without credentials or live network
requests: 32 anonymous update-client tests, four retained legacy credential-helper
tests, and two version-receipt tests. The legacy credential helpers are not used
by the 1.0.3 About page or updater. Run them locally from `src`:

```powershell
python -m unittest discover -s tests -p test_update_client.py -v
python -m unittest discover -s tests -p test_update_credentials.py -v
python -m unittest discover -s tests -p test_app_version.py -v
```

Native UI tests also need PyQt6; solver/integration tests need S4 and the numerical
dependencies. See [`packaging/BUILDING.md`](packaging/BUILDING.md) for build and
verification instructions. The Windows packager requires an explicitly supplied
application source/library bundle containing native and ML dependencies, official
NVIDIA redistributable wheels, PyInstaller, and Inno Setup. A source checkout alone
is not a complete installer payload. Select the public profile for an empty seed
and review its final file inventory. Preserve the Inno application ID for upgrades.

## Stable and experimental work

Develop on **`test`**, run the appropriate checks, and review a pull request into
private **`main`**. Source imports and tests do not publish releases, merge branches,
or install updates. Experimental work must not be released as stable.

For an approved release, set `APP_VERSION` and `BUILD_DATE` in `src/app_version.py`,
build and verify the installer, and record the exact reviewed stable source commit.
Keep the matching `OpticalDesignStudio-Source-1.0.3.zip` in the private development
release. After distribution approval, the separate public download release uses
the matching version tag and assets:

- `OpticalDesignStudio-Setup-1.0.3-Windows-x64.exe`
- Its `.sha256` checksum file.

Assemble releases as drafts and publish only after review. The app ignores drafts
and prereleases, compares numeric versions, and requires a compatible package
with a SHA-256 digest. Windows assets must use the exact pattern
`OpticalDesignStudio-Setup-<version>-Windows-x64.exe`. Future Linux packages need
their own build and verification. Access tokens, signing keys, installation
receipts, or unapproved research data must not be attached to a release.
