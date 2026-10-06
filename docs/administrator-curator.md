# Omnia administrator and curator guide

This guide is for people who register data, design a logical catalogue tree,
publish releases, and operate the local storage and MongoDB connection used by
Omnia.

## Mental model

Omnia separates physical storage from the logical catalogue presented to users.

```text
POSIX/object storage → Dataset records → catalogue → versioned tree snapshot → user view
```

- A **Dataset** records one physical data asset and its metadata.
- A **catalogue** groups related datasets, for example `example-project`.
- A **tree snapshot** is an immutable, versioned logical hierarchy for one
  catalogue release.
- A **TreeEntry** is a logical directory, file, or alias inside a snapshot.
- A curator-owned **manifest** supplies exclusions, logical renames, roles,
  and scientific metadata.

Use one snapshot for one coherent scientific release. For example,
`example-project_20261001` can contain genotypes, phenotypes, proteomics, and annex
files known to belong together. If a phenotype release changes, publish a new
top-level snapshot rather than changing the old one.

## Create and publish a release

Create the catalogue once, then ingest a physical source directory into a
draft snapshot:

```bash
omnia catalogue create example-project --description "Example project data"

omnia tree ingest example-project /processing/example-project example-project_20261001 \
  --manifest example-project_20261001.yaml
```

Use the `catalogue` command group to manage catalogue records:

```bash
omnia catalogue list
omnia catalogue describe example-project
omnia catalogue verify example-project
omnia catalogue update example-project --description "Updated project description"
omnia catalogue delete example-project
```

`mkdir`, `mv`, and `rmdir` remain available as legacy compatibility commands,
but new scripts should use `omnia catalogue create`, `update`, and `delete`.
`omnia ls` is also a legacy command: use `catalogue describe` for catalogue
metadata and `catalogue verify` for checksum verification.

Inspect and publish the draft:

```bash
omnia tree validate example-project example-project_20261001
omnia tree publish example-project example-project_20261001
```

The lifecycle is:

```text
draft → published → retired
```

- **draft**: may be extended with `tree add-path`, validated, or discarded.
- **published**: immutable; it can be browsed, mounted, and exported.
- **retired**: preserved as provenance but excluded from normal browse results,
  mounts, and exports.

Retire a superseded release after its replacement is published:

```bash
omnia tree retire example-project example-project_20261001 \
  --reason "Superseded by phenotype QC release P2"
```

List all lifecycle records, including drafts and retired snapshots:

```bash
omnia tree list example-project
```

Discard only a draft that is no longer wanted:

```bash
omnia tree discard example-project failed_import --yes
```

## Add data before publication

An additional source tree can be placed below an explicit logical destination
while a snapshot is still draft:

```bash
omnia tree add-path example-project example-project_20261001 \
  /processing/example-project_annex annex \
  --skip-metadata-computation
```

For a directory source, its contents appear below `annex/`. For a single file,
the destination is the exact logical file path. Omnia creates missing logical
parents and rejects path collisions, unsafe paths, and additions to published
or retired snapshots.

## Update one modality in a new release

Published snapshots are immutable. When, for example, phenotypes are updated,
clone the current published release into a draft and replace only its logical
phenotype subtree:

```bash
omnia tree clone example-project example-project_20261001 example-project_20261215

omnia tree replace-path example-project example-project_20261215 \
  /processing/example-project_phenotypes_P2 phenotypes \
  --manifest example-project_20261215.yaml

omnia tree validate example-project example-project_20261215
omnia tree publish example-project example-project_20261215
omnia tree retire example-project example-project_20261001 \
  --reason "Superseded by phenotype release P2"
```

`tree clone` accepts a published source snapshot and creates a draft target
snapshot with copied logical entries, Dataset references, curator metadata, and
manifest provenance. When the source manifest declares a `snapshot`, Omnia
retargets that safeguard and recalculates its checksum for the draft name. It
does not copy physical data bytes.

`tree replace-path` is draft-only. It removes the destination path and all its
logical descendants, then adds the supplied file or directory at the same
logical destination. Unchanged entries elsewhere in the snapshot still point
to the original Dataset records. Metadata on the replaced root is retained;
curate changed descendants through a replacement manifest.

Always pass `--manifest` when a replacement changes the logical scientific
description. The manifest is checked against the post-replacement tree and
stored as the new snapshot manifest. Without it, Omnia clears the copied
manifest checksum and records that the previous manifest was invalidated by
the replacement; do not publish that draft until its provenance is acceptable
for your release policy.

## Curator manifest

The manifest is YAML and is stored verbatim, with a SHA-256 checksum, in the
published snapshot. It is the small, reviewable description of the scientific
meaning of the tree.

