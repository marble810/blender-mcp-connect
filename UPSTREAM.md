# UPSTREAM — Cross-Forge Downstream Maintenance

## Repository Layout

| Remote | URL | Purpose |
|---|---|---|
| `origin` | <https://github.com/marble810/blender-mcp-connect.git> | Downstream product |
| `upstream` | <https://projects.blender.org/lab/blender_mcp.git> | Authoritative upstream |
| (optional) `blender-fork` | user fork on `projects.blender.org` | Only for submitting upstream PRs |

| Branch | Purpose |
|---|---|
| `main` | Reviewed downstream product branch |
| `upstream-main` | Exact mirror of Blender Lab `main` |
| `feature/*` | Downstream work |

GitHub cannot mark a repository hosted on another forge as a GitHub fork, so
this repository reports `isFork: false` while still preserving the complete
upstream Git ancestry. It is a legitimate Git downstream.

## Automatic Synchronization

`.github/workflows/upstream-sync.yml` runs daily (06:00 UTC, plus manual
`workflow_dispatch`):

1. Fetches Blender Lab `main` and force-updates the `upstream-main` mirror.
2. Probes for merge conflicts (`git merge-tree`).
3. **Clean merge** → merge commit (recording the exact upstream SHA) +
   unit tests → pushed to `main`.
4. **Conflicts, failing tests, or a protected `main`** → a
   `sync/upstream-*` branch is pushed and a PR is opened, **assigned to
   the repository owner** (GitHub emails the assignee). Conflicts are
   committed with markers as a WIP state — never force-resolved.

## Manual Synchronization

The automated flow covers the common case. The manual flow below remains
available for exceptional reviewed merges:

```bash
git fetch upstream

git switch upstream-main
git reset --hard upstream/main
git push --force-with-lease origin upstream-main

git switch main
git merge --no-ff upstream-main
```

Rules:

1. Upstream changes are synchronized automatically (see above): clean
   merges land on `main` with merge commits and the upstream SHA recorded;
   conflicting/failing merges open a reviewed `sync/upstream-*` PR — never
   an unattended force-resolution.
2. Merge reviewed upstream changes with merge commits; do not rewrite
   published downstream history (no rebase of `main`).
3. Do not republish Blender Lab release tags. Use `connect-vX.Y.Z` tags.
4. Record the exact upstream SHA in every downstream release.

## Versioning

Upstream owns tags: `v0.1.0`, `v0.3.0`, `v1.0.0`, `26.04.10`.

Downstream uses independent versions starting at `0.1.0` with tags:

```text
connect-v0.1.0
```

## Contributing Fixes Upstream

Create a real fork on `projects.blender.org` only when submitting focused
generic fixes upstream. Cherry-pick only generic fixes (SDK compatibility,
Windows stdio child-process handling, generic socket/test improvements) into
the upstream PR. Do **not** submit downstream branding, PyPI workflow, or
product-specific registry paths as part of unrelated fixes.

When upstream merges an equivalent fix, remove the downstream duplicate
during a reviewed synchronization.
