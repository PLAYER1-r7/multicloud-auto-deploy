# ランディングページとSNS統合テスト レポート

**実施日時**: 2026-03-03
**実施者**: AI Agent
**テスト範囲**: ランディングページ + SNS統合テスト (Production → Staging)

---

## エグゼクティブサマリー

| 環境 | クラウド | ランディングページ | SNS App | API Health | 総合状態 |
|------|---------|-------------------|---------|-----------|---------|
| **Production** | AWS | ✅ 200 | ✅ 200 | ✅ 200 | ✅ PASS |
| **Production** | Azure | ✅ 200 | ✅ 200 | ✅ 200 | ✅ PASS |
| **Production** | GCP | ✅ 200 | ✅ 200 | ✅ 200 | ✅ PASS |
| **Staging** | AWS | ⚠️ 403 | ⚠️ 403 | ✅ 200 | ⚠️ PARTIAL |
| **Staging** | Azure | ✅ 200 | ✅ 200 | ✅ 200 | ✅ PASS |
| **Staging** | GCP | ✅ 200 | ✅ 200 | ✅ 200 | ✅ PASS |

### 主な発見事項

1. **✅ 本番環境は完全動作** - 全3クラウドで100%成功
2. **⚠️ AWSステージングCloudFrontに403エラー** - S3オリジンアクセス設定の問題
3. **✅ 全てのAPIエンドポイントは正常** - バックエンドは問題なし
4. **🔧 テストスクリプト修正** - CloudFrontドメイン名を最新に更新

---

## 詳細テスト結果

### 1. 本番環境（Production）

#### 1.1 ランディングページテスト

```bash
./scripts/test-landing-pages.sh --env production
```

**結果**: ✅ **全テスト通過** (36/36)

| クラウド | HTTP | Response Time | Content-Type | Size | Cache-Control |
|---------|------|--------------|--------------|------|---------------|
| AWS | 200 | 268ms | text/html | 5681B | public, max-age=3600 |
| Azure | 200 | 106ms | text/html | 5470B | public, max-age=3600 |
| GCP | 200 | 145ms | text/html | 6683B | public, max-age=3600 |

**検証項目**:
- ✅ HTTP 200 レスポンス
- ✅ Content-Type: text/html
- ✅ ブランド名 "Ashnova" 存在
- ✅ クラウドバッジ表示（AWS/Azure/GCP）
- ✅ SNS app リンク存在
- ✅ localhost 参照なし（環境変数正常注入）
- ✅ HTTPS 維持
- ✅ Cache-Control ヘッダー設定
- ✅ /sns/ パス動作確認

#### 1.2 SNS統合テスト（クイックモード）

```bash
./scripts/test-sns-all.sh --env production --quick
```

**結果**: ✅ **全テスト通過** (9/9)

| クラウド | Landing Page | SNS App | API /health |
|---------|--------------|---------|------------|
| AWS | ✅ 200 | ✅ 200 | ✅ 200 |
| Azure | ✅ 200 | ✅ 200 | ✅ 200 |
| GCP | ✅ 200 | ✅ 200 | ✅ 200 |

**エンドポイント**:
- AWS: `https://www.aws.ashnova.jp` + `https://qkzypr32af.execute-api.ap-northeast-1.amazonaws.com`
- Azure: `https://www.azure.ashnova.jp` + `https://multicloud-auto-deploy-production-func-cfdne7ecbngnh0d0.japaneast-01.azurewebsites.net/api`
- GCP: `https://www.gcp.ashnova.jp` + `https://multicloud-auto-deploy-production-api-son5b3ml7a-an.a.run.app`

---

### 2. ステージング環境（Staging）

#### 2.1 ランディングページテスト

```bash
./scripts/test-landing-pages.sh --env staging
```

**結果**: ⚠️ **部分的成功** (28/36)

| クラウド | HTTP | Response Time | Content-Type | Size | 状態 |
|---------|------|--------------|--------------|------|-----|
| AWS | ❌ 403 | 149ms | - | 0B | **FAIL** |
| Azure | 200 | 183ms | text/html | 5470B | **PASS** |
| GCP | 200 | 46ms | text/html | 6683B | **PASS** |

**AWS失敗要因**: CloudFront経由でS3が403を返却
- エラーレスポンスヘッダー: `server: AmazonS3`, `x-cache: Error from cloudfront`
- 原因推定: S3バケットポリシーまたはCloudFront OAI/OAC設定の問題

#### 2.2 SNS統合テスト（クイックモード）

```bash
./scripts/test-sns-all.sh --env staging --quick
```

**結果**: ⚠️ **部分的成功** (7/9)

| クラウド | Landing Page | SNS App | API /health |
|---------|--------------|---------|------------|
| AWS | ❌ 403 | ❌ 403 | ✅ 200 |
| Azure | ✅ 200 | ✅ 200 | ✅ 200 |
| GCP | ✅ 200 | ✅ 200 | ✅ 200 |

