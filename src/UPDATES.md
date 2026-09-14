# About and private updates

Version 1.0.2 adds **About** to the desktop sidebar. It shows the installed version, actual installation/update date when recorded, platform, last check time, and private release status. **File → Open project / Save project** and **Ctrl+O / Ctrl+S** remain available; duplicate title-bar buttons were removed.

## Connect this computer

Open **About → Connect GitHub**. Enter your own GitHub personal access token with access to `Wgeshow/optical-design-studio-updates`. For the repository owner, use a fine-grained token limited to this repository with **Contents: Read-only**. Existing browser sign-in does not connect the native application.

GitHub currently does not support fine-grained tokens for outside/repository collaborators in all cases. An invited collaborator needs a supported token for their account, or a future GitHub App connection. A classic token's `repo` scope is broader than one repository; do not describe it as read-only. Never share the owner's token. No UTA Students organization access is required or configured for this personal repository. [GitHub token documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)

Leave **Remember on this computer** unchecked for session-only access. When selected, Windows stores the token in the signed-in user's Credential Manager. Linux/macOS can use an installed supported system keyring; without one, use session access. Tokens are never stored in project files, research libraries, shared exports or application source. **Disconnect** removes remembered application access where available.

## Check and download

**Check for updates** checks the configured private repository on demand. It ignores draft and pre-release builds, compares numeric version tags and selects the matching platform package. No automatic startup checks run. Empty releases, incompatible packages, missing permissions, offline connections and invalid metadata are reported separately; none is called “up to date.”

**Download update** appears beside Check only for a newer compatible release. Choose the folder, follow progress, or cancel. A completed download must match GitHub's authenticated SHA-256 digest and file size. The application preserves files already in the selected folder and offers **Open download folder** after success. Run the installer yourself when ready. No automatic installation, process replacement or rollback is included in this version.

Simulation and optimization can continue while checks/downloads run. Closing the application cancels an active update request and waits for its worker to finish before saving and closing.

## Publish stable and experimental versions

The personal private repository is https://github.com/Wgeshow/optical-design-studio-updates . `main` holds stable source; `test` is for experimental changes. Test a change there, open a pull request into `main`, and publish a stable release only after validation. Mark experimental releases as **pre-release** so the application does not offer them.

Use numeric stable tags such as `v1.0.2`. Windows x64 installer filenames must be `OpticalDesignStudio-Setup-1.0.2-Windows-x64.exe`, with the same version in the tag and executable metadata. Attach the source archive and checksum files as additional release assets. GitHub must provide a valid SHA-256 asset digest before the download button is offered. A checksum verifies transport/file integrity; it is not an independent publisher signature.

Source compatibility includes Windows and Linux. The released installer is Windows x64; a Linux update requires its own tested package. Personal repository collaborators have write access, so do not promise download-only roles for invitations. Any future account/permission changes need to remain under the user's personal account unless separately authorized.
