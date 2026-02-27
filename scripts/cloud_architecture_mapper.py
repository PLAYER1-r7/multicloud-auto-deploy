#!/usr/bin/env python3
"""Collect multicloud resources and render architecture diagrams.

MVP scope:
- AWS / Azure / GCP collection using Pulumi outputs + cloud CLI discovery
- Normalized JSON snapshot output
- Mermaid diagram generation
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PULUMI_DIRS = {
    "aws": REPO_ROOT / "infrastructure" / "pulumi" / "aws",
    "azure": REPO_ROOT / "infrastructure" / "pulumi" / "azure",
    "gcp": REPO_ROOT / "infrastructure" / "pulumi" / "gcp",
}


@dataclass
class Resource:
    provider: str
    resource_type: str
    name: str
    resource_id: str
    region: str | None
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CloudSnapshot:
    provider: str
    pulumi_outputs: dict[str, Any] = field(default_factory=dict)
    resources: list[Resource] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def run_json_command(command: list[str], cwd: Path | None = None) -> Any:
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or result.stdout.strip() or "Command failed"
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Invalid JSON output from command: {' '.join(command)}"
        ) from exc


def run_text_command(command: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or result.stdout.strip() or "Command failed"
        )
    return result.stdout.strip()


def safe_collect(collector: callable, snapshot: CloudSnapshot) -> None:
    try:
        collector(snapshot)
    except Exception as exc:
        snapshot.errors.append(str(exc))


def normalize_name(value: str | None, fallback: str) -> str:
    base = value or fallback
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "-", base)
    cleaned = re.sub(r"-{2,}", "-", cleaned)
    cleaned = cleaned.strip("-_")
    if not cleaned:
        fallback_cleaned = re.sub(r"[^a-zA-Z0-9_-]", "-", fallback)
        fallback_cleaned = re.sub(r"-{2,}", "-", fallback_cleaned).strip("-_")
        cleaned = fallback_cleaned or "node"
    return cleaned[:80]


def append_resource(
    snapshot: CloudSnapshot,
    resource_type: str,
    name: str,
    resource_id: str,
    region: str | None,
    source: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    snapshot.resources.append(
        Resource(
            provider=snapshot.provider,
            resource_type=resource_type,
            name=name,
            resource_id=resource_id,
            region=region,
            source=source,
            metadata=metadata or {},
        )
    )


def collect_pulumi_outputs(snapshot: CloudSnapshot, stack: str) -> None:
    outputs = run_json_command(
        ["pulumi", "stack", "output", "--json", "--stack", stack],
        cwd=PULUMI_DIRS[snapshot.provider],
    )
    snapshot.pulumi_outputs = outputs


def collect_aws(snapshot: CloudSnapshot, stack: str, region: str) -> None:
    collect_pulumi_outputs(snapshot, stack)

    prefix = f"multicloud-auto-deploy-{stack}"

    distributions = run_json_command(
        ["aws", "cloudfront", "list-distributions", "--output", "json"]
    )
    items = distributions.get("DistributionList", {}).get("Items", []) or []
    for dist in items:
        aliases = dist.get("Aliases", {}).get("Items", []) or []
        domain = dist.get("DomainName", "")
        if prefix in domain or any("ashnova.jp" in alias for alias in aliases):
            append_resource(
                snapshot,
                "cdn",
                dist.get("Id", "unknown-cf"),
                dist.get("ARN", dist.get("Id", "unknown-cf")),
                "global",
                "aws-cli",
                {"domain": domain, "aliases": aliases},
            )

    buckets = run_json_command(["aws", "s3api", "list-buckets", "--output", "json"])
    for bucket in buckets.get("Buckets", []) or []:
        name = bucket.get("Name", "")
        if prefix in name or "ashnova" in name:
            append_resource(snapshot, "object_storage", name, name, region, "aws-cli")

    apis = run_json_command(
        ["aws", "apigatewayv2", "get-apis", "--region", region, "--output", "json"]
    )
    for api in apis.get("Items", []) or []:
        name = api.get("Name", "")
        if prefix in name:
            append_resource(
                snapshot,
                "api_gateway",
                name,
                api.get("ApiId", name),
                region,
                "aws-cli",
                {"apiEndpoint": api.get("ApiEndpoint")},
            )

    lambdas = run_json_command(
        ["aws", "lambda", "list-functions", "--region", region, "--output", "json"]
    )
    for fn in lambdas.get("Functions", []) or []:
        fn_name = fn.get("FunctionName", "")
        if prefix in fn_name:
            append_resource(
                snapshot,
                "compute",
                fn_name,
                fn.get("FunctionArn", fn_name),
                region,
                "aws-cli",
            )

    ddb = run_json_command(
        ["aws", "dynamodb", "list-tables", "--region", region, "--output", "json"]
    )
    for table in ddb.get("TableNames", []) or []:
        if prefix in table or table == "simple-sns-messages":
            append_resource(snapshot, "database", table, table, region, "aws-cli")


def collect_azure(snapshot: CloudSnapshot, stack: str, region: str) -> None:
    collect_pulumi_outputs(snapshot, stack)

    prefix = f"multicloud-auto-deploy-{stack}"

    frontdoor_profiles = run_json_command(
        ["az", "afd", "profile", "list", "-o", "json"]
    )
    for profile in frontdoor_profiles:
        name = profile.get("name", "")
        rg = profile.get("resourceGroup", "")
        if prefix in name or f"{stack}-rg" in rg:
            append_resource(
                snapshot, "cdn", name, profile.get("id", name), "global", "az-cli"
            )

    storage_accounts = run_json_command(
        ["az", "storage", "account", "list", "-o", "json"]
    )
    for account in storage_accounts:
        name = account.get("name", "")
        rg = account.get("resourceGroup", "")
        if prefix in rg or name.startswith("mcad"):
            append_resource(
                snapshot,
                "object_storage",
                name,
                account.get("id", name),
                account.get("primaryLocation", region),
                "az-cli",
            )

    function_apps = run_json_command(["az", "functionapp", "list", "-o", "json"])
    for app in function_apps:
        name = app.get("name", "")
        rg = app.get("resourceGroup", "")
        if prefix in name or prefix in rg:
            append_resource(
                snapshot,
                "compute",
                name,
                app.get("id", name),
                app.get("location", region),
                "az-cli",
            )

    cosmos_accounts = run_json_command(["az", "cosmosdb", "list", "-o", "json"])
    for account in cosmos_accounts:
        name = account.get("name", "")
        rg = account.get("resourceGroup", "")
        if prefix in name or prefix in rg:
            append_resource(
                snapshot,
                "database",
                name,
                account.get("id", name),
                account.get("location", region),
                "az-cli",
            )


def collect_gcp(snapshot: CloudSnapshot, stack: str, region: str) -> None:
    collect_pulumi_outputs(snapshot, stack)

    project_id = snapshot.pulumi_outputs.get("gcp_project")
    if not project_id:
        try:
            project_id = run_text_command(["gcloud", "config", "get-value", "project"])
        except Exception:
            project_id = ""

    frontend_prefix = f"ashnova-multicloud-auto-deploy-{stack}"

    backend_buckets = run_json_command(
        ["gcloud", "compute", "backend-buckets", "list", "--format=json"]
    )
    for bucket in backend_buckets:
        name = bucket.get("name", "")
        bucket_name = bucket.get("bucketName", "")
        if stack in name or frontend_prefix in bucket_name:
            append_resource(
                snapshot,
                "cdn",
                name,
                name,
                "global",
                "gcloud-cli",
                {"bucketName": bucket_name},
            )

    url_maps = run_json_command(
        ["gcloud", "compute", "url-maps", "list", "--format=json"]
    )
    for item in url_maps:
        name = item.get("name", "")
        if "multicloud" in name and stack in name:
            append_resource(
                snapshot, "load_balancer", name, name, "global", "gcloud-cli"
            )

    run_services = run_json_command(
        [
            "gcloud",
            "run",
            "services",
            "list",
            "--platform=managed",
            "--region",
            region,
            "--format=json",
        ]
    )
    for service in run_services:
        name = service.get("metadata", {}).get("name", "")
        if stack in name or "multicloud-auto-deploy" in name:
            append_resource(snapshot, "compute", name, name, region, "gcloud-cli")

    buckets = run_json_command(
        ["gcloud", "storage", "buckets", "list", "--format=json"]
    )
    for bucket in buckets:
        name = bucket.get("name", "")
        if frontend_prefix in name:
            append_resource(
                snapshot,
                "object_storage",
                name,
                name,
                bucket.get("location", region),
                "gcloud-cli",
            )

    firestore_dbs = run_json_command(
        [
            "gcloud",
            "firestore",
            "databases",
            "list",
            "--project",
            project_id,
            "--format=json",
        ]
    )
    for db in firestore_dbs:
        db_name = db.get("name", "")
        db_id = db_name.split("/")[-1] if db_name else "default"
        append_resource(
            snapshot, "database", db_id, db_name or db_id, region, "gcloud-cli"
        )


def build_snapshot(
    stack: str, aws_region: str, azure_region: str, gcp_region: str
) -> dict[str, Any]:
    aws_snapshot = CloudSnapshot(provider="aws")
    azure_snapshot = CloudSnapshot(provider="azure")
    gcp_snapshot = CloudSnapshot(provider="gcp")

    safe_collect(lambda s: collect_aws(s, stack=stack, region=aws_region), aws_snapshot)
    safe_collect(
        lambda s: collect_azure(s, stack=stack, region=azure_region), azure_snapshot
    )
    safe_collect(lambda s: collect_gcp(s, stack=stack, region=gcp_region), gcp_snapshot)

    normalized = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "environment": stack,
        "clouds": {
            "aws": {
                "pulumiOutputs": aws_snapshot.pulumi_outputs,
                "resources": [asdict(resource) for resource in aws_snapshot.resources],
                "errors": aws_snapshot.errors,
            },
            "azure": {
                "pulumiOutputs": azure_snapshot.pulumi_outputs,
                "resources": [
                    asdict(resource) for resource in azure_snapshot.resources
                ],
                "errors": azure_snapshot.errors,
            },
            "gcp": {
                "pulumiOutputs": gcp_snapshot.pulumi_outputs,
                "resources": [asdict(resource) for resource in gcp_snapshot.resources],
                "errors": gcp_snapshot.errors,
            },
        },
    }
    return normalized


def first_resource(
    resources: list[dict[str, Any]], resource_type: str
) -> dict[str, Any] | None:
    for item in resources:
        if item.get("resource_type") == resource_type:
            return item
    return None


def render_cloud_lines(provider: str, resources: list[dict[str, Any]]) -> list[str]:
    lines = [f"  subgraph {provider.upper()}[{provider.upper()}]"]
    nodes: list[str] = []
    node_index: dict[tuple[str, str], str] = {}

    mapping = {
        "cdn": "CDN",
        "load_balancer": "LoadBalancer",
        "api_gateway": "ApiGateway",
        "compute": "Compute",
        "database": "Database",
        "object_storage": "ObjectStorage",
    }

    for resource in resources:
        kind = mapping.get(
            resource.get("resource_type", ""), resource.get("resource_type", "Resource")
        )
        resource_type = resource.get("resource_type", "resource")
        rid = normalize_name(
            f"{resource_type}-{resource.get('name')}",
            f"{provider}-{resource_type}-{kind}",
        )
        label = resource.get("name", kind)
        node_index[(resource_type, resource.get("name", ""))] = f"{provider}_{rid}"
        nodes.append(f'    {provider}_{rid}["{kind}: {label}"]')

    lines.extend(nodes)

    cdn = first_resource(resources, "cdn")
    lb = first_resource(resources, "load_balancer")
    storage = first_resource(resources, "object_storage")
    api = first_resource(resources, "api_gateway")
    compute = first_resource(resources, "compute")
    db = first_resource(resources, "database")

    def node_id(resource: dict[str, Any] | None, fallback: str) -> str:
        if not resource:
            return fallback
        key = (resource.get("resource_type", "resource"), resource.get("name", ""))
        return node_index.get(
            key,
            f"{provider}_{normalize_name(f'{resource.get("resource_type", "resource")}-{resource.get("name")}', fallback)}",
        )

    if lb and storage:
        lines.append(f"    {node_id(lb, 'lb')} --> {node_id(storage, 'storage')}")
    if cdn and storage:
        lines.append(f"    {node_id(cdn, 'cdn')} --> {node_id(storage, 'storage')}")
    if api and compute:
        lines.append(f"    {node_id(api, 'api')} --> {node_id(compute, 'compute')}")
    if compute and db:
        lines.append(f"    {node_id(compute, 'compute')} --> {node_id(db, 'database')}")

    lines.append("  end")
    return lines


def render_mermaid(snapshot: dict[str, Any]) -> str:
    aws_resources = snapshot["clouds"]["aws"]["resources"]
    azure_resources = snapshot["clouds"]["azure"]["resources"]
    gcp_resources = snapshot["clouds"]["gcp"]["resources"]

    lines = [
        "flowchart LR",
        "  User((User))",
    ]
    lines.extend(render_cloud_lines("aws", aws_resources))
    lines.extend(render_cloud_lines("azure", azure_resources))
    lines.extend(render_cloud_lines("gcp", gcp_resources))

    for provider, resources in [
        ("aws", aws_resources),
        ("azure", azure_resources),
        ("gcp", gcp_resources),
    ]:
        entry = first_resource(resources, "cdn") or first_resource(
            resources, "load_balancer"
        )
        if entry:
            entry_key = f"{entry.get('resource_type', 'resource')}-{entry.get('name')}"
            entry_id = f"{provider}_{normalize_name(entry_key, provider)}"
            lines.append(f"  User --> {entry_id}")

    return "\n".join(lines) + "\n"


def validate_mermaid(mermaid: str) -> list[str]:
    errors: list[str] = []
    node_ids: set[str] = set()

    for line in mermaid.splitlines():
        node_match = re.match(r'^\s*([A-Za-z0-9_-]+)\["', line)
        if node_match:
            node_id = node_match.group(1)
            node_ids.add(node_id)
            if "--" in node_id:
                errors.append(f"Invalid node id contains '--': {node_id}")

    for line in mermaid.splitlines():
        edge_match = re.match(r"^\s*([A-Za-z0-9_-]+)\s*-->\s*([A-Za-z0-9_-]+)", line)
        if edge_match:
            source = edge_match.group(1)
            target = edge_match.group(2)
            if source not in node_ids and source != "User":
                errors.append(f"Edge source node not defined: {source}")
            if target not in node_ids and target != "User":
                errors.append(f"Edge target node not defined: {target}")

    return errors


def collect_command(args: argparse.Namespace) -> int:
    snapshot = build_snapshot(
        stack=args.environment,
        aws_region=args.aws_region,
        azure_region=args.azure_region,
        gcp_region=args.gcp_region,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Snapshot written: {output_path}")
    return 0


def render_command(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Input snapshot does not exist: {input_path}", file=sys.stderr)
        return 1
    snapshot = json.loads(input_path.read_text(encoding="utf-8"))
    mermaid = render_mermaid(snapshot)
    if args.validate:
        errors = validate_mermaid(mermaid)
        if errors:
            print("Mermaid validation failed:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 2
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(mermaid, encoding="utf-8")
    print(f"Mermaid diagram written: {output_path}")
    return 0


def all_command(args: argparse.Namespace) -> int:
    snapshot = build_snapshot(
        stack=args.environment,
        aws_region=args.aws_region,
        azure_region=args.azure_region,
        gcp_region=args.gcp_region,
    )
    snapshot_path = Path(args.snapshot_output)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(
        json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    mermaid = render_mermaid(snapshot)
    if args.validate:
        errors = validate_mermaid(mermaid)
        if errors:
            print("Mermaid validation failed:", file=sys.stderr)
            for error in errors:
                print(f"  - {error}", file=sys.stderr)
            return 2
    diagram_path = Path(args.diagram_output)
    diagram_path.parent.mkdir(parents=True, exist_ok=True)
    diagram_path.write_text(mermaid, encoding="utf-8")

    print(f"Snapshot written: {snapshot_path}")
    print(f"Mermaid diagram written: {diagram_path}")
    for provider in ["aws", "azure", "gcp"]:
        errors = snapshot["clouds"][provider]["errors"]
        if errors:
            print(f"[{provider}] warnings:")
            for error in errors:
                print(f"  - {error}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Multicloud architecture mapper (MVP)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser(
        "collect", help="Collect normalized JSON snapshot"
    )
    collect_parser.add_argument(
        "--environment", default="staging", choices=["staging", "production"]
    )
    collect_parser.add_argument("--aws-region", default="ap-northeast-1")
    collect_parser.add_argument("--azure-region", default="japaneast")
    collect_parser.add_argument("--gcp-region", default="asia-northeast1")
    collect_parser.add_argument(
        "--output", default="docs/generated/architecture/snapshot.json"
    )
    collect_parser.set_defaults(func=collect_command)

    render_parser = subparsers.add_parser(
        "render", help="Render Mermaid from snapshot JSON"
    )
    render_parser.add_argument(
        "--input", default="docs/generated/architecture/snapshot.json"
    )
    render_parser.add_argument(
        "--output", default="docs/generated/architecture/architecture.mmd"
    )
    render_parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate generated Mermaid node IDs and edges before writing output",
    )
    render_parser.set_defaults(func=render_command)

    all_parser = subparsers.add_parser("all", help="Collect and render in one command")
    all_parser.add_argument(
        "--environment", default="staging", choices=["staging", "production"]
    )
    all_parser.add_argument("--aws-region", default="ap-northeast-1")
    all_parser.add_argument("--azure-region", default="japaneast")
    all_parser.add_argument("--gcp-region", default="asia-northeast1")
    all_parser.add_argument(
        "--snapshot-output", default="docs/generated/architecture/snapshot.json"
    )
    all_parser.add_argument(
        "--diagram-output", default="docs/generated/architecture/architecture.mmd"
    )
    all_parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate generated Mermaid node IDs and edges before writing output",
    )
    all_parser.set_defaults(func=all_command)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
