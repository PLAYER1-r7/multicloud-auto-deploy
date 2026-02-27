#!/usr/bin/env python3
"""
公式クラウドアイコンの取得スクリプト

AWS/Azure/GCPの公式アイコンをダウンロードまたはCDN経由で参照する。
"""

import json
import urllib.request
from pathlib import Path

# 公式アイコンCDN/URLマッピング
# 実際のアイコンは各クラウドプロバイダーの公式リポジトリから取得
ICON_SOURCES = {
    "aws": {
        # AWS Architecture Icons
        # https://aws.amazon.com/architecture/icons/
        "cdn": "https://d1.awsstatic.com/webteam/architecture-icons/q3-2021/Arch_Networking-Content-Delivery/48/Arch_Amazon-CloudFront_48.svg",
        "compute": "https://d1.awsstatic.com/webteam/architecture-icons/q3-2021/Arch_Compute/48/Arch_AWS-Lambda_48.svg",
        "object_storage": "https://d1.awsstatic.com/webteam/architecture-icons/q3-2021/Arch_Storage/48/Arch_Amazon-Simple-Storage-Service_48.svg",
        "database": "https://d1.awsstatic.com/webteam/architecture-icons/q3-2021/Arch_Database/48/Arch_Amazon-DynamoDB_48.svg",
        "api_gateway": "https://d1.awsstatic.com/webteam/architecture-icons/q3-2021/Arch_App-Integration/48/Arch_Amazon-API-Gateway_48.svg",
    },
    "azure": {
        # Azure Architecture Icons
        # https://docs.microsoft.com/en-us/azure/architecture/icons/
        "cdn": "https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/1-CONTRIBUTION-GUIDE/images/cdn.svg",
        "compute": "https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/1-CONTRIBUTION-GUIDE/images/function.svg",
        "object_storage": "https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/1-CONTRIBUTION-GUIDE/images/storage-accounts.svg",
        "database": "https://raw.githubusercontent.com/Azure/azure-quickstart-templates/master/1-CONTRIBUTION-GUIDE/images/cosmos-db.svg",
    },
    "gcp": {
        # Google Cloud Icons
        # https://cloud.google.com/icons
        "cdn": "https://www.gstatic.com/images/branding/productlogos/cloud_cdn/v1/web-48dp/logo_cloud_cdn_color_1x_web_48dp.png",
        "compute": "https://www.gstatic.com/images/branding/productlogos/cloud_run/v1/web-48dp/logo_cloud_run_color_1x_web_48dp.png",
        "object_storage": "https://www.gstatic.com/images/branding/productlogos/cloud_storage/v1/web-48dp/logo_cloud_storage_color_1x_web_48dp.png",
        "database": "https://www.gstatic.com/images/branding/productlogos/firestore/v1/web-48dp/logo_firestore_color_1x_web_48dp.png",
    },
}


def download_icon(url: str, output_path: Path) -> bool:
    """アイコンをダウンロード"""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, output_path)
        return True
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return False


def generate_icon_config(output_path: Path) -> None:
    """アイコン設定ファイルを生成（CDN URL参照）"""
    config = {
        "version": "1.0",
        "description": "Cloud service icon mapping for architecture diagrams",
        "icons": ICON_SOURCES,
    }
    output_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"Icon config generated: {output_path}")


if __name__ == "__main__":
    # アイコン設定を生成
    config_path = Path("assets/icons/icon_config.json")
    generate_icon_config(config_path)

    # 必要に応じてアイコンをローカルにダウンロード
    # download_all = input("Download all icons locally? (y/N): ").lower() == 'y'
    # if download_all:
    #     for provider, icons in ICON_SOURCES.items():
    #         for resource_type, url in icons.items():
    #             local_path = Path(f"assets/icons/{provider}/{resource_type}.svg")
    #             download_icon(url, local_path)
