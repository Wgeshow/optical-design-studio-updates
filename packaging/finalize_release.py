"""Publish a verified installer to the local deliverables folder, never online."""
import hashlib
import json
from pathlib import Path
import shutil
import struct

from verify_frozen import pe_machine
from build_version import release_info

ROOT = Path(__file__).resolve().parent


def digest(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 ** 2), b''):
            result.update(chunk)
    return result.hexdigest()


def icon_check(executable):
    import pefile
    icon = (ROOT / 'assets' / 'S4_Studio.ico').read_bytes()
    reserved, kind, count = struct.unpack_from('<HHH', icon)
    assert reserved == 0 and kind == 1
    expected = []
    for number in range(count):
        size, offset = struct.unpack_from('<II', icon, 6 + number * 16 + 8)
        expected.append(hashlib.sha256(icon[offset:offset + size]).hexdigest())
    embedded = []
    with pefile.PE(str(executable)) as binary:
        for category in binary.DIRECTORY_ENTRY_RESOURCE.entries:
            if category.id == 3:
                for resource in category.directory.entries:
                    for language in resource.directory.entries:
                        info = language.data.struct
                        embedded.append(hashlib.sha256(binary.get_data(info.OffsetToData, info.Size)).hexdigest())
    if sorted(expected) != sorted(embedded):
        raise AssertionError('The application icon differs from the supplied original.')
    return dict(original_icon_images=count, embedded_icon_images=len(embedded), matches_original=True)


def main():
    info = release_info()
    version = info['version']
    filename = f'OpticalDesignStudio-Setup-{version}-Windows-x64.exe'
    installer = ROOT / 'release' / filename
    verification = json.loads((ROOT / 'install_verification' / 'latest-verification.json').read_text(encoding='utf-8'))
    if verification['status'] != 'passed' or Path(verification['installer']).resolve() != installer.resolve():
        raise AssertionError('This release has not passed installer verification.')
    runtime_path = Path(verification['checks']['installed_runtime_without_developer_paths']['detail']['report'])
    runtime = json.loads(runtime_path.read_text(encoding='utf-8'))
    if any(not result['passed'] for result in runtime['checks'].values()):
        raise AssertionError('Installed application verification failed.')
    payload = ROOT / 'dist' / 'Optical Design Studio'
    manifest = json.loads((payload / 'PAYLOAD-MANIFEST.json').read_text(encoding='utf-8'))
    assert manifest['version'] == version
    assert manifest['build_date'] == info['build_date']
    for executable in (installer, payload / 'Optical Design Studio.exe', payload / 'OpticalDesignBackend.exe'):
        assert pe_machine(executable) == 0x8664, executable
    icon = icon_check(payload / 'Optical Design Studio.exe')
    checksum = digest(installer)
    target = ROOT.parent / filename
    if target.exists() and digest(target) != checksum:
        raise FileExistsError('An unrelated file already uses the release filename: ' + str(target))
    if not target.exists():
        shutil.copyfile(installer, target)
    assert digest(target) == checksum
    (ROOT.parent / (filename + '.sha256')).write_text(checksum + '  ' + filename + '\n', encoding='ascii')
    (installer.parent / (filename + '.sha256')).write_text(checksum + '  ' + filename + '\n', encoding='ascii')
    # Keep durable evidence for each release instead of referring to a temporary
    # installer test directory or replacing the previous release's reports.
    evidence = ROOT / f'verification-{version}'
    evidence.mkdir(exist_ok=True)
    stable_runtime = evidence / 'installed-runtime.json'
    stable_runtime.write_text(json.dumps(runtime, indent=2), encoding='utf-8')
    verification['checks']['installed_runtime_without_developer_paths']['detail']['report'] = str(stable_runtime)
    stable_installer_report = evidence / 'installer-verification.json'
    stable_installer_report.write_text(json.dumps(verification, indent=2), encoding='utf-8')
    previous_version = verification['checks']['custom_folder_install']['detail'].get('payload_version')
    if verification.get('previous_installer'):
        upgrade_summary = (f'An isolated installation of {previous_version} was upgraded to {version}; '
                           'the saved library was verified byte-for-byte before relaunch, and the new '
                           'application was tested against that library. ')
    else:
        upgrade_summary = 'Reinstalling the package preserved the saved library byte-for-byte. '
    guide = ROOT.parent / 'Optical_Design_Studio_Installation.md'
    guide.write_text((ROOT / 'INSTALLATION.md').read_text(encoding='utf-8') +
        '\n## Release verification\n\n'
        f'Version {version} passed packaged application and installer checks. ' + upgrade_summary +
        'Uninstall also preserved the library. The installer recorded its version and actual installation '
        'date, and launching the application did not change that date.\n\n'
        'The installer is unsigned, so Windows may display an unknown-publisher notice. '
        'Native Windows maximize/restore was tested; the Windows 11 maximize-hover Snap menu is not implemented.\n', encoding='utf-8')
    checks = verification['checks']
    release = dict(**info, installer=str(target), bytes=target.stat().st_size, sha256=checksum,
                   architecture='Windows x64 (AMD64)', signed=False, online_updates_enabled=True,
                   update_mode='User-requested authenticated check and download; installer is run manually',
                   automatic_update_installation=False, updates=manifest['updates'],
                   upgraded_from_version=previous_version if verification.get('previous_installer') else None,
                   included_saved_entries=manifest['build_input']['seed_runs'],
                   included_custom_material_presets=manifest['build_input']['seed_presets'],
                   application_runtime_checks={name: value['passed'] for name, value in runtime['checks'].items()},
                   installer_checks={name: value['passed'] for name, value in checks.items()},
                   upgrade_saved_files_unchanged=checks['upgrade_preserves_user_data_and_untracked_files']['detail']['saved_data_files_unchanged'],
                   uninstall_saved_files_unchanged=checks['uninstall_preserves_user_data_and_untracked_files']['detail']['saved_data_files_unchanged'],
                   runtime_report=str(stable_runtime), installer_report=str(stable_installer_report),
                   icon_verification=icon, guide=str(guide))
    text = json.dumps(release, indent=2)
    latest = ROOT.parent / 'OPTICAL_DESIGN_STUDIO_RELEASE.json'
    if latest.is_file():
        previous = json.loads(latest.read_text(encoding='utf-8'))
        previous_archive = ROOT.parent / f"OPTICAL_DESIGN_STUDIO_RELEASE_{previous['version']}.json"
        if previous['version'] != version and not previous_archive.exists():
            shutil.copyfile(latest, previous_archive)
    (ROOT.parent / f'OPTICAL_DESIGN_STUDIO_RELEASE_{version}.json').write_text(text, encoding='utf-8')
    latest.write_text(text, encoding='utf-8')
    print(text)


if __name__ == '__main__':
    main()
