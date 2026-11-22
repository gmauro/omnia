# Omnia data user guide

This guide is for data scientists, analysts, and workflow users who want to
find and use published data without changing the catalogue.

## Hierarchy and Terminology

Omnia organizes data into catalogues and snapshots:

- **Catalogue:** a collection of related data. Separate catalogues may
  hold source and QC data for the same study.
- **Snapshot:** a specific version of a catalogue’s contents. Users access
  **published snapshots**, also called **releases**.
- **Path (logical path):** the location of a file or directory within an
  Omnia snapshot, such as `phenotypes/phenotype_matrix.csv`. This may differ
  from its location in physical storage.

Source data are the original files supplied by the data holders.
QC data are produced through quality checking of source data.
Analysis data are results produced through analytical processing.

Data can also be grouped by type or **modality**, such as genotypes or
phenotypes. Modality labels help you find and access a particular type
of data.

## User commands overview

- **[Discover a snapshot](#start-with-discovery):** use `omnia browse catalogs`,
  `omnia browse snapshots`, and `omnia browse show` to find catalogues, choose a
  snapshot, and inspect its summary.
- **[Explore its contents](#navigate-the-logical-hierarchy):** use
  `omnia browse ls` to list directories and files within a snapshot.
- **[Find files or modalities](#search-for-files-and-modalities):** use
  `omnia browse find` to search by name, path, modality, or entry kind.
- **[Inspect file or directory metadata](#inspect-file-or-directory-metadata):** use
  `omnia browse describe` to view metadata for a specific path.
- **[Choose the command output format](#choose-the-command-output-format):** add
  `--format json` or `--format tsv` to browse commands to display their output as JSON or TSV.
- **[Use documented data paths](#access-data-after-finding-it):**
  use the logical paths provided in the data documentation as inputs
  to your analysis tools.
- **[Personal mount](#interactive-workstation-mount-a-snapshot):**
  optionally use `omnia mount` to create a read-only view when supported.
- **[Personal symlink view](#hpcshared-filesystem-export-a-symlink-view):**
  optionally use `omnia export-links` to create your own filesystem view.
- **[Inspect a local view](#inspect-metadata-from-a-local-snapshot-view):**
  use `omnia describe` to identify its catalogue and snapshot and inspect
  metadata for your current location.

## Start with discovery

List available catalogues:

```bash
omnia browse catalogs
```

The returned `NAME` column contains the catalogue names you can use in subsequent
commands. List published snapshots in a catalogue:

```bash
omnia browse snapshots <catalogue-name>
```

Retired snapshots are hidden from normal listings. Include their records
when inspecting previous versions and their lifecycle status:

```bash
omnia browse snapshots <catalogue-name> --include-retired
```

> [!NOTE]
> Retirement does not necessarily mean that the data are invalid.
> Superseded snapshots retain documented logical paths for reproducing
> earlier analyses.
>
> Check the data documentation for the snapshot's status. Do not use data
> marked as deprecated.

Inspect one snapshot before using it:

```bash
omnia browse show <catalogue-name> <snapshot-name>
```

The summary includes snapshot state, publication date, manifest checksum,
modalities, file counts, and known size.

> [!TIP]
> For reproducibility, record the catalogue name, snapshot name, and
> manifest checksum alongside your analysis.

## Navigate the logical hierarchy

Browse the snapshot’s root directory:

```bash
omnia browse ls <catalogue-name> <snapshot-name>
```

To browse a directory within the snapshot, append its path relative to the
snapshot root, as shown in the `PATH` column. For example, to browse
`proteomics/olink`:

```bash
omnia browse ls <catalogue-name> <snapshot-name> proteomics/olink
```

Useful listing options:

```bash
omnia browse ls <catalogue-name> <snapshot-name> proteomics/olink \
  --recursive --long --human-readable --sort size --reverse
```

- `--recursive` shows all descendants.
- `--long` shows alias targets and entry status.
- `--human-readable` formats sizes for terminal use.
- `--sort name|path|kind|size` and `--reverse` control order.

If Omnia reports that a path is not a directory, follow the suggested
`browse describe` command to inspect its metadata. See
[Inspect file or directory metadata](#inspect-file-or-directory-metadata).

## Search for files and modalities

Search by name or path, or filter results by modality and entry kind.
For name and path searches, use wildcard patterns in single quotes:

```bash
omnia browse find <catalogue-name> <snapshot-name> --name '*sample*'
omnia browse find <catalogue-name> <snapshot-name> --path 'annex/**'
omnia browse find <catalogue-name> <snapshot-name> --modality genotype --kind file
```

Available filters are:

| Option                          | Meaning                                                 |
| ------------------------------- | ------------------------------------------------------- |
| `--name PATTERN`                | Match the final file or directory name.                 |
| `--path PATTERN`                | Match the full logical path.                            |
| `--modality NAME`               | Restrict results to a curator-defined modality subtree. |
| `--kind directory\|file\|alias` | Restrict the kind of entry.                             |
| `--limit`, `--offset`           | Page search results.                                    |

No match is a normal result: Omnia prints an empty table and `0 matching
entries`.

## Inspect file or directory metadata

After finding a file or directory with `browse ls` or `browse find`, use
`browse describe` to inspect its metadata.

Copy the value from the `PATH` column and use the same catalogue and snapshot
names as in your listing or search:

```bash
omnia browse describe <catalogue-name> <snapshot-name> <path>
```

For example, to inspect a genotype file returned by the preceding search:

```bash
omnia browse describe <catalogue-name> <snapshot-name> \
  genotypes/imputed/chrX.pvar
```

For a file, it reports its Dataset identifier, size, checksum, encoding
format, availability status, curated metadata, and logical aliases. For a
directory or alias, it reports the relevant logical metadata and target.
Backing storage paths are intentionally not shown.

## Choose the command output format

Browse commands display human-readable tables by default. Use `--format`
to obtain output suitable for processing in notebooks, scripts, or workflows:

- **JSON** is suitable for notebooks and workflow scripts.
- **TSV** is suitable for shell tools such as `awk`, `cut`, and `column`.

For example, find files in the `phenotype` modality and return their metadata
in JSON format:

```bash
omnia browse find <catalogue-name> <snapshot-name> \
  --modality phenotype --kind file --format json
```

Or list the files and directories immediately inside the phenotypes
directory in TSV format:

```bash
omnia browse ls <catalogue-name> <snapshot-name> phenotypes --format tsv
```

Note that paths are relative to the selected snapshot’s root.

## Access data after finding it

Use the logical paths provided in the data documentation as inputs
to your analysis tools. The documentation identifies the catalogue and
snapshot associated with those paths.

When an update is published, use the newly documented paths for new
analyses. Keep existing analyses pinned to their original documented paths,
unless those data have been deprecated.

Do not infer the data version from the filesystem directory name.
Use the documented snapshot identifier or check it with `omnia describe`.

Browse commands read catalogue metadata and omit physical storage paths.
Exported symlinks can reveal where the original files are stored.

The following sections explain how to create a personal snapshot view
when this is supported by your installation. You do not need to create
one when a documented shared view is already available.

### Interactive workstation: mount a snapshot

Mounting makes a snapshot’s directories and files accessible through a
folder on your workstation. This requires FUSE, a filesystem component
that your administrator can help you set up.

If FUSE is available, choose a location for the snapshot view. In this example,
it is `~/omnia/my-snapshot` inside your home directory:

```bash
omnia mount <catalogue-name> <snapshot-name> ~/omnia/my-snapshot
```

While the mount is running, open another terminal to browse the folder
or read files using your usual tools:

```bash
ls ~/omnia/my-snapshot
```

For example, if the snapshot contains `annex/sample_metadata.csv`:

```bash
less ~/omnia/my-snapshot/annex/sample_metadata.csv
```

> [!TIP]
> Use mounted file paths directly as inputs to your analysis tools.
> For example, if your snapshot is mounted at `~/omnia/my-snapshot`,
> the file `phenotypes/phenotype_matrix.csv` is accessible at
> `~/omnia/my-snapshot/phenotypes/phenotype_matrix.csv`.
>
> The mount is read-only. Save analysis outputs in a separate working
> directory.
>
> Keep the mount running in its original terminal and use another terminal
> for your analysis. This foreground mode is recommended on macOS.
> Pressing **Ctrl+C** in the original terminal stops the mount.

### HPC/shared filesystem: export a symlink view

On an HPC or shared filesystem, use `export-links` when FUSE is unavailable.

This creates the snapshot’s directory structure with **symlinks**—shortcuts
pointing to the original data files. It does not copy the data.

Choose a destination that does not already exist:

```bash
omnia export-links <catalogue-name> <snapshot-name> ~/omnia/my-snapshot
```

After the command finishes, browse the view using ordinary filesystem tools:

```bash
ls ~/omnia/my-snapshot
```

To create a view containing only genotype data, use a separate destination:

```bash
omnia export-links <catalogue-name> <snapshot-name> \
  ~/omnia/my-snapshot-genotypes --modality genotype
```

> [!TIP]
> Use paths inside the exported view as inputs to your analysis tools,
> just as you would use ordinary file paths.

> [!IMPORTANT]
> Writing to a file through its symlink can modify the original data if
> your permissions allow it. Treat linked files as read-only inputs and
> save analysis outputs elsewhere.

> [!TIP]
> When you no longer need an exported view, remove its directory:
>
> ```bash
> rm -r ~/omnia/my-snapshot
> ```
>
> This removes the view without deleting the linked data or changing the
> catalogue. Check the directory first: any additional files saved inside
> it will also be deleted.

### Inspect metadata from a local snapshot view

Use `omnia describe` inside a mounted or exported snapshot to identify
the snapshot and inspect metadata for your current location.

For example, move into a directory within the view and run:

```bash
cd ~/omnia/my-snapshot/phenotypes
omnia describe
```

Omnia identifies the snapshot automatically and reports its state,
manifest checksum, and metadata for the selected location. For a directory,
it also summarizes its contents, including recursive counts, known size,
and modalities.

You can also provide a local path:

```bash
omnia describe ~/omnia/my-snapshot/phenotypes
```

And obtain a JSON output:

```bash
cd ~/omnia/my-snapshot/phenotypes
omnia describe . --format json
```

## Legacy: list physical storage paths

Use `omnia get` when you specifically need the physical storage paths of
datasets registered in a catalogue:

```bash
omnia get <catalogue-name>
```

To display the paths in JSON format:

```bash
omnia get <catalogue-name> --format json
```

To save the path list to a local file:

```bash
omnia get <catalogue-name> --output catalogue-paths.txt
```

This legacy command lists paths across the catalogue without selecting a
snapshot. Its output may include datasets outside the snapshot you are
using.

> [!TIP]
> For reproducible analyses, use the logical paths provided in the
> data documentation. Record the actual catalogue, snapshot, and paths
> alongside your analysis.
>
> `omnia get` does not select a snapshot and should not be used to choose
> a specific data version.

## Common problems

| Situation                                  | What to do                                                                                              |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------- |
| A snapshot is not listed                   | Check the catalogue name; retired snapshots need `--include-retired`. Draft snapshots are curator-only. |
| A search has no result                     | Quote globs, for example `--name '*sample*'`; try `--path` for parent-directory text.                   |
| `browse ls` says a path is not a directory | Run the suggested `omnia browse describe ...` command.                                                  |
| `omnia describe` cannot find an Omnia view | Run it below an exported/snapshot-mounted root, or use `browse` first.                                  |
| Mount/export rejects a storage root        | Obtain the approved trusted root from the administrator.                                                |
| An exported view already exists            | Choose a new destination or remove only your existing view before exporting again.                      |
| Retired snapshot will not mount            | Check its documented access paths.                                                                      |
| Data marked as deprecated                  | Stop using it and contact the curator.                                                                  |

## What Omnia does not yet provide

Omnia currently assumes access to the catalogue database and trusted shared
storage has already been arranged. It does not yet offer browser-based login,
fine-grained Omnia authorization, direct authenticated per-file downloads, or
a remote GA4GH DRS endpoint. Contact the data steward when you need access
outside the shared environment.
