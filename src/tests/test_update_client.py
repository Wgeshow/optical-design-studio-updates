"""No-network tests for private release selection and safe update downloads."""
from dataclasses import replace
from email.message import Message
import hashlib
from http.client import IncompleteRead
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import update_client as updates
from update_client import GitHubUpdateClient, ReleaseInfo, UpdateCancelled, UpdateError


TOKEN = "never-display-or-forward-this-token"
DATA = b"a simulated update executable\x00\x01"
BASE = "https://api.github.com"
REPO = f"/repos/{updates.REPOSITORY}"


def headers(**values):
    result = Message()
    for name, value in values.items():
        result[name.replace("_", "-")] = str(value)
    return result


class Response(io.BytesIO):
    def __init__(self, data=b"", status=200, response_headers=None):
        super().__init__(data)
        self.status = status
        self.headers = response_headers or headers()


class Opener:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append(request)
        if not self.responses:
            raise AssertionError("Unexpected HTTP request")
        expected, result = self.responses.pop(0)
        if request.full_url != expected:
            raise AssertionError(f"Wrong URL: {request.full_url!r}, wanted {expected!r}")
        if isinstance(result, Exception):
            raise result
        return result


def json_response(value):
    return Response(json.dumps(value).encode("utf-8"))


def release(version="1.0.2", platform="windows-x64", **changes):
    result = {
        "tag_name": f"v{version}", "draft": False, "prerelease": False,
        "published_at": "2026-09-13T12:00:00Z", "body": "Release notes",
        "html_url": "https://untrusted.example/fake-release",
        "assets": [{"id": 123, "state": "uploaded", "size": len(DATA),
                    "name": updates._PACKAGE_TEMPLATES[platform].format(version=version),
                    "digest": "sha256:" + hashlib.sha256(DATA).hexdigest(),
                    "url": "https://untrusted.example/fake-api",
                    "browser_download_url": "https://untrusted.example/fake-package"}],
    }
    result.update(changes)
    return result


def check_opener(releases, *, private=True, account="approved-user"):
    return Opener([
        (BASE + "/user", json_response({"login": account})),
        (BASE + REPO, json_response({"private": private, "full_name": updates.REPOSITORY})),
        (BASE + REPO + "/releases?per_page=100&page=1", json_response(releases)),
    ])


def release_info():
    return ReleaseInfo("1.0.2", "v1.0.2", "2026-09-13T12:00:00Z", "Release notes",
                       updates.REPOSITORY_URL + "/releases/tag/v1.0.2", 123,
                       "OpticalDesignStudio-Setup-1.0.2-Windows-x64.exe", len(DATA),
                       hashlib.sha256(DATA).hexdigest())


