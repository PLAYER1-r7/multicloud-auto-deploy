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

### Combined diagram (staging + production)

```bash
# Generate snapshots separately
python3 scripts/cloud_architecture_mapper.py collect \
  --environment staging \
  --output docs/generated/architecture/snapshot.staging.json

python3 scripts/cloud_architecture_mapper.py collect \
  --environment production \
  --output docs/generated/architecture/snapshot.production.json

# Render a single overlay diagram
python3 scripts/cloud_architecture_mapper.py compare \
  --staging-input docs/generated/architecture/snapshot.staging.json \
  --production-input docs/generated/architecture/snapshot.production.json \
  --output docs/generated/architecture/architecture-combined.mmd \
  --validate
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

---

## Interactive HTML Diagram Generator

### Overview

`scripts/generate_icon_diagram.py` generates interactive HTML architecture diagrams with official cloud service icons embedded. This tool enhances the basic Mermaid diagrams with:

- **Official SVG icons** from AWS, Azure, and GCP
- **Interactive flowchart nodes** with icons embedded in-node (top-left corner)
- **Base64-encoded data URIs** for zero external dependencies
- **Responsive sidebar legend** with resource counts

### Features

- ✅ Official AWS Architecture Icons (48px SVG, Q3-2021 package)
- ✅ Official Azure Public Service Icons V14 (18px SVG with gradients)
- ✅ Official GCP Product Icons (SVG)
- ✅ JavaScript icon injection into Mermaid-rendered nodes
- ✅ No external CDN dependencies (all icons embedded)
- ✅ Separate diagrams for staging, production, and combined view

### Icon Assets

Icons are stored in `assets/icons/{provider}/`:

```
assets/icons/
├── aws/
│   ├── cloudfront.svg      (AWS CloudFront)
│   ├── lambda.svg          (AWS Lambda)
│   ├── s3.svg              (Amazon S3)
│   ├── dynamodb.svg        (Amazon DynamoDB)
│   └── api-gateway.svg     (Amazon API Gateway)
├── azure/
│   ├── cdn.svg             (Azure Front Door)
│   ├── function.svg        (Azure Functions)
│   ├── storage.svg         (Azure Storage Account)
│   └── cosmos-db.svg       (Azure Cosmos DB)
└── gcp/
    ├── cdn.svg             (Cloud CDN)
    ├── run.svg             (Cloud Run)
    ├── storage.svg         (Cloud Storage)
    ├── firestore.svg       (Cloud Firestore)
    └── load-balancer.svg   (Cloud Load Balancer)
```

**Total size**: ~50KB (14KB AWS + 16KB Azure + 20KB GCP)  
**Format**: SVG (embedded as Base64 data URIs in HTML)  
**Source**:
- AWS: [AWS Architecture Icons Asset Package](https://aws.amazon.com/architecture/icons/)
- Azure: [Azure Public Service Icons V14](https://learn.microsoft.com/azure/architecture/icons/)
- GCP: [Google Cloud Icons](https://cloud.google.com/icons)

### Usage

```bash
# Generate staging environment diagram
python3 scripts/generate_icon_diagram.py staging

# Generate production environment diagram
python3 scripts/generate_icon_diagram.py production

# Generate combined (staging + production) diagram
python3 scripts/generate_icon_diagram.py combined
```

### Outputs

Generated HTML files in `docs/generated/architecture/`:

- `architecture.staging.html` (~85KB) - Staging environment with official icons
- `architecture.production.html` (~85KB) - Production environment with official icons
- `architecture-combined.html` (~91KB) - Staging + Production overlay with color-coded nodes

Each HTML file includes:
- Embedded Mermaid.js v10 (ESM module)
- Base64-encoded SVG icons (no external requests)
- JavaScript DOM manipulation for icon injection
- Interactive legend sidebar with resource counts
- Responsive layout (CSS Grid)

### Technical Details

**Icon Loading**:
```python
def load_official_icon(provider: str, resource_type: str) -> str:
    """Load official SVG icon and return Base64 data URI"""
    # Icon mappings for AWS, Azure, GCP
    # Returns: data:image/svg+xml;base64,PHN2Zy...
```

**Icon Injection (JavaScript)**:
```javascript
// Pattern: flowchart-{provider}_{resource_type}-{name}-{index}
const nodeId = node.id;
const match = nodeId.match(/flowchart-([a-z]+)_([a-z_]+)-/);
if (match && icons[match[1]] && icons[match[1]][match[2]]) {
  // Inject <image> element at (x+6, y+6) with 28x28px size
  rect.parentNode.insertBefore(iconElement, rect.nextSibling);
}
```

**Node ID Convention**:
- Pattern: `flowchart-{provider}_{resource_type}-{name}-{index}`
- Examples: `flowchart-aws_cdn-E1TBH4R432SZBZ-0`, `flowchart-azure_compute-mcadfuncdiev0w-1`
- Provider: `aws` | `azure` | `gcp`
- Resource types: `cdn`, `object_storage`, `serverless_function`, `database`, `api_gateway`, `load_balancer`, `compute`

### Known Limitations

- Icons assume 48x48px source size (scaled to 28x28px in nodes)
- Injection timing requires 800ms setTimeout for Mermaid rendering
- No icon caching (data URIs embedded in each HTML file)
- Resource type mapping is manually maintained in `load_official_icon()`

### Resource Analysis

The tool can identify isolated/orphaned resources (nodes with no connections). As of 2026-02-27:

**13 isolated resources** identified across staging:
- ❌ **Delete candidates** (5): `multicloud-auto-deploy-staging-posts` (AWS DynamoDB), 4 Azure Storage Accounts not in Pulumi
- ✅ **In use but unconnected** (2): GCP function-source bucket, uploads bucket
- ❓ **Needs verification** (6): 3 AWS CloudFront distributions for ashnova.jp domains, GCP landing bucket, 2 others

> **Note**: Resource cleanup postponed pending further investigation (2026-02-27)