```yaml
catalog: example-project
snapshot: example-project_20261001

exclude:
  - "**/*.log"
  - ".DS_Store"

renames:
  - source: raw_data
    destination: phenotypes/source
  - source: raw_data/qc
    destination: phenotypes/qced/qc_v2

nodes:
  - path: phenotypes
    role: modality
    metadata:
      modality: phenotype

  - path: phenotypes/qced/qc_v2
    role: derived_data
    metadata:
      processing_level: qced
      qc_version: qc_v2
      pipeline: phenotype-qc
      pipeline_version: "2.1.0"
```

### Manifest fields

| Field | Meaning |
|---|---|
| `catalog`, `snapshot` | Optional safeguards that must match the ingest command. |
| `exclude` | Shell-style patterns evaluated against scanned physical-relative paths. |
| `renames` | Maps a scanned `source` subtree to a logical `destination` without moving data. |
| `nodes` | Annotates a logical path after renaming with a `role` and JSON-compatible `metadata`. |

All manifest paths must be non-empty safe relative paths: no absolute paths and
no `..`. Rename destinations are logical paths. The most-specific matching
rename applies to nested sources. Omnia rejects duplicate rename sources and
logical collisions. Logical aliases are rewritten consistently when their
targets are renamed.

Metadata accepts strings, numbers, booleans, lists, and mappings. `modality`
is currently used by `browse find --modality` and `export-links --modality`;
other metadata remains available through `browse describe` and JSON output.

## Naming and QC strategy

Keep modality roots stable and encode release identity in the snapshot name:

```text
example-project_20261001/
├── genotypes/
├── phenotypes/
│   ├── source/
│   ├── qced/qc_v2/
│   └── documentation/
├── proteomics/
└── annex/
```

Prefer names such as `example-project_YYYYMMDD`, `genotypes`, `phenotypes`,
`qced/qc_v2`, and `derived/<pipeline>/<version>`. Keep explicit QC versions
for reproducibility. A `current` or `latest` logical alias may be convenient,
but it must not be the only path to a versioned result.

When a modality changes, create a new snapshot such as `example-project_20261215`.
Unchanged files are represented by new logical entries pointing to the same
Dataset records; Omnia does not copy their underlying bytes.

## Configure storage profiles and safe data access

Trusted physical roots belong in the administrator-managed Omnia YAML
configuration, not MongoDB and not normal user commands. For a shared/HPC
deployment, keep this file centrally managed and read-only, for example
`/etc/omnia/config.yaml`:

```yaml
default_storage_profile: example-project-shared

storage_profiles:
  example-project-shared:
    storage_roots:
      - /processing/example-project
      - /processing/reference-data
    allowed_catalogs:
      - example-project
```

Users then select a published snapshot without knowing the physical roots:

```bash
omnia --configuration_file /etc/omnia/config.yaml \
  mount example-project example-project_20261001 /mnt/example-project

omnia --configuration_file /etc/omnia/config.yaml \
  export-links example-project example-project_20261001 /project/views/example-project_20261001
```

`allowed_catalogs` prevents accidental use of a profile for the wrong
catalogue. A named profile can be selected when a deployment has more than
one:

```bash
omnia mount example-project example-project_20261001 /mnt/example-project \
  --storage-profile example-project-shared
```

`--storage-root` remains an advanced administrator override for test and
one-off environments. It may be repeated for multiple roots, but it cannot be
combined with `--storage-profile`.

Only files registered in Omnia below the resolved roots are exposed. Paths
outside those roots and physical symbolic links are rejected.

For an HPC shared filesystem without FUSE, materialize a new symlink view:

```bash
omnia export-links example-project example-project_20261001 /project/views/example-project_20261001
```

Exports are atomically created and their directories are owner-writable so the
view can be removed. The file symlinks still reveal and depend on their POSIX
targets; target filesystem permissions remain the access control mechanism.
FUSE avoids exposing target paths to ordinary directory listings.

On macOS, use foreground FUSE operation. macFUSE background forking can fail
because the process may fork after Objective-C threads are active.

## Preserve provenance and consistency

Never manually edit `tree_snapshots` or `tree_entries` in MongoDB. Do not
delete a Dataset that is referenced by a tree snapshot: `omnia rm` now refuses
that operation and reports the logical entries that depend on it. Validate
legacy or externally damaged snapshots with:

```bash
omnia tree validate example-project example-project_20261001
```

Validation reports missing parents, missing alias targets, and deleted Dataset
references. Published snapshots cannot be repaired in place; publish a
corrected successor snapshot instead.

## Hand off a release to users

Give users the catalogue and snapshot name, plus either:

- the approved `omnia mount` command and trusted storage root; or
- an approved `omnia export-links` destination on the shared filesystem.

Users should discover logical paths with `omnia browse`, not by receiving raw
storage paths. See [the data user guide](data-user.md).

## Current security boundary

This implementation is appropriate for trusted users and workflow jobs that
already have MongoDB and filesystem access on the relevant host or shared
filesystem. It does not yet provide federated identity, dataset-level Omnia
authorization, or authenticated remote downloads. Do not treat a local mount
or symlink export as a security boundary; enforce access through POSIX ACLs,
storage policy, and the surrounding platform.
