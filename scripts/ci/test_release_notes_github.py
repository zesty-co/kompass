import json
import io
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import release_notes_github as adapter


class RESTFixture:
    def __init__(self):
        self.objects = {}
        self.routes = {}
        self.calls = []
        self.posts = []
        self.received_headers = []
        self.corrupt_writes = False
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                fixture.calls.append(('GET', self.path))
                fixture.received_headers.append(dict(self.headers))
                status, body = fixture.routes.get(self.path, (200, fixture.objects.get(self.path)))
                if body is None:
                    status, body = 404, b'not found'
                if not isinstance(body, bytes):
                    body = json.dumps(body).encode()
                self.send_response(status)
                if status == 302:
                    self.send_header('Location', body.decode())
                self.end_headers()
                self.wfile.write(body)

            def do_PUT(self):
                fixture.calls.append(('PUT', self.path))
                fixture.objects[self.path] = self.rfile.read(int(self.headers['Content-Length']))
                if fixture.corrupt_writes:
                    fixture.objects[self.path] = b'corrupt'
                self.send_response(201)
                self.end_headers()

            def do_POST(self):
                data = self.rfile.read(int(self.headers.get('Content-Length', '0')))
                fixture.calls.append(('POST', self.path))
                fixture.posts.append((self.path, data))
                if self.path.endswith('/releases'):
                    release = json.loads(data)
                    release.update(id=1, upload_url=fixture.url + '/upload{?name,label}')
                    fixture.routes['/repos/owner/repo/releases/tags/' + release['tag_name']] = (200, release)
                    fixture.routes['/repos/owner/repo/releases/1/assets?per_page=100&page=1'] = (200, [])
                    body = json.dumps(release).encode()
                elif self.path.startswith('/upload?name='):
                    name = self.path.split('=', 1)[1]
                    route = '/repos/owner/repo/releases/1/assets?per_page=100&page=1'
                    assets = fixture.routes[route][1]
                    identity = 9 + len(assets)
                    fixture.objects['/repos/owner/repo/releases/assets/' + str(identity)] = data
                    assets.append({'id': identity, 'name': name})
                    body = b'{}'
                else:
                    body = b'{}'
                self.send_response(201)
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = 'http://127.0.0.1:%s' % self.server.server_port

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.fixture = RESTFixture()
        self.addCleanup(self.fixture.close)
        self.api = adapter.GitHub('owner/repo', 'token', self.fixture.url)

    def review(self, number, state='APPROVED', sha='head', user=42):
        return {'id': number, 'state': state, 'commit_id': sha, 'user': {'id': user}}

    def test_pagination_and_latest_effective_review(self):
        route = '/repos/owner/repo/pulls/7/reviews?per_page=100&page='
        self.fixture.routes[route + '1'] = (200, [self.review(i, user=i+100) for i in range(99)] + [self.review(100)])
        self.fixture.routes[route + '2'] = (200, [self.review(101, 'DISMISSED')])
        with self.assertRaisesRegex(ValueError, 'approval'):
            adapter.approval(self.api, 7, 'head', {42})
        self.fixture.routes[route + '2'] = (200, [self.review(101, 'COMMENTED')])
        self.assertEqual(adapter.approval(self.api, 7, 'head', {42})['id'], 100)

    def test_exact_head_and_numeric_allowlist(self):
        route = '/repos/owner/repo/pulls/7/reviews?per_page=100&page=1'
        for reviews, allowed in [([self.review(1, sha='old')], {42}),
                                 ([self.review(1, user=9)], {42}),
                                 ([self.review(1)], set()),
                                 ([self.review(1), self.review(2, 'CHANGES_REQUESTED')], {42})]:
            with self.subTest(reviews=reviews, allowed=allowed):
                self.fixture.routes[route] = (200, reviews)
                with self.assertRaises(ValueError):
                    adapter.approval(self.api, 7, 'head', allowed)
        for value in ['', 'alice', '42,alice', '0']:
            with self.assertRaises(ValueError):
                adapter.product_ids(value)
        self.assertEqual(adapter.product_ids('42, 73'), {42, 73})


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = RESTFixture()
        self.addCleanup(self.fixture.close)
        self.registry = adapter.Registry(self.fixture.url, '12', 'token')

    def test_immutable_write_readback_and_retry(self):
        self.registry.put('abc', 'package.tgz', b'first')
        self.registry.put('abc', 'package.tgz', b'first')
        self.assertEqual(self.registry.get('abc', 'package.tgz'), b'first')
        self.assertEqual(sum(method == 'PUT' for method, _ in self.fixture.calls), 1)
        with self.assertRaisesRegex(ValueError, 'conflict'):
            self.registry.put('abc', 'package.tgz', b'changed')

    def test_permission_errors_are_not_missing_artifacts(self):
        self.fixture.routes['/projects/12/packages/generic/release-notes/abc/receipt.json'] = (403, b'denied')
        with self.assertRaises(Exception):
            self.registry.get('abc', 'receipt.json', missing=True)

    def test_readback_corruption_blocks_freeze(self):
        self.fixture.corrupt_writes = True
        with self.assertRaisesRegex(ValueError, 'readback'):
            self.registry.put('abc', 'package.tgz', b'expected')

    def test_asset_redirect_does_not_leak_credentials(self):
        target = RESTFixture()
        self.addCleanup(target.close)
        target.objects['/asset'] = b'archive'
        self.fixture.routes['/redirect'] = (302, (target.url.replace('127.0.0.1', 'localhost') + '/asset').encode())
        data = adapter.request('GET', self.fixture.url + '/redirect', {'Authorization': 'Bearer secret'})
        self.assertEqual(data, b'archive')
        self.assertNotIn('Authorization', target.received_headers[-1])


