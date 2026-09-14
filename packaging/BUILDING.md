Build on 64-bit Windows using Python 3.12 and the application's pinned dependencies. The native S4 extension requires the matching MKL 2023.1 DLLs in the build interpreter's `Library/bin` folder. PyInstaller 6.22.2 and Inno Setup 7.1.0 were used for this release.

1. Export the full data/source bundle from Saved work.
2. Keep the current complete application source alongside the export.
3. Install the Python requirements, including `requirements-desktop.txt`, `requirements-ml.txt`, and PyInstaller, into the build environment.
4. Install the official Inno Setup compiler, or pass its location to the command below.
5. Put these official NVIDIA Windows wheels in `tools` using `python -m pip download --no-deps --only-binary=:all: --dest tools nvidia-cublas-cu11==11.11.3.6 nvidia-cuda-runtime-cu11==11.8.89`.
6. Keep the supplied original icon files in `assets`.

Run from PowerShell:

```powershell
.\build_windows.ps1 -SourceRoot 'C:\path\to\application' -DataBundle 'C:\path\to\s4_bundle.zip' -Python 'C:\path\to\python.exe' -InnoCompiler 'C:\path\to\ISCC.exe'
```

The output is `release/OpticalDesignStudio-Setup-1.0.2-Windows-x64.exe`. The build checks the shared-data checksums, creates a data-only seed archive, compiles GUI and calculation executables sharing one private runtime, copies the readable application/native source and dependency notices, and runs the packaged CPU/ML/field/GUI checks before creating Setup. Version 1.0.2 includes the About page and authenticated, user-requested checks and installer downloads from the private release repository. It does not automatically apply an update.

The build environment's paths are not needed on the destination computer. Setup installs files only in the chosen application directory and creates per-user shortcuts/uninstall registration. First launch imports the supplied records into the separate writable user-data folder. Existing data is never replaced. The installer does not install system Python, alter PATH, or install graphics drivers.

Source distribution and third-party dependency licensing information are in the installed `THIRD_PARTY_LICENSES` folder. Code signing requires a publisher certificate and is not part of this local build.

For a release with a different shared library, set the build verification's expected saved-entry count to that library's count. Keep the Inno `AppId` stable for upgrades. Set `APP_VERSION` and `BUILD_DATE` in the application's `app_version.py` before a release. `prepare_payload.py` reads those literal constants without importing the GUI and generates both `version_info.txt` and `version.iss`. The payload inventory, installer, executable versions, verification default, and release reports use that version. Do not change the Inno version override independently of the application.

For a complete release verification, run the packaged application check and an isolated upgrade from the previously published installer before finalizing deliverables:

```powershell
python verify_frozen.py 'dist/Optical Design Studio/Optical Design Studio.exe' 'v102_test' --gpu
python verify_local_installation.py 'release/OpticalDesignStudio-Setup-1.0.2-Windows-x64.exe' --previous-installer 'release/OpticalDesignStudio-Setup-1.0.1-Windows-x64.exe'
python finalize_release.py
```

Use `--cpu-only` on the installer verification and omit `--gpu` on computers without NVIDIA hardware. Installer verification uses an owned temporary directory outside OneDrive, refuses to modify an existing registered installation, checks the install receipt, and verifies that upgrade and uninstall preserve the user library. Release finalization preserves each version's evidence and writes the installer checksum beside its EXE.

The release should contain the installer EXE, its `.sha256` checksum, and a source archive for the same version. Publish a stable release from the release branch only after testing. Use the separate `test` branch for experimental changes and mark any experimental release as a prerelease. The application ignores draft releases and prereleases. Do not include access tokens, credential-store contents, or signing keys in source or release assets.

The Windows installer requires Windows-native S4 and runtime binaries. Linux users run the cross-platform Python source with a native Linux S4 build and its dependencies; the Windows EXE and its bundled DLLs are not Linux binaries. See the application's source README and Linux launch/build scripts for that workflow. A Linux packaged update needs its own platform artifact and verification; this release distributes a Windows x64 installer.
