# Reviewed chart release notes

The feature is off unless `RELEASE_NOTES_ENABLED` is exactly `true`.
When enabled, the publisher does not use the legacy tag-difference publisher.
A missing bundle, missing classification, or missing Product approval stops publication.

## Enable the feature

1. Install the engine, lifecycle helper, adapter, and three workflow files on the default branch.
2. Configure the private collector to generate `release-notes/<promotion_id>` outside `charts`.
3. Acquire the lifecycle generation before source collection and baseline selection.
4. Save that generation in the bundle's `lifecycle.json`.
5. Run dependency preparation after bundle generation, before the PR commit.
6. Configure the registry and GitHub settings below.
7. Enable both the private pipeline and public repository feature flags.
8. Require the status `Release Notes / Product Review` in the protected branch rules.

Do not enable the flag until dependency preparation is connected to the private pipeline.
The PR must contain `frozen.json`; an empty dependency array is not an alternative.
Allow `frozen.json` in the private pipeline's bundle file allowlist.

### GitHub variables and secrets

- Variable `RELEASE_NOTES_ENABLED`: `true` enables the new path.
- Variable `RELEASE_NOTES_PRODUCT_IDS`: comma-separated numeric GitHub user IDs. No default exists.
- Variable `RELEASE_NOTES_RECOVERY_PROJECT`: URL-encoded GitLab project ID or project path.
- Secret `RELEASE_NOTES_RECOVERY_TOKEN`: deploy token with package read and write access.
- Optional variable `RELEASE_NOTES_GITLAB_API_URL`: defaults to `https://gitlab.com/api/v4`.
- Optional variable `RELEASE_NOTES_INDEX_URL`: public index URL for a custom Pages domain.
  The default is `https://<owner>.github.io/<repository>/index.yaml`.

The workflow token needs repository content write access and PR read access for publication.
The review workflow needs content read, PR read, and commit status write access.
Permit the publication token to update `gh-pages` and the `release-notes-state` branch.
Protect these branches against other writers.

### Registry controls

Use a private GitLab Generic Package Registry project.
Disable duplicate generic package files and configure retention to keep recovery artifacts.
Give the private collector package write access. Restrict the publication token to trusted jobs.
Do not expose either token to PR code.
Use HTTPS for the registry API URL.

The adapter compares existing bytes before upload and checks uploaded bytes after upload.
Registry denial, transport errors, and checksum conflicts stop the operation.
Only an HTTP 404 means that an artifact does not exist.
The registry must reject duplicate writes; a GET followed by PUT is not an atomic lock.
The lifecycle branch and workflow concurrency group prevent supported publishers from overlapping.

## Prepare and review

After `engine.generate`, run this command from the public chart checkout:

```sh
python3 scripts/ci/release_notes_github.py prepare-review \
  --bundle "release-notes/$PROMOTION_ID" --charts charts
```

Set `RELEASE_NOTES_RECOVERY_PROJECT` and `RELEASE_NOTES_RECOVERY_TOKEN` first.
In GitLab, `CI_JOB_TOKEN` can replace the deploy token.
`CI_API_V4_URL` selects the API host for this command.

Preparation copies all chart sources to a temporary directory.
It resolves external dependencies and local child dependencies there.
It stores exact prepared source bytes as `release-notes/<storage_key>/sources.tar` in the registry.
The storage key binds all original runtime digests and the preparation-script checksum.
Thus a refreshed public base can use a new snapshot without changing the promotion identity.
`frozen.json` binds the archive checksum and the runtime digests of every original local chart.
This includes local dependencies that are not in the publication chart set.
The archive checksum binds all external dependency archive bytes.
A retry reuses the archive only if every original chart digest still matches.
Source charts remain unchanged.