class ArtifactTests(unittest.TestCase):
    def test_source_refresh_and_credential_free_preview(self):
        import release_notes as engine
        fixture = RESTFixture()
        self.addCleanup(fixture.close)
        registry = adapter.Registry(fixture.url, '12', 'token')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            charts = root / 'charts'
            chart = charts / 'kompass'
            chart.mkdir(parents=True)
            (chart / 'Chart.yaml').write_text('apiVersion: v2\nname: kompass\nversion: 1.0.0\n')
            inputs = {'schema_version': 1, 'source': {'spoke_sha': 'a' * 40, 'components': {}, 'rightsizing': 'v1'},
                      'baselines': {}, 'entries': [], 'changed_charts': ['kompass']}
            bundle = root / engine.promotion_id(inputs['source'])
            engine.generate(inputs, charts, bundle)
            adapter.prepare_review(bundle, charts, registry)
            first = json.loads((bundle / 'frozen.json').read_bytes())
            adapter.prepare_review(bundle, charts, registry)
            self.assertEqual(first, json.loads((bundle / 'frozen.json').read_bytes()))
            (chart / 'Chart.yaml').write_text('apiVersion: v2\nname: kompass\nversion: 1.0.1\n')
            engine.generate(inputs, charts, bundle)
            adapter.prepare_review(bundle, charts, registry)
            refreshed = json.loads((bundle / 'frozen.json').read_bytes())
            self.assertNotEqual(first['storage_key'], refreshed['storage_key'])
            self.assertEqual(len([call for call in fixture.calls if call[0] == 'PUT']), 2)
            env = {key: value for key, value in os.environ.items()
                   if key not in ('RELEASE_NOTES_RECOVERY_TOKEN', 'CI_JOB_TOKEN', 'RELEASE_NOTES_RECOVERY_PROJECT')}
            subprocess.run(['python3', adapter.__file__, 'prepare-review', '--preview', '--bundle', str(bundle),
                            '--charts', str(charts)], env=env, check=True, capture_output=True)
            preview = json.loads((bundle / 'frozen.json').read_bytes())
            self.assertTrue(preview['preview'])
            self.assertEqual(preview['storage_key'], refreshed['storage_key'])
            self.assertEqual(len([call for call in fixture.calls if call[0] == 'PUT']), 2)
            with self.assertRaisesRegex(ValueError, 'preview evidence'):
                adapter.payload(bundle, charts)

    def test_untrusted_archives_cannot_write_links_or_escape(self):
        for name, kind in [('../escaped', tarfile.REGTYPE), ('/absolute', tarfile.REGTYPE),
                           ('link', tarfile.SYMTYPE)]:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                data = io.BytesIO()
                with tarfile.open(fileobj=data, mode='w') as archive:
                    info = tarfile.TarInfo(name)
                    info.type = kind
                    info.linkname = '/etc/passwd'
                    archive.addfile(info)
                with self.assertRaises(ValueError):
                    adapter.extract(data.getvalue(), temporary)

    def test_changed_chart_without_bundle_is_not_unrelated(self):
        with self.assertRaisesRegex(ValueError, 'missing'):
            adapter.bundle_for_files('.', ['charts/kompass/Chart.yaml'])
        self.assertIsNone(adapter.bundle_for_files('.', ['docs/help.md']))

    def test_chart_plan_must_cover_actual_changed_charts(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary)
            subprocess.run(['git', 'init', str(repo)], check=True, capture_output=True)
            def git(*args):
                return subprocess.check_output(['git', '-C', str(repo), '-c', 'user.name=Fixture',
                                                '-c', 'user.email=fixture@example.invalid', *args], stderr=subprocess.DEVNULL).decode().strip()
            (repo / 'README.md').write_text('base')
            git('add', '.')
            git('commit', '-m', 'base')
            base = git('rev-parse', 'HEAD')
            (repo / 'charts/kompass').mkdir(parents=True)
            (repo / 'charts/kompass/Chart.yaml').write_text('version: 1.0.0')
            git('add', '.')
            git('commit', '-m', 'chart')
            files = [{'filename': 'charts/kompass/Chart.yaml'}]
            with self.assertRaisesRegex(ValueError, 'chart set'):
                adapter.validate_chart_plan(repo, {'changed_files': 1}, files,
                                            {'public_base_sha': base, 'charts': []}, git('rev-parse', 'HEAD'))

    def test_offline_packages_include_filtered_notes_in_nested_children(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            charts, notes, packages = root / 'charts', root / 'notes', root / 'packages'
            for name in ('kompass', 'kompass-insights'):
                (charts / name).mkdir(parents=True)
                (charts / name / 'Chart.yaml').write_text('apiVersion: v2\nname: %s\nversion: 1.0.0\n' % name)
                (notes / name).mkdir(parents=True)
                (notes / name / 'RELEASE_NOTES.md').write_text('Approved ' + name)
            (charts / 'kompass' / 'charts').mkdir()
            data = io.BytesIO()
            with tarfile.open(fileobj=data, mode='w:gz') as archive:
                archive.add(charts / 'kompass-insights', arcname='kompass-insights')
            (charts / 'kompass/charts/kompass-insights-1.0.0.tgz').write_bytes(data.getvalue())
            adapter.package_frozen(charts, notes, packages)
            with tarfile.open(packages / 'kompass-1.0.0.tgz') as archive:
                names = archive.getnames()
                self.assertIn('kompass/RELEASE_NOTES.md', names)
                # Helm expands dependencies into the parent archive.
                child = archive.extractfile('kompass/charts/kompass-insights/RELEASE_NOTES.md').read()
                self.assertEqual(child, b'Approved kompass-insights')
            (charts / 'kompass' / '.helmignore').write_text('RELEASE_NOTES.md\n')
            with self.assertRaisesRegex(ValueError, 'packaged release notes'):
                adapter.package_frozen(charts, notes, root / 'ignored-packages')


class PublicationTests(unittest.TestCase):
    def test_release_asset_repair_is_exact_and_idempotent(self):
        fixture = RESTFixture()
        self.addCleanup(fixture.close)
        api = adapter.GitHub('owner/repo', 'token', fixture.url)
        chart = {'name': 'kompass', 'version': '1.0.0', 'notes': 'Customer text',
                 'package_sha256': adapter.sha(b'package')}
        adapter.publish_release(api, chart, 'merged-sha', b'package')
        adapter.publish_release(api, chart, 'merged-sha', b'package')
        self.assertEqual(sum(method == 'POST' for method, _ in fixture.calls), 2)
        fixture.objects['/repos/owner/repo/releases/assets/9'] = b'foreign bytes'
        with self.assertRaisesRegex(ValueError, 'asset'):
            adapter.publish_release(api, chart, 'merged-sha', b'package')

    def test_wrong_package_is_rejected_before_public_write(self):
        fixture = RESTFixture()
        self.addCleanup(fixture.close)
        api = adapter.GitHub('owner/repo', 'token', fixture.url)
        chart = {'name': 'kompass', 'version': '1.0.0', 'notes': 'Customer text',
                 'package_sha256': adapter.sha(b'approved')}
        with self.assertRaises(ValueError):
            adapter.publish_release(api, chart, 'merged-sha', b'wrong')
        self.assertEqual(fixture.calls, [])

    def test_index_failure_recovers_frozen_bytes_without_new_approval(self):
        import release_notes as engine
        fixture = RESTFixture()
        self.addCleanup(fixture.close)
        api = adapter.GitHub('owner/repo', 'token', fixture.url)
        registry = adapter.Registry(fixture.url, '12', 'token')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            remote, repo = root / 'remote.git', root / 'repo'
            subprocess.run(['git', 'init', '--bare', str(remote)], check=True, capture_output=True)
            subprocess.run(['git', 'clone', str(remote), str(repo)], check=True, capture_output=True)

            def git(*args):
                return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.DEVNULL).decode().strip()

            git('config', 'user.email', 'fixture@example.invalid')
            git('config', 'user.name', 'Fixture')
            chart = repo / 'charts/kompass'
            chart.mkdir(parents=True)
            (chart / 'Chart.yaml').write_text('apiVersion: v2\nname: kompass\nversion: 1.0.0\n')
            git('add', '.')
            git('commit', '-m', 'base')
            git('push', 'origin', 'HEAD:refs/heads/main', 'HEAD:refs/heads/gh-pages')
            base = git('rev-parse', 'HEAD')
            (chart / 'values.yaml').write_text('feature: true\n')
            inputs = {'schema_version': 1, 'source': {'spoke_sha': 'a' * 40, 'components': {}, 'rightsizing': 'v1'},
                      'baselines': {}, 'entries': [], 'changed_charts': ['kompass'], 'public_base_sha': base}
            promotion = engine.promotion_id(inputs['source'])
            bundle = repo / 'release-notes' / promotion
            engine.generate(inputs, repo / 'charts', bundle)
            state = adapter.run('python3', str(Path(adapter.__file__).with_name('release_notes_lifecycle.py')),
                                '--repo', str(repo), 'acquire', '--promotion', promotion)
            (bundle / 'lifecycle.json').write_bytes(state)
            adapter.prepare_review(bundle, repo / 'charts', registry)
            git('add', '.')
            git('commit', '-m', 'reviewed')
            head = git('rev-parse', 'HEAD')
            git('push', 'origin', 'HEAD:refs/pull/7/head')
            git('commit', '--allow-empty', '-m', 'squash merge')
            merged = git('rev-parse', 'HEAD')
            git('push', 'origin', 'HEAD:refs/heads/main')
            fixture.routes['/repos/owner/repo/commits/' + merged + '/pulls?per_page=100&page=1'] = (200, [{'number': 7, 'merged_at': 'now'}])
            fixture.routes['/repos/owner/repo/pulls?state=closed&sort=updated&direction=desc&per_page=100&page=1'] = (200, [{'number': 7, 'merged_at': 'now', 'merge_commit_sha': merged}])
            fixture.routes['/repos/owner/repo/pulls/7'] = (200, {'number': 7, 'merge_commit_sha': merged, 'head': {'sha': head}})
            fixture.routes['/repos/owner/repo/pulls/7/files?per_page=100&page=1'] = (200, [
                {'filename': 'charts/kompass/values.yaml'},
                {'filename': 'release-notes/' + promotion + '/manifest.json'}])
            review_route = '/repos/owner/repo/pulls/7/reviews?per_page=100&page=1'
            fixture.routes[review_route] = (200, [{'id': 1, 'state': 'APPROVED', 'commit_id': head, 'user': {'id': 42}}])
            with self.assertRaisesRegex(ValueError, 'PRODUCT_IDS'):
                adapter.check_review(api, repo, 7, '')
            self.assertEqual(json.loads(fixture.posts[-1][1])['state'], 'failure')
            adapter.check_review(api, repo, 7, {42})
            self.assertEqual(json.loads(fixture.posts[-1][1])['state'], 'success')
            fixture.routes['/repos/owner/repo/releases?per_page=100&page=1'] = (200, [])
            tools = root / 'tools'
            tools.mkdir()
            cr = tools / 'cr'
            cr.write_text('#!/bin/sh\nexit 17\n')
            cr.chmod(0o755)
            git('commit', '--allow-empty', '-m', 'later docs update')
            with patch.dict(os.environ, {'PATH': str(tools) + os.pathsep + os.environ['PATH'],
                                         'RELEASE_NOTES_INDEX_URL': fixture.url + '/index.yaml'}):
                with self.assertRaises(subprocess.CalledProcessError):
                    adapter.recover(api, registry, repo, promotion, {42})
                self.assertIsNone(registry.get(promotion, 'receipt.json', missing=True))
                authorization = registry.get(promotion, 'authorization.json')
                with self.assertRaisesRegex(ValueError, 'recover'):
                    adapter.cancel(repo, registry, promotion)
                public_bytes = fixture.objects['/repos/owner/repo/releases/assets/9']
                index = {'entries': {'kompass': [{'version': '1.0.0', 'digest': adapter.sha(public_bytes),
                                                 'urls': ['https://github.com/owner/repo/releases/download/kompass-1.0.0/kompass-1.0.0.tgz']}]}}
                fixture.routes['/index.yaml'] = (200, index)
                fixture.routes[review_route] = (403, b'reviews unavailable on retry')
                cr.write_text('#!/bin/sh\nexit 0\n')
                adapter.publish(api, registry, repo, promotion, {42})
                self.assertEqual(registry.get(promotion, 'authorization.json'), authorization)
                self.assertEqual(fixture.objects['/repos/owner/repo/releases/assets/9'], public_bytes)
                receipt = json.loads(registry.get(promotion, 'receipt.json'))
                self.assertEqual(receipt['charts'][0]['package_sha256'], adapter.sha(public_bytes))
                public_receipt = json.loads(fixture.objects['/repos/owner/repo/releases/assets/10'])
                self.assertEqual(public_receipt['chart'], 'kompass')
                self.assertEqual(public_receipt['package_sha256'], adapter.sha(public_bytes))
                self.assertEqual(public_receipt['source'], inputs['source'])
                with tarfile.open(fileobj=io.BytesIO(public_bytes)) as archive:
                    note_bytes = archive.extractfile('kompass/RELEASE_NOTES.md').read()
                self.assertEqual(public_receipt['notes_sha256'], adapter.sha(note_bytes))
                self.assertEqual(public_receipt['authorization_id'], adapter.sha(authorization))
                self.assertEqual(adapter.lifecycle(repo, bundle, 'status')['status'], 'complete')
                fixture.routes['/index.yaml'] = (200, {'entries': {}})
                with self.assertRaisesRegex(ValueError, 'index'):
                    adapter.publish(api, registry, repo, promotion, {42})
                fixture.routes['/index.yaml'] = (200, index)
                adapter.publish(api, registry, repo, promotion, {42})
                (chart / 'values.yaml').write_text('newer: true\n')
                git('add', '.')
                git('commit', '-m', 'later change')
                adapter.recover(api, registry, repo, promotion, {42})
                self.assertEqual((chart / 'values.yaml').read_text(), 'newer: true\n')


