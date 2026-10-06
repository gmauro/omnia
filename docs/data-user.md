# Omnia data user guide

This guide is for data scientists, analysts, and workflow users who want to
find and use published data without changing the catalogue.

## Start with discovery

List available catalogues:

```bash
omnia browse catalogs
```

List published releases in a catalogue:

```bash
omnia browse snapshots example-project
```

Retired snapshots are hidden by default. They are available for provenance
inspection only when explicitly requested:

```bash
omnia browse snapshots example-project --include-retired
```

Inspect one release before using it:

```bash
omnia browse show example-project example-project_20261001
```

The summary includes snapshot state, publication date, manifest checksum,
modalities, file counts, and known size. Record the catalogue, snapshot name,
and manifest checksum with an analysis so it can be reproduced later.

## Navigate the logical hierarchy

Browse the root or a directory:

```bash
omnia browse ls example-project example-project_20261001
omnia browse ls example-project example-project_20261001 phenotypes
```

Useful listing options:

```bash
omnia browse ls example-project example-project_20261001 phenotypes \
  --recursive --long --human-readable --sort size --reverse
```

- `--recursive` shows all descendants.
- `--long` shows alias targets and entry status.
- `--human-readable` formats sizes for terminal use.
- `--sort name|path|kind|size` and `--reverse` control order.

If a path is a file or alias rather than a directory, Omnia suggests the exact
`browse describe` command to use.

## Search for files and modalities

Search entry names with shell-style globs. Quote wildcard patterns so the
shell does not expand them first:

```bash
omnia browse find example-project example-project_20261001 --name '*sample*'
omnia browse find example-project example-project_20261001 --path 'annex/**'
omnia browse find example-project example-project_20261001 --modality genotype --kind file
```

Available filters are:

| Option | Meaning |
|---|---|
| `--name PATTERN` | Match the final file or directory name. |
| `--path PATTERN` | Match the full logical path. |
| `--modality NAME` | Restrict results to a curator-defined modality subtree. |
| `--kind directory|file|alias` | Restrict the kind of entry. |
| `--limit`, `--offset` | Page search results. |

No match is a normal result: Omnia prints an empty table and `0 matching
entries`.

## Inspect one logical entry

Use `browse describe` when you have a logical path:

```bash
omnia browse describe example-project example-project_20261001 \
  phenotypes/qced/qc_v2/phenotype_matrix.csv
```

For a file, it reports its Dataset identifier, size, checksum, encoding
format, availability status, curated metadata, and logical aliases. For a
directory or alias, it reports the relevant logical metadata and target.
Backing storage paths are intentionally not shown.

## Use JSON or TSV in notebooks and workflows

Browse commands support human-readable tables by default plus structured
output:

```bash
omnia browse find example-project example-project_20261001 \
  --modality phenotype --kind file --format json

omnia browse ls example-project example-project_20261001 phenotypes --format tsv
```

JSON is suitable for notebooks and workflow wrappers. TSV is suitable for
shell tools such as `awk`, `cut`, and `column`.

## Access data after finding it

Browsing only reads catalogue metadata. To use the data with ordinary tools,
ask the curator or platform administrator for the approved Omnia configuration
and access method. In a managed installation, storage roots are resolved by
the configured storage profile and are not shown to users.

### Interactive workstation: mount a snapshot

When FUSE is available:

```bash
omnia mount example-project example-project_20261001 ~/omnia/example-project
```

Then use the logical paths directly:

```bash
less ~/omnia/example-project/annex/sample_metadata.csv
```

The mount is read-only. It continues running in the foreground until it is
unmounted or interrupted. On macOS, foreground operation is the reliable
mode.

### HPC/shared filesystem: export a symlink view

If FUSE is unavailable, create a personal logical view:

```bash
omnia export-links example-project example-project_20261001 ~/omnia/example-project
```

To access one curated modality only:

```bash
omnia export-links example-project example-project_20261001 ~/omnia/example-project-genotypes \
  --modality genotype
```

The destination must not already exist. It is safe to remove your exported
view with normal recursive deletion because the directories are owner-writable;
the data targets are not deleted. Do not change the symlink view and assume it
changes the catalogue—it does not.

### Describe where you are

Inside an exported view or a snapshot FUSE mount, use the top-level command:

```bash
cd ~/omnia/example-project/phenotypes/qced/qc_v2
omnia describe
```

It finds the snapshot marker in the view root and reports the logical
directory or file context from that level downwards: recursive counts, known
size, modalities, curator metadata, snapshot state, and manifest checksum.

An explicit path also works:

```bash
omnia describe ~/omnia/example-project/phenotypes/qced/qc_v2
omnia describe . --format json
```

`omnia describe` does not work on an arbitrary backing-storage path or on a
generic catalogue mount without `--snapshot`, because there is no single
snapshot context to describe.

## Legacy: obtain a raw path list only when needed

`omnia get` prints the physical paths of every dataset registered in a
catalogue. It does not select a snapshot or use the curated logical hierarchy.
Prefer `browse find` to discover logical paths, then `mount` or
`export-links` to access a published snapshot. Use this legacy command only
when an approved administrative workflow explicitly needs raw paths:

```bash
omnia get example-project
omnia get example-project --format json
omnia get example-project --output example-project-paths.txt
```

The first two write to standard output; `--output` explicitly creates a local
file.

## Common problems

| Situation | What to do |
|---|---|
| A snapshot is not listed | Check the catalogue name; retired snapshots need `--include-retired`. Draft snapshots are curator-only. |
| A search has no result | Quote globs, for example `--name '*sample*'`; try `--path` for parent-directory text. |
| `browse ls` says a path is not a directory | Run the suggested `omnia browse describe ...` command. |
| `omnia describe` cannot find an Omnia view | Run it below an exported/snapshot-mounted root, or use `browse` first. |
| Mount/export rejects a storage root | Obtain the approved trusted root from the administrator. |
| An exported view already exists | Choose a new destination or remove only your existing view before exporting again. |

## What Omnia does not yet provide

Omnia currently assumes access to the catalogue database and trusted shared
storage has already been arranged. It does not yet offer browser-based login,
fine-grained Omnia authorization, direct authenticated per-file downloads, or
a remote GA4GH DRS endpoint. Contact the data steward when you need access
outside the shared environment.
