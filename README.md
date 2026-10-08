# Omnia

Omnia is a MongoDB-backed catalogue for scientific data assets. It separates
physical storage from curated, versioned logical views that scientists can
browse, mount, or export without copying data.

## Documentation

Choose the guide that matches your role:

- [Administrator and curator guide](docs/administrator-curator.md): create
  catalogues, ingest and curate trees, manage manifests, version releases,
  replace updated modalities, publish, retire, mount, and export views.
- [Data user guide](docs/data-user.md): browse published releases, search and
  inspect logical paths, use JSON/TSV output, mount/export data, and describe
  the current view.

## Quick start

Curators publish a versioned tree:

```bash
omnia catalogue create example-project --description "Example project data"
omnia tree ingest example-project /processing/example-project example-project_20261001 \
  --manifest project-manifest.yaml
omnia tree validate example-project example-project_20261001
omnia tree publish example-project example-project_20261001
```

Users discover and inspect that release:

```bash
omnia browse snapshots example-project
omnia browse find example-project example-project_20261001 --modality genotype --kind file
omnia browse describe example-project example-project_20261001 genotypes
```

Use `omnia --help` or the role-specific guides for the full command reference
and operational guidance.