class ReleaseCheckTests(unittest.TestCase):
    def test_highest_semantic_version_across_pages_not_latest_by_date(self):
        first = [release("1.9.0"), release("9.0.0", prerelease=True), release("8.0.0", draft=True)]
        first += [release("1.0.0", draft=True) for _ in range(97)]
        opener = check_opener(first)
        opener.responses.append((BASE + REPO + "/releases?per_page=100&page=2", json_response([release("1.10.0")])))
        result = GitHubUpdateClient(TOKEN, opener=opener).check("1.9.0")
        self.assertEqual((result.status, result.release.version, result.username), ("available", "1.10.0", "approved-user"))
        self.assertEqual(result.release.html_url, updates.REPOSITORY_URL + "/releases/tag/v1.10.0")
        self.assertTrue(result.checked_at.endswith("Z"))
        self.assertEqual(len(opener.requests), 4)
        for request in opener.requests:
            self.assertEqual(request.get_header("Authorization"), "Bearer " + TOKEN)

    def test_empty_and_incompatible_are_not_current(self):
        for items, expected in [([], "no_releases"), ([release(platform="linux-x64")], "no_compatible"),
                                ([release("9.0.0", prerelease=True)], "no_releases")]:
            with self.subTest(status=expected):
                result = GitHubUpdateClient(TOKEN, opener=check_opener(items)).check("1.0.1")
                self.assertEqual(result.status, expected)
                self.assertIsNone(result.release)

    def test_no_windows_package_is_offered_on_linux(self):
        result = GitHubUpdateClient(TOKEN, opener=check_opener([release()])).check("1.0.1", "linux-x64")
        self.assertEqual(result.status, "no_compatible")
        result = GitHubUpdateClient(TOKEN, opener=check_opener([release(platform="linux-x64")])).check("1.0.1", "linux-x64")
        self.assertEqual(result.status, "available")
        self.assertTrue(result.release.asset_name.endswith("Linux-x64.tar.gz"))

    def test_current_requires_an_eligible_verified_release(self):
        for installed in ("1.0.2", "1.1.0"):
            result = GitHubUpdateClient(TOKEN, opener=check_opener([release()])).check(installed)
            self.assertEqual(result.status, "current")

    def test_tag_filename_version_mismatch_is_incompatible(self):
        mismatch = release("1.0.2")
        mismatch["assets"][0]["name"] = "OpticalDesignStudio-Setup-1.0.3-Windows-x64.exe"
        result = GitHubUpdateClient(TOKEN, opener=check_opener([mismatch])).check("1.0.1")
        self.assertEqual(result.status, "no_compatible")

    def test_missing_digest_does_not_silently_fall_back_to_old_release(self):
        newest = release("1.0.3")
        newest["assets"][0].pop("digest")
        with self.assertRaises(UpdateError) as caught:
            GitHubUpdateClient(TOKEN, opener=check_opener([release(), newest])).check("1.0.1")
        self.assertEqual(caught.exception.code, "integrity_metadata")

    def test_missing_or_oversized_or_unuploaded_assets_are_rejected(self):
        for key, value in [("state", "new"), ("id", True), ("size", 0), ("size", updates._MAX_PACKAGE_BYTES + 1)]:
            with self.subTest(key=key, value=value):
                item = release()
                item["assets"][0][key] = value
                with self.assertRaises(UpdateError) as caught:
                    GitHubUpdateClient(TOKEN, opener=check_opener([item])).check("1.0.1")
                self.assertEqual(caught.exception.code, "invalid_asset")

    def test_private_repository_is_required_before_listing(self):
        opener = check_opener([], private=False)
        with self.assertRaises(UpdateError) as caught:
            GitHubUpdateClient(TOKEN, opener=opener).check("1.0.1")
        self.assertEqual(caught.exception.code, "repository_not_private")
        self.assertEqual(len(opener.requests), 2)

    def test_auth_missing_access_rate_limit_and_network_never_become_current(self):
        for status, expected in [(401, "authentication"), (404, "access_denied"), (403, "access_denied"), (429, "rate_limit")]:
            opener = Opener([(BASE + "/user", HTTPError(BASE + "/user", status, TOKEN, headers(), io.BytesIO(TOKEN.encode())))])
            with self.subTest(status=status), self.assertRaises(UpdateError) as caught:
                GitHubUpdateClient(TOKEN, opener=opener).check("1.0.1")
            self.assertEqual(caught.exception.code, expected)
            self.assertNotIn(TOKEN, str(caught.exception))
        opener = Opener([(BASE + "/user", URLError("secret=" + TOKEN))])
        with self.assertRaises(UpdateError) as caught:
            GitHubUpdateClient(TOKEN, opener=opener).check("1.0.1")
        self.assertEqual(caught.exception.code, "network")
        self.assertNotIn(TOKEN, str(caught.exception))

    def test_releases_404_is_not_empty(self):
        opener = check_opener([])
        url, _ = opener.responses[-1]
        opener.responses[-1] = (url, Response(status=404))
        with self.assertRaises(UpdateError) as caught:
            GitHubUpdateClient(TOKEN, opener=opener).check("1.0.1")
        self.assertEqual(caught.exception.code, "access_denied")

    def test_json_redirect_is_not_followed_with_credentials(self):
        opener = Opener([(BASE + "/user", Response(status=302, response_headers=headers(Location="https://evil.example/")))])
        with self.assertRaises(UpdateError):
            GitHubUpdateClient(TOKEN, opener=opener).check("1.0.1")
        self.assertEqual(len(opener.requests), 1)

    def test_incomplete_json_response_becomes_safe_network_error(self):
        response = Response()
        response.read1 = lambda count: (_ for _ in ()).throw(IncompleteRead(TOKEN.encode(), 99))
        opener = Opener([(BASE + "/user", response)])
        with self.assertRaises(UpdateError) as caught:
            GitHubUpdateClient(TOKEN, opener=opener).check("1.0.1")
        self.assertEqual(caught.exception.code, "network")
        self.assertNotIn(TOKEN, str(caught.exception))
        self.assertTrue(response.closed)

    def test_json_stream_checks_cancel_between_available_chunks(self):
        event = threading.Event()
        response = Response()

        def first_chunk(size):
            event.set()
            return b'{"login":'

        response.read = lambda size: self.fail("A buffered read delays cancellation")
        response.read1 = first_chunk
        opener = Opener([(BASE + "/user", response)])
        with self.assertRaises(UpdateCancelled):
            GitHubUpdateClient(TOKEN, opener=opener).check("1.0.1", cancel=event)
        self.assertTrue(response.closed)

    def test_streamed_json_remains_size_bounded(self):
        response = Response(b" " * 33)
        opener = Opener([(BASE + "/user", response)])
        with patch.object(updates, "_MAX_JSON_BYTES", 32):
            with self.assertRaises(UpdateError) as caught:
                GitHubUpdateClient(TOKEN, opener=opener).check("1.0.1")
        self.assertEqual(caught.exception.code, "invalid_response")
        self.assertTrue(response.closed)

    def test_invalid_account_names_stop_before_repository_access(self):
        for account in ("", "x" * 40, "not an account", "abc--def", "-abc", "abc-", "é", "<script>"):
            with self.subTest(account=account):
                opener = check_opener([], account=account)
                with self.assertRaises(UpdateError) as caught:
                    GitHubUpdateClient(TOKEN, opener=opener).check("1.0.1")
                self.assertEqual(caught.exception.code, "invalid_response")
                self.assertEqual(len(opener.requests), 1)

    def test_reaching_pagination_bound_cannot_claim_current(self):
        opener = check_opener([release()])
        opener.responses[-1] = (BASE + REPO + "/releases?per_page=1&page=1", json_response([release()]))
        with patch.object(updates, "_PAGE_SIZE", 1), patch.object(updates, "_MAX_PAGES", 1):
            with self.assertRaises(UpdateError) as caught:
                GitHubUpdateClient(TOKEN, opener=opener).check("1.0.2")
        self.assertEqual(caught.exception.code, "listing_limit")

    def test_invalid_inputs_and_cancel_make_no_requests(self):
        opener = Opener([])
        for invalid_token in ("bad\nheader", "x" * 2049):
            with self.subTest(token_length=len(invalid_token)), self.assertRaises(UpdateError):
                GitHubUpdateClient(invalid_token, opener=opener)
        client = GitHubUpdateClient(TOKEN, opener=opener)
        with self.assertRaises(UpdateError):
            client.check("latest")
        with self.assertRaises(UpdateError):
            client.check("1.0.1", "windows-arm64")
        event = threading.Event()
        event.set()
        with self.assertRaises(UpdateCancelled):
            client.check("1.0.1", cancel=event)
        self.assertEqual(opener.requests, [])


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name).resolve()
        self.info = release_info()
        self.api_url = BASE + REPO + "/releases/assets/123"

    def tearDown(self):
        self.temp.cleanup()

    def direct_client(self, data=DATA, response_headers=None):
        opener = Opener([(self.api_url, Response(data, response_headers=response_headers))])
        return GitHubUpdateClient(TOKEN, opener=opener), opener

    def assert_directory_clean(self, existing=None):
        self.assertEqual(set(self.directory.iterdir()), set(existing or []))

    def test_verified_stream_saved_with_progress_and_no_execution(self):
        client, opener = self.direct_client(response_headers=headers(Content_Length=len(DATA)))
        progress = []
        target = client.download(self.info, self.directory, progress=lambda done, total: progress.append((done, total)))
        self.assertEqual(target.read_bytes(), DATA)
        self.assertEqual(target.name, self.info.asset_name)
        self.assertEqual(progress[0], (0, len(DATA)))
        self.assertEqual(progress[-1], (len(DATA), len(DATA)))
        self.assertEqual(opener.requests[0].get_header("Accept"), "application/octet-stream")
        self.assert_directory_clean([target])

    def test_private_asset_redirects_strip_authorization_and_api_headers(self):
        for status in (302, 307):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as directory:
                target_url = "https://release-assets.githubusercontent.com/github-production-release-asset/123/file?signature=private"
                opener = Opener([(self.api_url, HTTPError(self.api_url, status, "redirect", headers(Location=target_url), io.BytesIO())),
                                 (target_url, Response(DATA))])
                result = GitHubUpdateClient(TOKEN, opener=opener).download(self.info, directory)
                self.assertEqual(result.read_bytes(), DATA)
                self.assertEqual(opener.requests[0].get_header("Authorization"), "Bearer " + TOKEN)
                self.assertIsNone(opener.requests[1].get_header("Authorization"))
                self.assertIsNone(opener.requests[1].get_header("X-github-api-version"))

    def test_insecure_or_unapproved_redirects_are_never_requested(self):
        urls = ["http://release-assets.githubusercontent.com/file", "https://evil.example/file",
                "https://release-assets.githubusercontent.com.evil.example/file",
                "https://api.github.com/repos/other/repository/releases/assets/123",
                "https://api.github.com/user", "https://user:password@release-assets.githubusercontent.com/file",
                "https://release-assets.githubusercontent.com:8443/file",
                "https://release-assets.githubusercontent.com/file#fragment"]
        for url in urls:
            with self.subTest(url=url):
                opener = Opener([(self.api_url, Response(status=302, response_headers=headers(Location=url)))])
                with self.assertRaises(UpdateError):
                    GitHubUpdateClient(TOKEN, opener=opener).download(self.info, self.directory)
                self.assertEqual(len(opener.requests), 1)
                self.assert_directory_clean()

    def test_truncated_oversized_and_hash_mismatched_bodies_are_discarded(self):
        for data, expected in [(DATA[:-1], "size_mismatch"), (DATA + b"x", "size_mismatch"), (b"x" * len(DATA), "hash_mismatch")]:
            with self.subTest(expected=expected):
                client, _ = self.direct_client(data)
                with self.assertRaises(UpdateError) as caught:
                    client.download(self.info, self.directory)
                self.assertEqual(caught.exception.code, expected)
                self.assert_directory_clean()

    def test_content_length_must_match_metadata(self):
        client, _ = self.direct_client(response_headers=headers(Content_Length=len(DATA) + 1))
        with self.assertRaises(UpdateError) as caught:
            client.download(self.info, self.directory)
        self.assertEqual(caught.exception.code, "size_mismatch")
        self.assert_directory_clean()

    def test_interrupted_stream_is_reported_safely_and_discarded(self):
        response = Response()
        response.read1 = lambda count: (_ for _ in ()).throw(IncompleteRead(TOKEN.encode(), 99))
        opener = Opener([(self.api_url, response)])
        with self.assertRaises(UpdateError) as caught:
            GitHubUpdateClient(TOKEN, opener=opener).download(self.info, self.directory)
        self.assertEqual(caught.exception.code, "download_failed")
        self.assertNotIn(TOKEN, str(caught.exception))
        self.assertTrue(response.closed)
        self.assert_directory_clean()

    def test_download_uses_available_read_and_keeps_legacy_transport_compatibility(self):
        response = Response(DATA)
        response.read = lambda size: self.fail("A buffered read delays cancellation")
        opener = Opener([(self.api_url, response)])
        path = GitHubUpdateClient(TOKEN, opener=opener).download(self.info, self.directory)
        self.assertEqual(path.read_bytes(), DATA)
        fallback = Response(DATA)
        fallback.read1 = None
        opener = Opener([(self.api_url, fallback)])
        second = GitHubUpdateClient(TOKEN, opener=opener).download(self.info, self.directory)
        self.assertEqual(second.read_bytes(), DATA)

    def test_existing_destination_is_preserved_and_new_file_published(self):
        original = self.directory / self.info.asset_name
        original.write_bytes(b"user's existing file")
        client, _ = self.direct_client()
        result = client.download(self.info, self.directory)
        self.assertNotEqual(original, result)
        self.assertEqual(original.read_bytes(), b"user's existing file")
        self.assertEqual(result.read_bytes(), DATA)
        self.assert_directory_clean([original, result])

    def test_existing_destination_created_during_publication_is_preserved(self):
        original = self.directory / self.info.asset_name
        actual_link = updates.os.link

        def race(source, target):
            if target == original:
                original.write_bytes(b"created concurrently")
            return actual_link(source, target)

        client, _ = self.direct_client()
        with patch.object(updates.os, "link", side_effect=race):
            result = client.download(self.info, self.directory)
        self.assertEqual(original.read_bytes(), b"created concurrently")
        self.assertEqual(result.read_bytes(), DATA)
        self.assertNotEqual(original, result)

    @unittest.skipUnless(os.name == "nt", "Windows-only exclusive rename fallback")
    def test_windows_filesystem_without_hardlinks_still_preserves_existing_file(self):
        original = self.directory / self.info.asset_name
        original.write_bytes(b"keep original")
        client, _ = self.direct_client()
        with patch.object(updates.os, "link", side_effect=OSError("hard links unsupported")):
            result = client.download(self.info, self.directory)
        self.assertEqual(original.read_bytes(), b"keep original")
        self.assertEqual(result.read_bytes(), DATA)
        self.assert_directory_clean([original, result])

    def test_cancellation_removes_only_owned_partial_file(self):
        existing = self.directory / self.info.asset_name
        existing.write_bytes(b"user file")
        unrelated = self.directory / ".unrelated.part"
        unrelated.write_bytes(b"keep")
        event = threading.Event()
        client, _ = self.direct_client()

        def cancel_after_chunk(done, total):
            if done:
                event.set()

        with self.assertRaises(UpdateCancelled):
            client.download(self.info, self.directory, cancel_after_chunk, event)
        self.assert_directory_clean([existing, unrelated])
        self.assertEqual(existing.read_bytes(), b"user file")
        self.assertEqual(unrelated.read_bytes(), b"keep")

    def test_forged_filenames_ids_and_digests_are_rejected_before_network(self):
        invalid = [replace(self.info, asset_name="../escape.exe"), replace(self.info, asset_id=True),
                   replace(self.info, sha256=""), replace(self.info, asset_size=updates._MAX_PACKAGE_BYTES + 1),
                   replace(self.info, tag="v9.0.0"), replace(self.info, version="v1.0.2")]
        for item in invalid:
            with self.subTest(item=item):
                opener = Opener([])
                with self.assertRaises(UpdateError) as caught:
                    GitHubUpdateClient(TOKEN, opener=opener).download(item, self.directory)
                self.assertEqual(caught.exception.code, "invalid_asset")
                self.assert_directory_clean()


if __name__ == "__main__":
    unittest.main()
