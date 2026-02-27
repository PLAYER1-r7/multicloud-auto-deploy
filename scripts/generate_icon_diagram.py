#!/usr/bin/env python3
"""
公式クラウドアイコン付きHTML図の生成

Mermaid図に公式アイコンを統合したインタラクティブHTMLを生成する。
"""

import argparse
import base64
import json
import sys
from pathlib import Path
from typing import Any

# SVGアイコンテンプレート（プロバイダーとリソースタイプごとの色定義）
ICON_COLORS = {
    "aws": {
        "cdn": "#FF9900",  # AWS Orange
        "compute": "#FF9900",
        "object_storage": "#569A31",  # S3 Green
        "database": "#3B48CC",  # DynamoDB Blue
        "api_gateway": "#FF4F8B",  # API Gateway Pink
        "load_balancer": "#8C4FFF",  # ELB Purple
    },
    "azure": {
        "cdn": "#0089D6",  # Azure Blue
        "compute": "#0072C6",
        "object_storage": "#0072C6",
        "database": "#0072C6",
    },
    "gcp": {
        "cdn": "#4285F4",  # Google Blue
        "compute": "#4285F4",
        "object_storage": "#4285F4",
        "database": "#F9AB00",  # Firestore Yellow
        "load_balancer": "#34A853",  # GCP Green
    },
}


# SVGアイコンジェネレーター（シンプルなクラウドアイコン）
def generate_svg_icon(provider: str, resource_type: str) -> str:
    """リソースタイプに応じたSVGアイコンを生成（data URI形式）"""
    color = ICON_COLORS.get(provider, {}).get(resource_type, "#666666")

    # リソースタイプごとにアイコン形状を変更
    if resource_type in ["cdn", "load_balancer"]:
        # ネットワーク系: グローバルアイコン
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">
            <circle cx="24" cy="24" r="20" fill="{color}" opacity="0.2"/>
            <circle cx="24" cy="24" r="3" fill="{color}"/>
            <circle cx="10" cy="24" r="2.5" fill="{color}"/>
            <circle cx="38" cy="24" r="2.5" fill="{color}"/>
            <circle cx="24" cy="10" r="2.5" fill="{color}"/>
            <circle cx="24" cy="38" r="2.5" fill="{color}"/>
            <line x1="24" y1="24" x2="10" y2="24" stroke="{color}" stroke-width="2"/>
            <line x1="24" y1="24" x2="38" y2="24" stroke="{color}" stroke-width="2"/>
            <line x1="24" y1="24" x2="24" y2="10" stroke="{color}" stroke-width="2"/>
            <line x1="24" y1="24" x2="24" y2="38" stroke="{color}" stroke-width="2"/>
        </svg>'''
    elif resource_type == "compute":
        # コンピュート: サーバーアイコン
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">
            <rect x="8" y="14" width="32" height="20" rx="2" fill="{color}" opacity="0.2"/>
            <rect x="8" y="14" width="32" height="20" rx="2" fill="none" stroke="{color}" stroke-width="2"/>
            <circle cx="14" cy="20" r="1.5" fill="{color}"/>
            <circle cx="19" cy="20" r="1.5" fill="{color}"/>
            <rect x="12" y="24" width="24" height="2" fill="{color}"/>
            <rect x="12" y="28" width="18" height="2" fill="{color}"/>
        </svg>'''
    elif resource_type == "object_storage":
        # ストレージ: バケツアイコン
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">
            <path d="M14 12 L34 12 L38 36 L10 36 Z" fill="{color}" opacity="0.2"/>
            <path d="M14 12 L34 12 L38 36 L10 36 Z" fill="none" stroke="{color}" stroke-width="2"/>
            <ellipse cx="24" cy="12" rx="10" ry="3" fill="{color}" opacity="0.3"/>
            <line x1="10" y1="20" x2="38" y2="20" stroke="{color}" stroke-width="1.5" opacity="0.5"/>
            <line x1="11" y1="28" x2="37" y2="28" stroke="{color}" stroke-width="1.5" opacity="0.5"/>
        </svg>'''
    elif resource_type == "database":
        # データベース: シリンダーアイコン
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">
            <ellipse cx="24" cy="15" rx="12" ry="5" fill="{color}" opacity="0.3"/>
            <rect x="12" y="15" width="24" height="18" fill="{color}" opacity="0.2"/>
            <ellipse cx="24" cy="15" rx="12" ry="5" fill="none" stroke="{color}" stroke-width="2"/>
            <path d="M12 15 L12 33 Q12 38 24 38 Q36 38 36 33 L36 15" fill="none" stroke="{color}" stroke-width="2"/>
            <ellipse cx="24" cy="24" rx="12" ry="4" fill="none" stroke="{color}" stroke-width="1.5" opacity="0.6"/>
        </svg>'''
    elif resource_type == "api_gateway":
        # API Gateway: ゲートウェイアイコン
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">
            <rect x="10" y="10" width="28" height="28" rx="4" fill="{color}" opacity="0.2"/>
            <rect x="10" y="10" width="28" height="28" rx="4" fill="none" stroke="{color}" stroke-width="2"/>
            <path d="M20 18 L28 24 L20 30" fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>'''
    else:
        # デフォルト: クラウドアイコン
        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48">
            <path d="M38 28 Q38 22 33 19 Q33 14 28 12 Q24 10 20 12 Q16 14 14 18 Q10 18 8 21 Q6 24 6 27 Q6 31 9 33 Q12 35 15 35 L35 35 Q38 35 40 32 Q42 29 42 26 Q42 23 40 21 Q38 19 35 19" fill="{color}" opacity="0.3"/>
            <path d="M38 28 Q38 22 33 19 Q33 14 28 12 Q24 10 20 12 Q16 14 14 18 Q10 18 8 21 Q6 24 6 27 Q6 31 9 33 Q12 35 15 35 L35 35 Q38 35 40 32 Q42 29 42 26 Q42 23 40 21 Q38 19 35 19" fill="none" stroke="{color}" stroke-width="2"/>
        </svg>'''

    # SVGをdata URIに変換
    svg_bytes = svg.encode("utf-8")
    b64 = base64.b64encode(svg_bytes).decode("utf-8")
    return f"data:image/svg+xml;base64,{b64}"


