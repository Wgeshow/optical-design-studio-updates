# Optical Design Studio

## Install

1. Double-click `OpticalDesignStudio-Setup-1.0.3-Windows-x64.exe`.
2. Choose the installation folder. The default is `%LOCALAPPDATA%\Programs\Optical Design Studio`. Choose a folder your Windows account can write to.
3. Choose whether to create a desktop shortcut, then click **Install**. The wizard shows the required disk space before installation.
4. Leave **Launch Optical Design Studio** selected and click **Finish**.

The installer includes the application, Python runtime, native S4 simulation engine, PyQt6 interface, machine-learning libraries, and built-in material definitions. This public delivery package starts with an empty saved-work library and does not include the publisher's research results or uploaded material tables. No separate Python or Conda installation or internet connection is required. The installer uses the existing optical-layer icon and follows the Windows light or dark appearance.

Version 1.0.3 checks the public download repository without requiring a GitHub account or access token. **About** shows the application version, last installation/update date, and update status. It supports dark and light modes and keeps the integrated application title bar: **File** contains Open project and Save project, also available with **Ctrl+O** and **Ctrl+S**; View switches appearance. Drag the empty top-bar area to move the window, double-click it to maximize or restore, or drag a window edge to resize. The close button retains the application's session-save and running-calculation checks.

This package is for Intel/AMD 64-bit Windows 10 (version 1809 or later) and Windows 11. CPU simulation is available without an NVIDIA GPU. GPU acceleration requires compatible NVIDIA hardware and its NVIDIA driver; the installer does not install a device driver. GPU acceleration applies to supported computations, and the application may also use the CPU.

## Your saved work

The installation folder holds the application and its runtime files. Your material library, saved results, and settings are kept separately in:

`%LOCALAPPDATA%\Optical Design Studio\User Data`

Updates and uninstalling preserve your saved work, including results and material presets from a previous version. Changing the installation folder does not move or reset that library. Use **Saved work** in the application to export a library bundle for sharing or backup.

To upgrade, run the newer installer, choose the existing installation folder, and complete the wizard. The folder chooser remains available on upgrades. Close running simulations before upgrading. To uninstall, use **Settings > Apps > Installed apps > Optical Design Studio > Uninstall** in Windows.

## Check for a newer release

Updates are hosted in the public [Optical Design Studio downloads repository](https://github.com/Wgeshow/optical-design-studio-downloads). You do not need to sign in. The development repository is separate from the download repository.

1. Open **About**.
2. Click **Check for updates**. The page displays the result; it does not claim that the program is up to date until a check succeeds. If no stable release has been published, the page reports that status.
3. When a newer compatible stable release exists, **Download update** appears beside the check button. Select a destination and wait for the download to finish. The app validates the downloaded file against its published SHA-256 digest.
4. Save your work and finish running calculations. Close Optical Design Studio, then run the downloaded installer and use your existing installation folder.

The update feature checks and downloads only when requested. It does not use account credentials, silently install updates, upload your library, or interrupt calculations. Draft releases and experimental prereleases are excluded from stable update checks. A `test` branch is for development; a change on that branch is not an application update until a release is published.

The installer writes `installation.json` in the application folder when installation completes. About uses that receipt for the last installation/update date; starting the application does not reset it. A source checkout or an unpacked build without an installer receipt displays release/build information without inventing an installation date.

## Files included with the application

- `Optical Design Studio.exe` launches the interface.
- `OpticalDesignBackend.exe` runs simulations and optimization jobs.
- `_internal` contains the runtime and bundled application source in `_internal\source`.
- `installation.json` records the installed version and installation time.
- `THIRD_PARTY_LICENSES` contains dependency licenses; the application source also includes its `third-party-licenses` folder.

Keep the installed application folder intact. Copying only the application EXE does not include the runtime. Share the installer EXE to install the application on another computer.

## Rebuilding the installer

The installer definition is `OpticalDesignStudio.iss`. Build and test the PyInstaller one-folder payload first. Prepare the original icon files with:

```powershell
python prepare_installer_assets.py --source-directory "C:\path\to\original\icon\folder"
```

Compile with Inno Setup 7.1 or later, adjusting paths and the release version:

```powershell
& "C:\path\to\ISCC.exe" `
  '/DPayloadDir=C:\build\dist\Optical Design Studio' `
  '/DOutputDir=C:\build\release' `
  '/DVersion=1.0.3' `
  '.\OpticalDesignStudio.iss'
```

The installer is a single offline EXE. It installs per user, creates Start-menu and optional desktop shortcuts, and registers a Windows uninstaller. It does not change system Python, Conda, or PATH settings.

Installer behavior follows the official Inno Setup documentation for the [destination folder page](https://jrsoftware.org/ishelp/topic_setup_disabledirpage.htm), [per-user installation](https://jrsoftware.org/ishelp/topic_setup_privilegesrequired.htm), [light and dark styling](https://jrsoftware.org/ishelp/topic_setup_wizardstyle.htm), and [uninstall file handling](https://jrsoftware.org/ishelp/topic_uninstalldeletesection.htm).
