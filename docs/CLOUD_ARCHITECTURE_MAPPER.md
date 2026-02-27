# Cloud Architecture Mapper (MVP)

This tool collects current resource information from AWS, Azure, and GCP,
normalizes it into JSON, and renders a Mermaid system architecture diagram.

## Why this tool exists

- Build a single architecture snapshot from live cloud resources
- Cross-check Pulumi expected state vs actual cloud resources
- Generate a portable diagram artifact (`.mmd`) for documentation and reviews

## File

- `scripts/cloud_architecture_mapper.py`
- `scripts/refresh-architecture.sh`

## Prerequisites

- Pulumi CLI authenticated (`pulumi login`)
- AWS CLI authenticated (`aws sts get-caller-identity`)
- Azure CLI authenticated (`az account show`)
- GCP CLI authenticated (`gcloud auth list`)
- Access to stack outputs for:
  - `infrastructure/pulumi/aws`
  - `infrastructure/pulumi/azure`
  - `infrastructure/pulumi/gcp`

## Commands

### Collect normalized snapshot JSON

```bash
python3 scripts/cloud_architecture_mapper.py collect \
  --environment staging \
  --output docs/generated/architecture/snapshot.json
```

### Render Mermaid from an existing snapshot

```bash
python3 scripts/cloud_architecture_mapper.py render \
  --input docs/generated/architecture/snapshot.json \
  --output docs/generated/architecture/architecture.mmd

# Validate Mermaid node IDs / edges before write
python3 scripts/cloud_architecture_mapper.py render \
  --input docs/generated/architecture/snapshot.json \
  --output docs/generated/architecture/architecture.mmd \
  --validate
```

### One-shot collection + rendering

```bash
python3 scripts/cloud_architecture_mapper.py all \
  --environment staging \
  --snapshot-output docs/generated/architecture/snapshot.json \
  --diagram-output docs/generated/architecture/architecture.mmd \
  --validate
```

### Refresh via helper script

```bash
./scripts/refresh-architecture.sh staging
```

### VS Code tasks

- `architecture: refresh (staging)`
- `architecture: validate (render)`

## Outputs

- `docs/generated/architecture/snapshot.json`
  - `clouds.<provider>.pulumiOutputs`: Pulumi stack outputs
  - `clouds.<provider>.resources`: normalized resources
  - `clouds.<provider>.errors`: collection warnings/errors
- `docs/generated/architecture/architecture.mmd`
  - Mermaid `flowchart LR` diagram with provider subgraphs

## Current MVP coverage

- AWS: CloudFront, S3, API Gateway v2, Lambda, DynamoDB
- Azure: Front Door profile, Storage Account, Function App, Cosmos DB
- GCP: Backend Bucket / URL Map, Cloud Run, GCS, Firestore

## Notes

- The collector is intentionally read-only and uses list/get APIs.
- If one cloud collection fails, the tool still writes snapshot/diagram with warnings.
- `--validate` checks Mermaid node ID safety and edge references, and exits with non-zero status when invalid.
- This is an MVP foundation for future diff and drift analysis.