def load_official_icon(provider: str, resource_type: str) -> str:
    """公式アイコンSVGファイルを読み込んでdata URIに変換"""
    icon_dir = Path(__file__).parent.parent / "assets" / "icons"

    # AWSアイコンマッピング
    aws_icon_map = {
        "cdn": "cloudfront.svg",
        "compute": "lambda.svg",
        "object_storage": "s3.svg",
        "database": "dynamodb.svg",
        "api_gateway": "api-gateway.svg",
        "load_balancer": "cloudfront.svg",  # ELBの代わりにCloudFrontを使用
    }

    # GCPアイコンマッピング
    gcp_icon_map = {
        "cdn": "cdn.svg",
        "compute": "run.svg",
        "object_storage": "storage.svg",
        "database": "firestore.svg",
        "load_balancer": "load-balancer.svg",
    }

    icon_map = {}
    if provider == "aws":
        icon_map = aws_icon_map
    elif provider == "gcp":
        icon_map = gcp_icon_map

    if provider in ["aws", "gcp"] and resource_type in icon_map:
        icon_path = icon_dir / provider / icon_map[resource_type]
        if icon_path.exists():
            svg_content = icon_path.read_text(encoding="utf-8")
            svg_bytes = svg_content.encode("utf-8")
            b64 = base64.b64encode(svg_bytes).decode("utf-8")
            return f"data:image/svg+xml;base64,{b64}"

    # フォールバック: カスタムSVGアイコンを生成
    return generate_svg_icon(provider, resource_type)


def get_icon_url(provider: str, resource_type: str) -> str:
    """リソースタイプに対応するアイコンURLを取得（公式SVG優先、フォールバックはカスタムSVG）"""
    return load_official_icon(provider, resource_type)


