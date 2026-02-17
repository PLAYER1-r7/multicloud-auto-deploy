# Azure Front Door SKU変更エラーの対処法

## 問題

Azure Front DoorのSKUをPremiumからStandardに変更する際、以下のようなエラーが発生します：

```
error: azure-native:cdn:Profile (frontdoor-profile):
  error: updating existing Profile: autorest/azure: Service returned an error.
  Status=400 Code="InvalidParameter" Message="The SKU cannot be changed from Premium_AzureFrontDoor to Standard_AzureFrontDoor"
```

## 原因

Azure Front Doorは、PremiumからStandardへの**直接ダウングレードをサポートしていません**。SKUを変更するには、リソースを削除して再作成する必要があります。

## 解決策

### 方法1: Pulumi replace（自動）- 推奨

Pulumiコードに`replace_on_changes`オプションを追加済みです。次回のデプロイ時に自動的にリソースが置き換えられます。

```python
frontdoor_profile = azure.cdn.Profile(
    "frontdoor-profile",
    # ...
    opts=pulumi.ResourceOptions(replace_on_changes=["sku"]),
)
```

**実行方法：**
```bash
cd infrastructure/pulumi/azure
pulumi up  # Pulumiが自動的に削除→再作成を実行
```

### 方法2: 手動削除（確実）

既存のFront Doorリソースを完全に削除してから再作成します。

**ステップ1: Azureポータルで確認**
1. https://portal.azure.com にアクセス
2. リソースグループ `multicloud-auto-deploy-staging-rg` を開く
3. Front Door `multicloud-auto-deploy-staging-fd` を確認

**ステップ2: 特定リソースのみ削除**
```bash
cd infrastructure/pulumi/azure

# Front Doorのみを削除（他のリソースは保持）
pulumi destroy --target 'urn:pulumi:staging::multicloud-auto-deploy-azure::azure-native:cdn:Profile::frontdoor-profile'
pulumi destroy --target 'urn:pulumi:staging::multicloud-auto-deploy-azure::azure-native:cdn:AFDEndpoint::frontdoor-endpoint'
pulumi destroy --target 'urn:pulumi:staging::multicloud-auto-deploy-azure::azure-native:cdn:AFDOriginGroup::frontdoor-origin-group'
pulumi destroy --target 'urn:pulumi:staging::multicloud-auto-deploy-azure::azure-native:cdn:AFDOrigin::frontdoor-origin'
pulumi destroy --target 'urn:pulumi:staging::multicloud-auto-deploy-azure::azure-native:cdn:Route::frontdoor-route'

# 新しいStandard SKUで再作成
pulumi up
```

**ステップ3: すべてのAzureリソースを削除して再作成（最終手段）**
```bash
cd infrastructure/pulumi/azure
pulumi destroy  # すべてのリソースを削除
pulumi up      # すべてのリソースを再作成
```

⚠️ 注意: この方法はStorage AccountやKey Vaultも削除されます。本番環境では実行しないでください。

### 方法3: GitHub Actions経由での削除

GitHub Actionsのワークフロー実行時に環境変数を設定して強制削除：

```yaml
# .github/workflows/deploy-azure.ymlで実行
- name: Destroy existing Front Door
  if: github.event.inputs.force_recreate == 'true'
  run: |
    cd infrastructure/pulumi/azure
    pulumi destroy --target '*frontdoor*' --yes
```

## ダウンタイムの影響

Front Doorの削除→再作成には約5-10分かかります。この間、以下の影響があります：

- ✅ **Storage Account**: 影響なし（直接アクセス可能）
- ✅ **Azure Functions**: 影響なし（直接アクセス可能）
- ❌ **Front Door URL**: アクセス不可（削除→再作成中）

## 本番環境での対応

本番環境でダウンタイムを避けるには：

1. **Blue-Green Deployment**: 新しいFront Doorを別名で作成してからDNSを切り替え
2. **Azure Traffic Manager**: Front DoorのフェイルオーバーとしてTraffic Managerを使用
3. **カスタムドメイン**: DNS切り替えでダウンタイムを最小化

## 確認方法

デプロイ成功後、以下で確認：

```bash
# Front Door URLを取得
pulumi stack output frontdoor_url

# curlでアクセステスト
curl -I $(pulumi stack output frontdoor_url)
```

期待される結果：
```
HTTP/2 200
x-azure-ref: ...
```

## トラブルシューティング

### エラー: "Profile cannot be deleted because it has child resources"

**原因**: Front Doorに依存リソース（Endpoint、Origin等）が存在

**解決策**: 依存リソースを先に削除
```bash
pulumi destroy --target '*frontdoor-route*' --yes
pulumi destroy --target '*frontdoor-origin*' --yes
pulumi destroy --target '*frontdoor-origin-group*' --yes
pulumi destroy --target '*frontdoor-endpoint*' --yes
pulumi destroy --target '*frontdoor-profile*' --yes
```

### エラー: "Operation failed with status: 'Conflict'"

**原因**: Azure側でリソース削除が進行中

**解決策**: 5分待ってから再試行
```bash
sleep 300
pulumi up
```

---

**更新日**: 2026年2月15日
