# Optical Design Studio updates

Private distribution repository for Optical Design Studio installers, future update packages, and release notes. Approved users receive releases through their own GitHub accounts.

## Current status

Optical Design Studio **1.0.1 does not contain an in-app updater**. Creating this repository does not enable automatic updates. Until a compatible updater is shipped, approved users must download a published installer and run it themselves.

A future client will need individual authentication, verified update metadata and packages, and a safe restart/install process. Existing installations will need an initial upgrade to receive that client.

## Publish a release

1. Build and test the intended application version. Use a new version number for each release.
2. Open this repository's **Releases** page and choose **Draft a new release**.
3. Create the matching version tag, such as `v1.0.2`, and enter a title such as `Optical Design Studio 1.0.2`.
4. Describe the changes, supported operating system and architecture, and installation instructions.
5. Attach the tested installer or update package and its SHA-256 checksum file. Upload packages as release assets rather than committing binaries to Git history. A checksum alone is not a publisher signature.
6. Save the draft. Check the version, notes, package contents, and filenames before publishing. Mark testing builds as pre-releases.
7. Choose **Publish release** when the assets are ready. Publication remains restricted by this repository's private access permissions.

Keep previous stable releases available for recovery. Once a version has shipped, publish corrections under a new version instead of replacing its packages.

For future in-app updates, attach the signed metadata and package format required by the implemented updater; an installer asset alone will not activate it.

## Manage access

Keep this repository **private**. Grant access only to approved users, and reserve publishing permission for maintainers. For an organization-owned repository, use the **Read** role for download-only users. Personal repositories have different collaborator permissions; move to an organization if separate read and publishing roles are needed.

Users must sign in to GitHub with an account authorized for this repository. A repository or download link does not grant access by itself. Removing access blocks future private downloads but does not disable an application already installed offline.

## Repository contents

This repository is for release distribution and instructions. Do not commit personal simulation libraries, material datasets, research results, credentials, access tokens, or signing private keys. Review package contents before attaching them to a release.

## Reference

- [GitHub: managing releases](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)
- [GitHub: repository roles for organizations](https://docs.github.com/en/organizations/managing-user-access-to-your-organizations-repositories/managing-repository-roles/repository-roles-for-an-organization)