def generate_html_diagram(
    snapshot: dict[str, Any],
    mermaid_code: str,
    output_path: Path,
    title: str = "Cloud Architecture Diagram",
) -> None:
    """
    公式アイコン付きHTML図を生成

    アプローチ:
    1. Mermaid.jsでベース図を描画
    2. カスタムCSSでノードにアイコンを追加
    3. インタラクティブな凡例を追加
    """

    # リソース情報を収集
    resources_by_provider = {}
    resource_icon_map = {}  # {provider}:{resource_type} → アイコンURL のマッピング

    for provider in ["aws", "azure", "gcp"]:
        resources = snapshot.get("clouds", {}).get(provider, {}).get("resources", [])
        resources_by_provider[provider] = resources

        # 各リソースタイプのアイコンマッピングを作成
        resource_types = set(
            r.get("resource_type") for r in resources if r.get("resource_type")
        )
        for resource_type in resource_types:
            icon_url = get_icon_url(provider, resource_type)
            key = f"{provider}:{resource_type}"
            resource_icon_map[key] = icon_url

    # アイコン凡例を生成
    legend_items = []
    for provider, resources in resources_by_provider.items():
        resource_types = set(
            r.get("resource_type") for r in resources if r.get("resource_type")
        )
        for rt in sorted(resource_types):
            icon_url = get_icon_url(provider, rt)
            legend_items.append(
                {
                    "provider": provider.upper(),
                    "type": rt,
                    "icon": icon_url,
                    "label": rt.replace("_", " ").title(),
                }
            )

    html_template = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'default',
            flowchart: {{
                htmlLabels: true,
                curve: 'basis'
            }}
        }});

        // リソースアイコンマッピング
        const resourceIcons = {json.dumps(resource_icon_map, ensure_ascii=False)};

        // Mermaidレンダリング後にアイコンを追加
        window.addEventListener('load', () => {{
            setTimeout(() => {{
                const svg = document.querySelector('.mermaid svg');
                if (!svg) return;

                // 全てのノードを取得
                const nodes = svg.querySelectorAll('.node');
                nodes.forEach(node => {{
                    // ノードのid属性からプロバイダーとリソースタイプを抽出
                    // パターン: flowchart-{{provider}}_{{resource_type}}-{{name}}-{{index}}
                    const nodeId = node.id || '';
                    const match = nodeId.match(/flowchart-([a-z]+)_([a-z_]+)-/);

                    if (!match) return;

                    const provider = match[1];  // aws, azure, gcp
                    const resourceType = match[2];  // cdn, compute, object_storage, etc.

                    // アイコンURLを取得
                    const iconUrl = resourceIcons[`${{provider}}:${{resourceType}}`];
                    if (!iconUrl) return;

                    // ノードの矩形要素を取得
                    const rect = node.querySelector('rect');
                    if (!rect) return;

                    const x = parseFloat(rect.getAttribute('x') || 0);
                    const y = parseFloat(rect.getAttribute('y') || 0);

                    // アイコンをSVG imageとして追加（左上に配置）
                    const iconSize = 28;
                    const padding = 6;
                    const image = document.createElementNS('http://www.w3.org/2000/svg', 'image');
                    image.setAttributeNS('http://www.w3.org/1999/xlink', 'href', iconUrl);
                    image.setAttribute('x', x + padding);
                    image.setAttribute('y', y + padding);
                    image.setAttribute('width', iconSize);
                    image.setAttribute('height', iconSize);
                    image.style.pointerEvents = 'none';

                    // ノードグループの最後に挿入（テキストの上に表示）
                    node.appendChild(image);
                }});
            }}, 800);  // Mermaidのレンダリング完了を待つ
        }});
    </script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 2rem;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            text-align: center;
        }}
        .header h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}
        .header p {{
            opacity: 0.9;
            font-size: 0.95rem;
        }}
        .content {{
            display: grid;
            grid-template-columns: 250px 1fr;
            gap: 2rem;
            padding: 2rem;
        }}
        .sidebar {{
            background: #f8f9fa;
            padding: 1.5rem;
            border-radius: 8px;
            height: fit-content;
            position: sticky;
            top: 2rem;
        }}
        .sidebar h2 {{
            font-size: 1.1rem;
            margin-bottom: 1rem;
            color: #333;
        }}
        .legend {{
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
            padding: 0.5rem;
            background: white;
            border-radius: 6px;
            border: 1px solid #e0e0e0;
            transition: all 0.2s;
        }}
        .legend-item:hover {{
            border-color: #667eea;
            box-shadow: 0 2px 8px rgba(102,126,234,0.2);
        }}
        .legend-icon {{
            width: 32px;
            height: 32px;
            object-fit: contain;
            flex-shrink: 0;
        }}
        .legend-text {{
            flex: 1;
        }}
        .legend-provider {{
            font-size: 0.7rem;
            color: #666;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .legend-label {{
            font-size: 0.85rem;
            color: #333;
            font-weight: 500;
        }}
        .diagram {{
            background: white;
            padding: 2rem;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
            overflow-x: auto;
        }}
        .mermaid {{
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 600px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1rem;
            margin-top: 1.5rem;
        }}
        .stat-card {{
            background: white;
            padding: 1rem;
            border-radius: 6px;
            border: 1px solid #e0e0e0;
            text-align: center;
        }}
        .stat-number {{
            font-size: 1.5rem;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 0.25rem;
        }}
        .stat-label {{
            font-size: 0.75rem;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        @media (max-width: 1024px) {{
            .content {{
                grid-template-columns: 1fr;
            }}
            .sidebar {{
                position: static;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏗️ {title}</h1>
            <p>AWS・Azure・GCP マルチクラウドアーキテクチャ（公式アイコン表示）</p>
        </div>
        <div class="content">
            <aside class="sidebar">
                <h2>📋 アイコン凡例</h2>
                <div class="legend">
                    {
        "".join(
            f'''
                    <div class="legend-item">
                        <img src="{item['icon']}" alt="{item['label']}" class="legend-icon" loading="lazy">
                        <div class="legend-text">
                            <div class="legend-provider">{item['provider']}</div>
                            <div class="legend-label">{item['label']}</div>
                        </div>
                    </div>
                    '''
            for item in legend_items
        )
    }
                </div>
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-number">{
        len(resources_by_provider.get("aws", []))
    }</div>
                        <div class="stat-label">AWS</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{
        len(resources_by_provider.get("azure", []))
    }</div>
                        <div class="stat-label">Azure</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{
        len(resources_by_provider.get("gcp", []))
    }</div>
                        <div class="stat-label">GCP</div>
                    </div>
                </div>
            </aside>
            <main>
                <div class="diagram">
                    <pre class="mermaid">
{mermaid_code.strip()}
                    </pre>
                </div>
            </main>
        </div>
    </div>
</body>
</html>"""

    output_path.write_text(html_template, encoding="utf-8")
    print(f"HTML diagram with official icons written: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate HTML diagram with official cloud icons"
    )
    parser.add_argument(
        "--snapshot",
        default="docs/generated/architecture/snapshot.staging.json",
        help="Snapshot JSON file",
    )
    parser.add_argument(
        "--mermaid", help="Mermaid diagram file (auto-detected if not specified)"
    )
    parser.add_argument(
        "--output", help="Output HTML file (auto-generated if not specified)"
    )
    parser.add_argument("--title", default="Cloud Architecture", help="Diagram title")
    args = parser.parse_args()

    snapshot_path = Path(args.snapshot)
    if not snapshot_path.exists():
        print(f"Error: Snapshot file not found: {snapshot_path}", file=sys.stderr)
        sys.exit(1)

    # Mermaid図のパスを自動検出
    if args.mermaid:
        mermaid_path = Path(args.mermaid)
    else:
        # snapshot.staging.json → architecture.staging.mmd
        mermaid_path = snapshot_path.parent / snapshot_path.name.replace(
            "snapshot", "architecture"
        ).replace(".json", ".mmd")

    if not mermaid_path.exists():
        print(f"Error: Mermaid file not found: {mermaid_path}", file=sys.stderr)
        sys.exit(1)

    # Output HTML path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = mermaid_path.with_suffix(".html")

    # Load files
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    mermaid_code = mermaid_path.read_text(encoding="utf-8")

    # Extract Mermaid code from ```mermaid block if present
    if "```mermaid" in mermaid_code:
        mermaid_code = mermaid_code.split("```mermaid")[1].split("```")[0]

    # Generate HTML
    generate_html_diagram(snapshot, mermaid_code, output_path, args.title)