For a local preview, add `--preview` to the preparation command.
Preview requires no recovery credentials and makes no registry requests or writes.
It resolves dependencies locally and marks `frozen.json` as preview evidence.
Preview dependency archive bytes can differ from publication bytes because Helm adds timestamps.
Preview evidence is not publication authorization. The review gate rejects it.
The private pipeline must run preparation without `--preview` before it opens the promotion PR.

Product edits `review.yaml` to classify every entry as `customer-facing` or
`not-customer-facing`. Each classification must retain the matching `content_hash`.
Product then approves the exact current PR head through GitHub review.
Classification is not approval. A comment, stale approval, or dismissed approval does not authorize
publication. A later effective review replaces the same reviewer's earlier decision.

The review check runs default-branch code. It reads PR data through `git archive`.
It rejects links and unsafe archive paths. It does not run PR scripts or install PR dependencies.
The unprivileged review-event workflow triggers the default-branch `workflow_run` listener.
PR updates also trigger the check. Unrelated PRs do not need a release bundle.
All event sources share one concurrency group. Each queued check reads the current review state.
This prevents an older approval check from overwriting a later dismissal failure.

The adapter compares the actual PR chart set with the manifest chart set.
It also compares the reviewed source and metadata with the merged tree.
Squash merges can pass because the payload must match, not the merge commit SHA.

## Publish and recover

Publication uses only the manifest chart set.
It renders filtered notes, then packages local dependencies before their parents without network
dependency resolution. Nested local charts receive their filtered notes before parent packaging.
It saves exact package bytes and trusted authorization before creating public releases.
Retries use those bytes, not a new Helm build.

The adapter creates missing release assets but rejects conflicting existing assets.
It uses chart-releaser only to update the index from the recovered local packages.
It checks the served index before writing publication receipts.
Pages propagation can delay this check. Retry recovery after the index becomes available.

Each release receives `release-notes-receipt.json` after index verification.
The receipt includes `schema_version`, `chart`, `version`, `promotion_id`, `authorization_id`,
`package_sha256`, `notes_sha256`, `source`, `manifest_digest`, `index_url`, and `predecessor`.
The predecessor is the previous chart release tag, or null.
The registry also stores a per-chart receipt at
`release-notes/baseline-<chart>-<version>/receipt.json`.
An aggregate completion receipt is stored at `release-notes/<promotion_id>/receipt.json` last.

For recovery, dispatch the `release` workflow with `operation: recover` and the exact promotion ID.
The adapter finds the original merged PR, even if the default branch has moved.
After authorization exists, it restores the authorized merge tree in a temporary worktree.
It verifies the payload before it reuses authorization.
A completed retry checks public packages, receipts, and index without recreating the release.

For cancellation, dispatch the same workflow with `operation: cancel`.
Cancellation uses the same `chart-release` concurrency group as publication.
Cancellation is refused after authorization exists. Recover that publication instead.
Do not call lifecycle cancellation outside this serialized workflow while a publisher can run.

## Verification and limits

Run the local checks:

```sh
python3 -m unittest discover -s scripts/ci -p test_release_notes_github.py
sh scripts/ci/prepare-charts-test.sh
```

The adapter tests use local HTTP servers, local Git repositories, real Helm packaging, and a fake
index command. They cover index failure, exact-byte recovery, receipts, stale approvals, pagination,
archive paths, and credential removal on redirects. They do not write to live services.

Live GitHub event routing, GitLab duplicate rejection, token scopes, Pages propagation, and actual
`cr index --push` remain deployment checks. The preparation command above was exercised through its
Python entry point with local fixtures, not against a live registry.
Configure credentials before a controlled rollout.
Do not treat local tests as proof of these settings.
Configure the Pages deployment mechanism to publish changes made by the workflow token.

Implementation entry points: `scripts/ci/release_notes_github.py:84` for approval and
`scripts/ci/release_notes_github.py:169` for chart-set verification.
Dependency preparation starts at `scripts/ci/release_notes_github.py:243`.
Publication starts at `scripts/ci/release_notes_github.py:488`.
