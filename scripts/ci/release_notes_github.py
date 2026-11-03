#!/usr/bin/env python3
"""Trusted review and publication adapter. No PR code is executed."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request


CHECK = 'Release Notes / Product Review'


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def sha(data):
    return hashlib.sha256(data).hexdigest()


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        old, new = urllib.parse.urlparse(req.full_url), urllib.parse.urlparse(newurl)
        if old.scheme == 'https' and new.scheme != 'https':
            raise ValueError('Refusing HTTPS downgrade')
        if redirected is not None and (old.scheme, old.netloc) != (new.scheme, new.netloc):
            for header in ('Authorization', 'Deploy-token', 'Job-token', 'Private-token'):
                redirected.remove_header(header)
        return redirected


def request(method, url, headers, data=None, missing=False):
    try:
        opener = urllib.request.build_opener(SafeRedirect())
        with opener.open(urllib.request.Request(url, data=data, headers=headers, method=method), timeout=120) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        if missing and error.code == 404:
            return None
        raise


class GitHub:
    def __init__(self, repository, token, base='https://api.github.com'):
        self.base = base.rstrip('/') + '/repos/' + repository
        self.headers = {'Authorization': 'Bearer ' + token, 'Accept': 'application/vnd.github+json',
                        'X-GitHub-Api-Version': '2022-11-28'}

    def call(self, method, path, value=None, missing=False):
        data = request(method, self.base + path, self.headers,
                       canonical(value) if value is not None else None, missing)
        return json.loads(data) if data else None

    def pages(self, path):
        page = 1
        while True:
            batch = self.call('GET', path + ('&' if '?' in path else '?') + 'per_page=100&page=' + str(page))
            yield from batch
            if len(batch) < 100:
                return
            page += 1

    def status(self, head, state, description):
        self.call('POST', '/statuses/' + head, {'state': state, 'context': CHECK, 'description': description[:140]})


def product_ids(value):
    values = re.split(r'[,\s]+', value.strip())
    if not values or any(not re.fullmatch(r'[1-9][0-9]*', item) for item in values):
        raise ValueError('RELEASE_NOTES_PRODUCT_IDS must contain trusted numeric IDs')
    return {int(item) for item in values}


def approval(api, pr, head, allowed):
    if not allowed:
        raise ValueError('No trusted Product IDs configured')
    latest = {}
    for review in sorted(api.pages('/pulls/%s/reviews' % pr), key=lambda item: item['id']):
        user = (review.get('user') or {}).get('id')
        if user in allowed and review['state'] in ('APPROVED', 'CHANGES_REQUESTED', 'DISMISSED'):
            latest[user] = review
    valid = [item for item in latest.values() if item['state'] == 'APPROVED' and item['commit_id'] == head]
    if not valid:
        raise ValueError('Product approval of the exact PR head is required')
    return max(valid, key=lambda item: item['id'])


class Registry:
    def __init__(self, base, project, token, job_token=False):
        self.base = base.rstrip('/') + '/projects/' + project + '/packages/generic/release-notes/'
        self.headers = {'JOB-TOKEN' if job_token else 'DEPLOY-TOKEN': token}

    def url(self, promotion, name):
        return self.base + urllib.parse.quote(promotion, safe='') + '/' + urllib.parse.quote(name, safe='')

    def get(self, promotion, name, missing=False):
        return request('GET', self.url(promotion, name), self.headers, missing=missing)

    def put(self, promotion, name, data):
        previous = self.get(promotion, name, missing=True)
        if previous is not None:
            if previous != data:
                raise ValueError('Recovery artifact conflict: ' + name)
            return
        request('PUT', self.url(promotion, name), self.headers, data)
        if self.get(promotion, name) != data:
            raise ValueError('Recovery readback checksum mismatch: ' + name)


def registry_env():
    token = os.environ.get('RELEASE_NOTES_RECOVERY_TOKEN')
    return Registry(os.environ.get('CI_API_V4_URL', 'https://gitlab.com/api/v4'),
                    os.environ['RELEASE_NOTES_RECOVERY_PROJECT'], token or os.environ['CI_JOB_TOKEN'], not bool(token))


def run(*args, **kwargs):
    return subprocess.check_output(args, **kwargs)


def extract(data, destination):
    """Extract only ordinary files/directories, never links or paths outside the root."""
    destination = Path(destination)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for member in archive.getmembers():
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                raise ValueError('Unsafe archive member: ' + member.name)
            target = destination / path
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
                target.chmod(0o755 if member.mode & 0o100 else 0o644)


def snapshot(repo, ref, destination):
    extract(run('git', '-C', str(repo), 'archive', ref), destination)


def bundle_for_files(root, files):
    promotions = set()
    chart_change = False
    for item in files:
        path = item['filename'] if isinstance(item, dict) else item
        chart_change |= path.startswith('charts/') or (isinstance(item, dict) and item.get('previous_filename', '').startswith('charts/'))
        match = re.match(r'^release-notes/([0-9a-f]{64})/', path)
        if match:
            promotions.add(match[1])
    if not promotions:
        if chart_change:
            raise ValueError('Chart promotion is missing its release-notes bundle')
        return None
    if len(promotions) != 1:
        raise ValueError('Exactly one promotion bundle is required')
    return Path(root) / 'release-notes' / promotions.pop()


def validate_chart_plan(repo, pr, files, manifest, head):
    if pr.get('changed_files', len(files)) > 3000:
        raise ValueError('GitHub PR files limit exceeded; cannot prove chart coverage')
    base = manifest.get('public_base_sha', '')
    if not re.fullmatch(r'[0-9a-f]{40,64}', base):
        raise ValueError('Approved public_base_sha is required')
    run('git', '-C', str(repo), 'merge-base', '--is-ancestor', base, head)
    changed = run('git', '-C', str(repo), 'diff', '--no-renames', '--name-only', base, head, '--', 'charts').decode().splitlines()
    api_paths = [path for item in files for path in (item['filename'], item.get('previous_filename', ''))]
    def names(paths):
        return {parts[1] for path in paths if len(parts := path.split('/')) >= 3 and parts[0] == 'charts'}
    expected = names(changed)
    if expected != names(api_paths) or expected != {chart['name'] for chart in manifest['charts']}:
        raise ValueError('Manifest chart set does not match the actual PR chart set')


def payload(bundle, charts, require_review=True):
    import release_notes as engine
    engine.validate(bundle, require_review=require_review)
    manifest = json.loads((bundle / 'manifest.json').read_text())
    if bundle.name != manifest['promotion_id']:
        raise ValueError('Promotion directory does not match manifest')
    for chart in manifest['charts']:
        if engine.chart_digest(Path(charts) / chart['name']) != chart['runtime_digest']:
            raise ValueError('Runtime changed: ' + chart['name'])
    frozen = json.loads((bundle / 'frozen.json').read_text())
    if frozen.get('schema_version') != 1 or not re.fullmatch(r'[0-9a-f]{64}', frozen.get('source_sha256', '')):
        raise ValueError('Invalid frozen source record')
    if frozen.get('preview') or not re.fullmatch(r'sources-[0-9a-f]{64}', frozen.get('storage_key', '')):
        raise ValueError('Publication requires persisted source evidence, not preview evidence')
    runtimes = {path.name: engine.chart_digest(path) for path in Path(charts).iterdir() if (path / 'Chart.yaml').is_file()}
    if frozen.get('runtime_digests') != runtimes:
        raise ValueError('Frozen source chart set changed')
    state = json.loads((bundle / 'lifecycle.json').read_text())
    if state.get('promotion_id') != bundle.name or type(state.get('generation')) is not int or state['generation'] < 1:
        raise ValueError('Invalid lifecycle generation')
    metadata = {}
    for name in ('manifest.json', 'entries.json', 'review.yaml', 'frozen.json', 'lifecycle.json'):
        metadata[name] = sha((bundle / name).read_bytes())
    return manifest, sha(canonical(metadata))


def lifecycle(repo, bundle, action):
    state = json.loads((bundle / 'lifecycle.json').read_text())
    return json.loads(run('python3', str(Path(__file__).with_name('release_notes_lifecycle.py')),
                         '--repo', str(repo), action, '--promotion', bundle.name,
                         '--generation', str(state['generation'])))


def check_review(api, repo, pr_number, allowed):
    pr = api.call('GET', '/pulls/' + str(pr_number))
    head = pr['head']['sha']
    api.status(head, 'pending', 'Validate classification and exact-head Product approval')
    try:
        files = list(api.pages('/pulls/%s/files' % pr_number))
        run('git', '-C', str(repo), 'fetch', 'origin', 'pull/%s/head' % pr_number)
        if run('git', '-C', str(repo), 'rev-parse', 'FETCH_HEAD').decode().strip() != head:
            raise ValueError('PR head moved; retry review check')
        with tempfile.TemporaryDirectory() as temporary:
            snapshot(repo, head, temporary)
            bundle = bundle_for_files(temporary, files)
            if bundle:
                manifest, _ = payload(bundle, Path(temporary) / 'charts')
                validate_chart_plan(repo, pr, files, manifest, head)
                lifecycle(repo, bundle, 'check')
                approval(api, pr_number, head, product_ids(allowed) if isinstance(allowed, str) else allowed)
        if api.call('GET', '/pulls/' + str(pr_number))['head']['sha'] != head:
            raise ValueError('PR head moved; retry review check')
        api.status(head, 'success', 'Product review verified' if bundle else 'No chart promotion')
    except Exception:
        api.status(head, 'failure', 'Release notes or exact-head Product approval missing; see job log')
        raise


def prepare_review(bundle, charts, registry=None):
    import release_notes as engine
    engine.validate(bundle)
    runtimes = {path.name: engine.chart_digest(path) for path in Path(charts).iterdir() if (path / 'Chart.yaml').is_file()}
    policy = {'schema_version': 1, 'runtime_digests': runtimes,
              'preparation_sha256': sha(Path(__file__).with_name('prepare-charts.sh').read_bytes())}
    storage_key = 'sources-' + sha(canonical(policy))
    record = {'schema_version': 1, 'storage_key': storage_key, 'runtime_digests': runtimes,
              'preview': registry is None}
    existing = registry.get(storage_key, 'sources.tar', missing=True) if registry else None
    if existing is not None:
        with tarfile.open(fileobj=io.BytesIO(existing)) as archive:
            recorded = json.loads(archive.extractfile('source-runtime.json').read())
        if recorded != runtimes:
            raise ValueError('Frozen source conflicts with current charts')
        (bundle / 'frozen.json').write_bytes(canonical(dict(record, source_sha256=sha(existing))))
        return
    with tempfile.TemporaryDirectory() as temporary:
        prepared = Path(temporary) / 'charts'
        env = dict(os.environ, CHARTS_DIR=str(Path(charts).resolve()))
        run('sh', str(Path(__file__).with_name('prepare-charts.sh')), str(prepared), env=env)
        output = io.BytesIO()
        with tarfile.open(fileobj=output, mode='w') as archive:
            metadata = canonical(runtimes)
            info = tarfile.TarInfo('source-runtime.json')
            info.size = len(metadata)
            archive.addfile(info, io.BytesIO(metadata))
            for path in sorted(prepared.rglob('*')):
                if path.is_symlink():
                    raise ValueError('Symlink in prepared charts')
                if path.is_file():
                    info = archive.gettarinfo(str(path), str(path.relative_to(prepared)))
                    info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, '', ''
                    archive.addfile(info, io.BytesIO(path.read_bytes()))
        data = output.getvalue()
        if registry:
            registry.put(storage_key, 'sources.tar', data)
        (bundle / 'frozen.json').write_bytes(canonical(dict(record, source_sha256=sha(data))))


def package_frozen(charts, notes, destination):
    """Package without network resolution; replace local children before each parent."""
    destination.mkdir(parents=True, exist_ok=True)
    local = {path.name: path for path in charts.iterdir() if (path / 'Chart.yaml').is_file()}
    packaged, visiting = {}, set()

    def build(name):
        if name in packaged:
            return packaged[name]
        if name in visiting:
            raise ValueError('Local dependency cycle')
        visiting.add(name)
        chart = local[name]
        note = notes / name / 'RELEASE_NOTES.md'
        if note.exists():
            shutil.copyfile(note, chart / 'RELEASE_NOTES.md')
        for dependency in sorted((chart / 'charts').glob('*.tgz')):
            with tarfile.open(dependency) as archive:
                members = archive.getmembers()
                child = members[0].name.split('/')[0] if members else ''
            if child in local:
                replacement = build(child)
                if dependency.name != replacement.name:
                    raise ValueError('Frozen local dependency version mismatch')
                shutil.copyfile(replacement, dependency)
        metadata = json.loads(run('yq', '-o=json', '.', str(chart / 'Chart.yaml')))
        run('helm', 'package', str(chart), '--destination', str(destination))
        result = destination / (metadata['name'] + '-' + str(metadata['version']) + '.tgz')
        if not result.is_file():
            raise ValueError('Helm did not produce the expected package')
        if note.exists():
            with tarfile.open(result) as archive:
                try:
                    packaged_note = archive.extractfile(name + '/RELEASE_NOTES.md')
                except KeyError:
                    packaged_note = None
                if packaged_note is None or packaged_note.read() != note.read_bytes():
                    raise ValueError('Missing or changed packaged release notes: ' + name)
        packaged[name] = result
        visiting.remove(name)
        return result

    for name in sorted(local):
        build(name)
    return packaged


def publish_release(api, chart, merged_sha, data):
    if sha(data) != chart['package_sha256']:
        raise ValueError('Frozen package checksum mismatch')
    tag = chart['name'] + '-' + chart['version']
    release = api.call('GET', '/releases/tags/' + urllib.parse.quote(tag, safe=''), missing=True)
    if release is None:
        release = api.call('POST', '/releases', {'tag_name': tag, 'target_commitish': merged_sha,
                                               'name': tag, 'body': chart['notes'], 'draft': False,
                                               'prerelease': False})
    if release['body'] != chart['notes'] or release['target_commitish'] != merged_sha or release.get('draft'):
        raise ValueError('Existing release conflicts with authorization: ' + tag)
    publish_asset(api, release, tag + '.tgz', data)
    return release


def publish_asset(api, release, filename, data):
    assets = [item for item in api.pages('/releases/%s/assets' % release['id']) if item['name'] == filename]
    if len(assets) > 1:
        raise ValueError('Duplicate public asset: ' + filename)
    headers = dict(api.headers, Accept='application/octet-stream')
    if assets:
        existing = request('GET', api.base + '/releases/assets/' + str(assets[0]['id']), headers)
        if existing != data:
            raise ValueError('Existing public asset conflicts: ' + filename)
    else:
        upload = release['upload_url'].split('{', 1)[0]
        parsed = urllib.parse.urlparse(upload)
        if parsed.netloc not in (urllib.parse.urlparse(api.base).netloc, 'uploads.github.com'):
            raise ValueError('Unexpected GitHub upload host')
        headers['Content-Type'] = 'application/json' if filename.endswith('.json') else 'application/gzip'
        request('POST', upload + '?name=' + urllib.parse.quote(filename, safe=''), headers, data)
        assets = [item for item in api.pages('/releases/%s/assets' % release['id']) if item['name'] == filename]
        if len(assets) != 1 or request('GET', api.base + '/releases/assets/' + str(assets[0]['id']), headers) != data:
            raise ValueError('Public asset readback mismatch')


def check_baselines(api, registry, manifest, recovering):
    releases = list(api.pages('/releases'))
    index_url = os.environ.get('RELEASE_NOTES_INDEX_URL') or 'https://%s.github.io/%s/index.yaml' % tuple(api.base.rsplit('/', 2)[-2:])
    index = None
    for chart in manifest['charts']:
        name, previous = chart['name'], chart['previous_version']
        candidates = [item for item in releases if not item.get('draft') and not item.get('prerelease') and
                      re.fullmatch(re.escape(name) + r'-v?\d+\.\d+\.\d+(?:[-+].*)?', item['tag_name'])]
        if candidates and index is None:
            index = parse_yaml(request('GET', index_url, {'Cache-Control': 'no-cache'}))
            if not isinstance(index, dict) or not isinstance(index.get('entries'), dict):
                raise ValueError('Malformed published index')
        completed = []
        for candidate in sorted(candidates, key=lambda item: (item['published_at'], item['tag_name']), reverse=True):
            verified = verify_baseline_release(api, candidate, name, index, index_url)
            if verified is not None:
                completed.append(verified)
        latest = completed[0]['release_tag'] if completed else None
        permitted = {name + '-' + previous if previous else None}
        if recovering:
            permitted.add(name + '-' + chart['version'])
        if latest not in permitted:
            raise ValueError('Published baseline moved: ' + name)
        baseline = manifest['baselines'].get(name)
        if previous:
            matching = [item for item in completed if item['version'] == previous]
            if (not isinstance(baseline, dict) or baseline.get('status') != 'verified' or len(matching) != 1
                    or baseline.get('digest') != matching[0]['digest']):
                raise ValueError('Published baseline package evidence mismatch: ' + name)
            if baseline.get('receipt') != matching[0].get('receipt'):
                raise ValueError('Published baseline receipt mismatch: ' + name)


def parse_yaml(data):
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return json.loads(run('yq', '-o=json', '.', '-', input=data))


def verify_baseline_release(api, release, name, index, index_url):
    """Ignore incomplete releases, but fail on contradictory published evidence."""
    version = release['tag_name'][len(name) + 1:]
    entries = [item for item in index['entries'].get(name, []) if str(item.get('version')) == version]
    assets = list(api.pages('/releases/%s/assets' % release['id']))
    packages = [item for item in assets if item['name'] == release['tag_name'] + '.tgz']
    if not entries or not packages:
        return None
    if len(entries) != 1 or len(packages) != 1 or packages[0]['browser_download_url'] not in entries[0].get('urls', []):
        raise ValueError('Ambiguous or conflicting baseline package URL')
    headers = dict(api.headers, Accept='application/octet-stream')
    data = request('GET', api.base + '/releases/assets/' + str(packages[0]['id']), headers)
    if sha(data) != str(entries[0].get('digest', '')).removeprefix('sha256:'):
        raise ValueError('Published baseline package checksum mismatch')
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        files = {}
        for member in archive.getmembers():
            path = Path(member.name)
            if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
                raise ValueError('Unsafe baseline archive')
            if member.name in (name + '/Chart.yaml', name + '/RELEASE_NOTES.md') and member.isfile():
                if member.name in files:
                    raise ValueError('Duplicate baseline archive member')
                files[member.name] = archive.extractfile(member).read()
    metadata = parse_yaml(files[name + '/Chart.yaml'])
    if metadata.get('name') != name or str(metadata.get('version')) != version:
        raise ValueError('Published baseline chart metadata mismatch')
    notes = files.get(name + '/RELEASE_NOTES.md')
    receipts = [asset for asset in assets if asset['name'] == 'release-notes-receipt.json']
    if notes is not None and not receipts:
        return None
    result = {'version': version, 'release_tag': release['tag_name'], 'digest': sha(data)}
    if receipts:
        if len(receipts) != 1:
            raise ValueError('Ambiguous baseline receipt')
        receipt = json.loads(request('GET', api.base + '/releases/assets/' + str(receipts[0]['id']), headers))
        required = {'schema_version', 'chart', 'version', 'promotion_id', 'authorization_id', 'package_sha256',
                    'notes_sha256', 'source', 'manifest_digest', 'index_url', 'predecessor'}
        if (not isinstance(receipt, dict) or not required <= receipt.keys() or receipt['schema_version'] != 1
                or receipt['chart'] != name or receipt['version'] != version or receipt['package_sha256'] != sha(data)
                or receipt['index_url'] != index_url or notes is None or not isinstance(release.get('body'), str)
                or receipt['notes_sha256'] != sha(notes) or receipt['notes_sha256'] != sha(release['body'].encode())):
            raise ValueError('Published baseline receipt does not match package, notes, or index')
        import release_notes as engine
        if engine.promotion_id(receipt['source']) != receipt['promotion_id']:
            raise ValueError('Published baseline receipt source mismatch')
        result['receipt'] = receipt
    return result


def authorize(api, repo, bundle, manifest, fingerprint, allowed):
    merged_sha = run('git', '-C', str(repo), 'rev-parse', 'HEAD').decode().strip()
    prs = [pr for pr in api.pages('/commits/' + merged_sha + '/pulls') if pr.get('merged_at')]
    matched = []
    for candidate in prs:
        pr = api.call('GET', '/pulls/' + str(candidate['number']))
        if pr.get('merge_commit_sha') != merged_sha:
            continue
        head = pr['head']['sha']
        run('git', '-C', str(repo), 'fetch', 'origin', 'pull/%s/head' % pr['number'])
        if run('git', '-C', str(repo), 'rev-parse', 'FETCH_HEAD').decode().strip() != head:
            raise ValueError('Merged PR head changed')
        with tempfile.TemporaryDirectory() as temporary:
            snapshot(repo, head, temporary)
            reviewed = Path(temporary) / 'release-notes' / bundle.name
            _, approved_fingerprint = payload(reviewed, Path(temporary) / 'charts')
            validate_chart_plan(repo, pr, list(api.pages('/pulls/%s/files' % pr['number'])), manifest, head)
            if approved_fingerprint != fingerprint:
                raise ValueError('Merged payload differs from reviewed head')
            # All chart source trees, not just changed charts, must match the approved head.
            import release_notes as engine
            for chart in (repo / 'charts').iterdir():
                if (chart / 'Chart.yaml').is_file() and engine.chart_digest(chart) != engine.chart_digest(Path(temporary) / 'charts' / chart.name):
                    raise ValueError('Merged chart tree differs from reviewed head')
        review = approval(api, pr['number'], head, allowed)
        matched.append({'pr': pr['number'], 'head_sha': head, 'review_id': review['id'],
                        'reviewer_id': review['user']['id'], 'merged_sha': merged_sha})
    if len(matched) != 1:
        raise ValueError('Exactly one approved merged promotion PR is required')
    return matched[0]


def publish(api, registry, repo, promotion, allowed):
    import release_notes as engine
    if promotion:
        if not re.fullmatch(r'[0-9a-f]{64}', promotion):
            raise ValueError('Invalid promotion ID')
        bundle = repo / 'release-notes' / promotion
    else:
        changed = run('git', '-C', str(repo), 'diff-tree', '--root', '--first-parent', '-m', '--no-commit-id', '--name-only', '-r', 'HEAD').decode().splitlines()
        bundle = bundle_for_files(repo, changed)
        if bundle is None:
            return
    manifest, fingerprint = payload(bundle, repo / 'charts')
    generation = json.loads((bundle / 'lifecycle.json').read_text())['generation']
    stored = registry.get(bundle.name, 'authorization.json', missing=True)
    if stored:
        authorization = json.loads(stored)
        if authorization['payload_digest'] != fingerprint or authorization['generation'] != generation:
            raise ValueError('Stored authorization does not match this payload')
        receipt = registry.get(bundle.name, 'receipt.json', missing=True)
        if receipt is not None:
            if json.loads(receipt) != publication_receipt(authorization):
                raise ValueError('Completion receipt conflicts with authorization')
            state = lifecycle(repo, bundle, 'status')
            if not state or state['promotion_id'] != bundle.name or state['generation'] != generation or state['status'] not in ('active', 'complete'):
                raise ValueError('Completion belongs to a stale lifecycle generation')
            verify_publication(api, registry, authorization)
            if state['status'] == 'active':
                lifecycle(repo, bundle, 'complete')
            return
    else:
        lifecycle(repo, bundle, 'check')
        authorization = authorize(api, repo, bundle, manifest, fingerprint, allowed)
        authorization.update(schema_version=1, promotion_id=bundle.name, payload_digest=fingerprint,
                             generation=generation, source=manifest['source'], baselines=manifest['baselines'],
                             manifest_digest=manifest['manifest_digest'],
                             repository='/'.join(api.base.rsplit('/', 2)[-2:]),
                             index_url=os.environ.get('RELEASE_NOTES_INDEX_URL') or
                             'https://%s.github.io/%s/index.yaml' % tuple(api.base.rsplit('/', 2)[-2:]))
    lifecycle(repo, bundle, 'check')
    check_baselines(api, registry, manifest, bool(stored))
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        packages = work / '.cr-release-packages'
        packages.mkdir()
        if not stored:
            frozen = json.loads((bundle / 'frozen.json').read_text())
            sources = registry.get(frozen['storage_key'], 'sources.tar')
            if sha(sources) != frozen['source_sha256']:
                raise ValueError('Frozen source checksum mismatch')
            prepared = work / 'charts'
            extract(sources, prepared)
            if json.loads((prepared / 'source-runtime.json').read_text()) != frozen['runtime_digests']:
                raise ValueError('Frozen source runtime mismatch')
            notes = work / 'notes'
            engine.render(bundle, notes, require_review=True)
            built = package_frozen(prepared, notes, work / 'built')
            authorization['charts'] = []
            for chart in manifest['charts']:
                data = built[chart['name']].read_bytes()
                record = dict(chart, package_sha256=sha(data), notes=(notes / chart['name'] / 'RELEASE_NOTES.md').read_text())
                lifecycle(repo, bundle, 'check')
                registry.put(bundle.name, record['package_sha256'] + '.tgz', data)
                authorization['charts'].append(record)
            lifecycle(repo, bundle, 'check')
            registry.put(bundle.name, 'authorization.json', canonical(authorization))
        # Only the trusted immutable record supplies packages and release descriptions on retry.
        for chart in authorization['charts']:
            data = registry.get(bundle.name, chart['package_sha256'] + '.tgz')
            if sha(data) != chart['package_sha256']:
                raise ValueError('Recovery package checksum mismatch')
            (packages / (chart['name'] + '-' + chart['version'] + '.tgz')).write_bytes(data)
        lifecycle(repo, bundle, 'check')
        registry.put(bundle.name, 'ready.json', canonical({'authorization_sha256': sha(canonical(authorization))}))
        for chart in authorization['charts']:
            lifecycle(repo, bundle, 'check')
            publish_release(api, chart, authorization['merged_sha'],
                            (packages / (chart['name'] + '-' + chart['version'] + '.tgz')).read_bytes())
        # cr index needs the repository checkout, but only the exact downloaded packages.
        local_packages = repo / '.cr-release-packages'
        if local_packages.exists():
            shutil.rmtree(local_packages)
        shutil.copytree(packages, local_packages)
        (repo / '.cr-index').mkdir(exist_ok=True)
        lifecycle(repo, bundle, 'check')
        run('git', '-C', str(repo), 'fetch', 'origin', 'gh-pages:refs/remotes/origin/gh-pages')
        run('cr', 'index', '--push', cwd=repo)
        verify_index(authorization)
        receipt = publication_receipt(authorization)
        for chart in authorization['charts']:
            lifecycle(repo, bundle, 'check')
            chart_record = chart_receipt(authorization, chart)
            release = api.call('GET', '/releases/tags/' + urllib.parse.quote(chart['name'] + '-' + chart['version'], safe=''))
            publish_asset(api, release, 'release-notes-receipt.json', canonical(chart_record))
            registry.put('baseline-' + chart['name'] + '-' + chart['version'], 'receipt.json', canonical(chart_record))
        lifecycle(repo, bundle, 'check')
        registry.put(bundle.name, 'receipt.json', canonical(receipt))
        lifecycle(repo, bundle, 'complete')


def publication_receipt(authorization):
    receipt = {key: authorization[key] for key in ('schema_version', 'promotion_id', 'generation', 'source', 'baselines')}
    receipt['charts'] = [{key: chart[key] for key in ('name', 'version', 'previous_version', 'runtime_digest', 'package_sha256')}
                         for chart in authorization['charts']]
    return receipt


def chart_receipt(authorization, chart):
    return {'schema_version': 1, 'chart': chart['name'], 'version': chart['version'],
            'promotion_id': authorization['promotion_id'], 'authorization_id': sha(canonical(authorization)),
            'package_sha256': chart['package_sha256'], 'notes_sha256': sha(chart['notes'].encode()),
            'source': authorization['source'], 'manifest_digest': authorization['manifest_digest'],
            'index_url': authorization['index_url'],
            'predecessor': chart['name'] + '-' + chart['previous_version'] if chart['previous_version'] else None}


def verify_index(authorization):
    data = request('GET', authorization['index_url'], {'Cache-Control': 'no-cache'})
    try:
        index = json.loads(data)
    except json.JSONDecodeError:
        index = json.loads(run('yq', '-o=json', '.', '-', input=data))
    for chart in authorization['charts']:
        matches = [entry for entry in index.get('entries', {}).get(chart['name'], []) if entry['version'] == chart['version']]
        filename = chart['name'] + '-' + chart['version'] + '.tgz'
        expected_url = 'https://github.com/' + authorization['repository'] + '/releases/download/' + chart['name'] + '-' + chart['version'] + '/' + filename
        if len(matches) != 1 or matches[0].get('digest') != chart['package_sha256'] or not any(
                urllib.parse.unquote(url) == expected_url for url in matches[0].get('urls', [])):
            raise ValueError('Published index does not contain the exact frozen package: ' + filename)


def verify_publication(api, registry, authorization):
    verify_index(authorization)
    for chart in authorization['charts']:
        tag = chart['name'] + '-' + chart['version']
        release = api.call('GET', '/releases/tags/' + urllib.parse.quote(tag, safe=''))
        if release['body'] != chart['notes'] or release['target_commitish'] != authorization['merged_sha']:
            raise ValueError('Completed release changed')
        assets = list(api.pages('/releases/%s/assets' % release['id']))
        package = registry.get(authorization['promotion_id'], chart['package_sha256'] + '.tgz')
        if sha(package) != chart['package_sha256']:
            raise ValueError('Recovery package checksum mismatch')
        for name, expected in ((tag + '.tgz', package), ('release-notes-receipt.json', canonical(chart_receipt(authorization, chart)))):
            matches = [asset for asset in assets if asset['name'] == name]
            if len(matches) != 1 or request('GET', api.base + '/releases/assets/' + str(matches[0]['id']),
                                           dict(api.headers, Accept='application/octet-stream')) != expected:
                raise ValueError('Completed release asset changed: ' + name)


def recover(api, registry, repo, promotion, allowed):
    if not promotion or not re.fullmatch(r'[0-9a-f]{64}', promotion):
        raise ValueError('Recovery requires a promotion ID')
    stored = registry.get(promotion, 'authorization.json', missing=True)
    if stored is None:
        matches = []
        prefix = 'release-notes/' + promotion + '/'
        for pr in api.pages('/pulls?state=closed&sort=updated&direction=desc'):
            if pr.get('merged_at') and any(item['filename'].startswith(prefix)
                                           for item in api.pages('/pulls/%s/files' % pr['number'])):
                matches.append(pr['merge_commit_sha'])
        if len(set(matches)) != 1:
            raise ValueError('Recovery requires exactly one merged promotion PR')
        revision = matches[0]
    else:
        revision = json.loads(stored)['merged_sha']
    if not re.fullmatch(r'[0-9a-f]{40,64}', revision):
        raise ValueError('Invalid authorized merge revision')
    run('git', '-C', str(repo), 'fetch', 'origin', revision)
    with tempfile.TemporaryDirectory() as temporary:
        checkout = Path(temporary) / 'recovery'
        run('git', '-C', str(repo), 'worktree', 'add', '--detach', str(checkout), revision)
        try:
            publish(api, registry, checkout, promotion, allowed)
        finally:
            run('git', '-C', str(repo), 'worktree', 'remove', '--force', str(checkout))


def cancel(repo, registry, promotion):
    if not promotion or not re.fullmatch(r'[0-9a-f]{64}', promotion):
        raise ValueError('Cancellation requires a promotion ID')
    if registry.get(promotion, 'authorization.json', missing=True) is not None:
        raise ValueError('Publication has started; recover it instead of cancelling')
    command = ('python3', str(Path(__file__).with_name('release_notes_lifecycle.py')), '--repo', str(repo))
    state = json.loads(run(*command, 'status', '--promotion', promotion))
    if not state or state['promotion_id'] != promotion or state['status'] != 'active':
        raise ValueError('Promotion is not active')
    run(*command, 'cancel', '--promotion', promotion, '--generation', str(state['generation']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['review', 'prepare-review', 'publish', 'recover', 'cancel'])
    parser.add_argument('--repo', default='.')
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--charts', type=Path, default=Path('charts'))
    parser.add_argument('--pr', type=int)
    parser.add_argument('--promotion')
    parser.add_argument('--preview', action='store_true', help='prepare local evidence without registry access')
    args = parser.parse_args()
    if args.preview and args.command != 'prepare-review':
        raise ValueError('--preview is supported only by prepare-review')
    if args.command == 'prepare-review':
        prepare_review(args.bundle, args.charts, None if args.preview else registry_env())
        return
    if os.environ.get('RELEASE_NOTES_ENABLED') != 'true':
        raise ValueError('Release notes adapter requires RELEASE_NOTES_ENABLED=true')
    api = GitHub(os.environ['GITHUB_REPOSITORY'], os.environ['GITHUB_TOKEN'])
    if args.command == 'review':
        check_review(api, args.repo, args.pr, os.environ.get('RELEASE_NOTES_PRODUCT_IDS', ''))
    elif args.command == 'cancel':
        cancel(args.repo, registry_env(), args.promotion)
    elif args.command == 'recover':
        recover(api, registry_env(), Path(args.repo), args.promotion, product_ids(os.environ.get('RELEASE_NOTES_PRODUCT_IDS', '')))
    else:
        publish(api, registry_env(), Path(args.repo), args.promotion, product_ids(os.environ.get('RELEASE_NOTES_PRODUCT_IDS', '')))


if __name__ == '__main__':
    main()
