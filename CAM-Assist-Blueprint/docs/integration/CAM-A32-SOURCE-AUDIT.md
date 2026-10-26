# CAM-A32 Source Audit

## Disposition

```text
reported Phase 12 commit   058abb169754ebbfa2c38458ffcc64fc6de96452
reported historical branch cam-a32-indexed-surface-continuity-metrology
verdict                    NOT RECOVERED in the stores searched below
reconstruction             not authorized by CAM-A33-PEP-ALIGN-001
```

Absence from this Cloud Agent checkout is not a claim that every copy of
the object is gone. Locations this run could not open are listed as not
searched. The existing reconstruction note on `main`
(`docs/dev_orders/CAM-A32-RECONSTRUCTION.md`, introduced by `e1a9fd8` and
merged in `2b146ef`) is a citation of the same SHA. It is not the object,
and this audit does not treat that note as the witness.

The only file in this working tree that contains the SHA is that
reconstruction order. `git grep` equivalent search of the worktree found
no other copy.

## R0 baseline

Recorded on this clone before any CAM-A33 file was added.

| Fact | Witness |
| --- | --- |
| `main` and `HEAD` | `2b146ef1f325ae0db1377feac894eb6ae7e71316` |
| Active branch at inspection | `main`, tracking `origin/main` |
| Remote | `origin` → `https://github.com/HanzoRazer/CAM-Assist-Blueprint` |
| Worktrees | `/workspace` only, at `2b146ef` |
| Reflog | clone and checkout of `2b146ef` only. No earlier local history |
| Object store | one pack, 1518 objects, 0 loose objects (`git count-objects -v`) |
| Latest commit subject | `Merge pull request #41 from HanzoRazer/cursor/cam-a32-reconstructed-surface-metrology-4e0c` |
| GitHub CI on that SHA | Actions run `34945955534`, workflow `CAM Assist Tests`, conclusion `success`, created `2026-09-15T08:15:21Z` (Tuesday, September 15, 2026, 3:15 AM CT) |
| Local tests, unchanged tree | `python3 -m pytest` in `CAM-Assist-Blueprint`: `1637 passed in 34.91s`, exit 0 |
| Non-execution check | `python3 scripts/ci_verify_non_execution_invariant.py`: exit 0, `4 packages` |

`origin` branch names matching `a32` or `metrology`, from
`git ls-remote origin`:

```text
e1a9fd8b5f2ff63c50bbd2222133c34c2a2a6849  refs/heads/cursor/cam-a32-reconstructed-surface-metrology-4e0c
```

That ref is the reconstruction-order branch already merged. It does not
contain `058abb1`.

## Searched, and the object was absent

### 1. This clone's object store

Commands and results:

```text
git cat-file -t 058abb169754ebbfa2c38458ffcc64fc6de96452
  fatal: git cat-file: could not get object info

git rev-list --all | grep ^058abb
  no matching commit

git branch -a --contains 058abb169754ebbfa2c38458ffcc64fc6de96452
  error: no such commit

git cat-file --batch-check --batch-all-objects | awk prefix 058abb
  no line

git fsck --unreachable --no-reflogs
  no dangling output

git notes list
  empty
```

`git rev-list --all --count` was 177. The pack is the clone of
`origin`, not a second object store.

### 2. GitHub commit object for CAM-Assist-Blueprint

```text
GET /repos/HanzoRazer/CAM-Assist-Blueprint/commits/058abb169754ebbfa2c38458ffcc64fc6de96452
HTTP 422
{"message":"No commit found for SHA: 058abb169754ebbfa2c38458ffcc64fc6de96452"}
```

### 3. Historical branch name

```text
GET /repos/HanzoRazer/CAM-Assist-Blueprint/branches/cam-a32-indexed-surface-continuity-metrology
HTTP 404 Branch not found
```

### 4. Forks

```text
GET /repos/HanzoRazer/CAM-Assist-Blueprint/forks
empty list
```

### 5. Commit search by hash

```text
GET /search/commits?q=hash:058abb169754ebbfa2c38458ffcc64fc6de96452
{"total_count": 0, "items": []}
```

This search is limited to repositories the token can see. A zero count is
a negative result inside that scope. It is not a search of the public
internet.

### 6. The same SHA as a commit in related repositories

Each call returned HTTP 422, `No commit found for SHA`:

```text
HanzoRazer/luthiers-toolbox
HanzoRazer/tap_tone_pi
HanzoRazer/Master-All-Strings
HanzoRazer/CAM-Creation-Studio
HanzoRazer/CNC-Production-Shop
```

These checks ask whether that SHA is a commit object. They do not read
every blob.

### 7. Filesystem bundles and extra worktrees on this VM

`find /` for `*.bundle`, `*physical-engineering*`, `*luthiers*`, and
`*tap-tone*` returned only
`CAM-Assist-Blueprint/docs/dev_orders/CAM-A32-RECONSTRUCTION.md` as a
CAM-A32 path. No Git bundle was present.

## Not searched

These places were not opened. Do not read the disposition above as a
search of them.

```text
the original workstation
owner worktrees outside this VM
the File Library packet cited by CAM-A32-RECONSTRUCTION.md
removable media, private object stores, and bundles that are not on this VM
```

GitHub code search for the SHA string was attempted and returned HTTP 429
with a retry delay of about 736 seconds. That request did not finish, so
it is not a negative witness. The commit API results above remain the
object-level witnesses.

## What this does not authorize

```text
reconstructing surface_scan, setup_registration, or surface_state schemas
inventing Scan A/B inputs from the output summaries in the reconstruction note
assigning 058abb1 to a new commit
reusing the unrecovered branch name
editing LEDGER.md or ROADMAP.md
```

Phase R1 of the reconstruction program stays blocked on its own terms.
CAM-A33 does not lift that block.