**エンドポイント**:
- AWS: `https://d1m9oyy27szoic.cloudfront.net` + `https://z42qmqdqac.execute-api.ap-northeast-1.amazonaws.com`
- Azure: `https://mcad-staging-d45ihd-dseygrc9c3a3htgj.z01.azurefd.net` + `https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api`
- GCP: `https://www.gcp.ashnova.jp` + `https://multicloud-auto-deploy-staging-api-son5b3ml7a-an.a.run.app`

**注**: AWSのAPIエンドポイントは正常動作（バックエンドは問題なし）

---

## 修正事項

### スクリプト修正

#### 1. `test-sns-all.sh` - URL変数展開の問題修正

**問題**: コマンド置換のネスト構造により、URLにスペースが混入していた
**症状**: `curl exit code: 3` (URL malformed)
**修正**: if文による明示的な分岐に書き換え

```bash
# Before (問題あり)
local aws_cf="${AWS_CF_URL:-$([[ "$_env" == "production" ]] && echo "https://..." || echo "https://...") }"

# After (修正後)
if [[ "$_env" == "production" ]]; then
  aws_cf="${AWS_CF_URL:-https://www.aws.ashnova.jp}"
else
  aws_cf="${AWS_CF_URL:-https://d1m9oyy27szoic.cloudfront.net}"
fi
```

**影響範囲**: 全環境変数（aws_cf, aws_api, azure_fd, azure_api, gcp_cdn, gcp_api）

#### 2. CloudFrontドメイン名更新

**旧**: `d1tf3uumcm4bo1.cloudfront.net` (DNS解決不可)
**新**: `d1m9oyy27szoic.cloudfront.net` (現在のDistribution ID: EZEKNOK0BOTVA)

**確認コマンド**:
```bash
aws cloudfront list-distributions \
  --query "DistributionList.Items[?contains(Comment, 'staging')].{ID:Id, DomainName:DomainName}" \
  --output table
```

**更新ファイル**:
- `scripts/test-sns-all.sh`
- `scripts/test-landing-pages.sh`

---

## 既知の問題と推奨アクション

### 🔴 HIGH: AWSステージングCloudFront 403エラー

**症状**:
```
HTTP/2 403
content-type: application/xml
server: AmazonS3
x-cache: Error from cloudfront
```

**根本原因**:
- CloudFront Distribution `EZEKNOK0BOTVA` からS3バケット `multicloud-auto-deploy-staging-frontend` へのアクセスが拒否されている
- OAI (Origin Access Identity) または OAC (Origin Access Control) の設定が不完全

**推奨修正手順**:

1. **S3バケットポリシー確認**:
```bash
aws s3api get-bucket-policy \
  --bucket multicloud-auto-deploy-staging-frontend \
  --query Policy --output text | jq .
```

2. **CloudFront OAI/OAC確認**:
```bash
aws cloudfront get-distribution-config --id EZEKNOK0BOTVA \
  --query 'DistributionConfig.Origins.Items[0].S3OriginConfig' \
  --output json
```

3. **Pulumiスタック再デプロイ** (推奨):
```bash
cd infrastructure/pulumi/aws
pulumi stack select staging
pulumi up --yes
```

4. **手動修正**（緊急時のみ）:
- S3バケットポリシーでCloudFront OAIにGetObject権限を付与
- または、OACを使用する場合、適切なバケットポリシーを設定

**優先度**: 🔴 HIGH
**影響範囲**: AWSステージング環境のフロントエンド全体（ランディングページ + SNS app）
**回避策**: 直接S3バケットURLまたはAPI経由でアクセス可能（バックエンドは正常）

---

## テスト環境情報

### ツールバージョン
- curl: 8.5.0
- bash: 5.2.15
- AWS CLI: 2.x
- OS: Ubuntu 24.04.3 LTS (Dev Container)

### 実行環境
- Dev Container
- Network: devcontainer default
- DNS: System resolver

---

## 次のステップ

1. **即時対応**:
   - [ ] AWSステージングCloudFront OAI/OAC設定修正
   - [ ] ドキュメント内の古いCloudFront URLを更新

2. **中期対応**:
   - [ ] インフラ構成のDrift検出自動化
   - [ ] CloudFrontドメイン名の環境変数化（ハードコード削減）
   - [ ] CI/CDパイプラインにエンドポイント疎通テストを追加

3. **長期対応**:
   - [ ] Pulumi outputsからテストスクリプトへのエンドポイント自動注入
   - [ ] CloudFront分散設定の統一（staging/production間の差異解消）

---

## 参考資料

- [AI_AGENT_13_TESTING_JA.md](AI_AGENT_13_TESTING_JA.md) - テストスクリプト全体像
- [AI_AGENT_07_RUNBOOKS_JA.md](AI_AGENT_07_RUNBOOKS_JA.md) - CloudFront手動デプロイ手順
- [AI_AGENT_06_STATUS_JA.md](AI_AGENT_06_STATUS_JA.md) - 環境ステータス

---

## 結論

**本番環境**: ✅ **完全動作** - 全3クラウドでランディングページ+SNS統合テストが100%成功
**ステージング環境**: ⚠️ **AWS CloudFrontの403エラーを除き動作** - Azure/GCP正常、AWS APIも正常

**総合評価**: 🟢 **本番環境は本番準備完了**、🟡 **ステージング環境は部分的改善必要**