class BaselineTests(unittest.TestCase):
    def test_incomplete_release_is_ignored_but_verified_newer_release_blocks(self):
        import release_notes as engine
        fixture = RESTFixture()
        self.addCleanup(fixture.close)
        api = adapter.GitHub('owner/repo', 'token', fixture.url)
        registry = adapter.Registry(fixture.url, '12', 'token')
        index_url = fixture.url + '/index.yaml'
        index = {'entries': {'kompass': []}}
        releases = []

        def release(number, version, notes=None):
            tag = 'kompass-' + version
            output = io.BytesIO()
            files = {'Chart.yaml': json.dumps({'apiVersion': 'v2', 'name': 'kompass', 'version': version}).encode()}
            if notes is not None:
                files['RELEASE_NOTES.md'] = notes.encode()
            with tarfile.open(fileobj=output, mode='w:gz') as archive:
                for name, data in files.items():
                    info = tarfile.TarInfo('kompass/' + name)
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
            data = output.getvalue()
            asset_url = fixture.url + '/download/' + tag + '.tgz'
            assets = [{'id': number, 'name': tag + '.tgz', 'browser_download_url': asset_url}]
            fixture.objects['/repos/owner/repo/releases/assets/' + str(number)] = data
            fixture.routes['/repos/owner/repo/releases/%s/assets?per_page=100&page=1' % number] = (200, assets)
            index['entries']['kompass'].append({'version': version, 'digest': adapter.sha(data), 'urls': [asset_url]})
            releases.append({'id': number, 'tag_name': tag, 'draft': False, 'prerelease': False,
                             'published_at': '2026-01-%02d' % number, 'body': notes or ''})
            return adapter.sha(data), assets

        old_digest, _ = release(1, '1.0.0')
        new_digest, assets = release(2, '1.1.0', 'Approved notes')
        fixture.routes['/repos/owner/repo/releases?per_page=100&page=1'] = (200, releases)
        fixture.routes['/index.yaml'] = (200, index)
        baseline = {'version': '1.0.0', 'status': 'verified', 'digest': old_digest}
        manifest = {'charts': [{'name': 'kompass', 'version': '1.2.0', 'previous_version': '1.0.0'}],
                    'baselines': {'kompass': baseline}}
        with patch.dict(os.environ, {'RELEASE_NOTES_INDEX_URL': index_url}):
            adapter.check_baselines(api, registry, manifest, False)
            index['entries']['kompass'][0]['digest'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'checksum'):
                adapter.check_baselines(api, registry, manifest, False)
            index['entries']['kompass'][0]['digest'] = old_digest
            baseline['digest'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'baseline'):
                adapter.check_baselines(api, registry, manifest, False)
            baseline['digest'] = old_digest
            source = {'spoke_sha': 'a' * 40, 'components': {}, 'rightsizing': 'v1'}
            receipt = {'schema_version': 1, 'chart': 'kompass', 'version': '1.1.0',
                       'promotion_id': engine.promotion_id(source), 'authorization_id': 'b' * 64,
                       'package_sha256': new_digest, 'notes_sha256': adapter.sha(b'Approved notes'),
                       'source': source, 'manifest_digest': 'c' * 64, 'index_url': index_url,
                       'predecessor': 'kompass-1.0.0'}
            assets.append({'id': 20, 'name': 'release-notes-receipt.json'})
            fixture.objects['/repos/owner/repo/releases/assets/20'] = adapter.canonical(receipt)
            with self.assertRaisesRegex(ValueError, 'baseline moved'):
                adapter.check_baselines(api, registry, manifest, False)


if __name__ == '__main__':
    unittest.main()
