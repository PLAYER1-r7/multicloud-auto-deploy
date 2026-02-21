# セキュリティ強化まとめ

このドキュメントは、3つのクラウドプロバイダーに追加したセキュリティ対策をまとめています。

## 🔒 AWS セキュリティ対策

### S3バケット

- ✅ **サーバー側暗号化（SSE-S3）**: AES256暗号化を有効化
- ✅ **バージョニング**: オブジェクトの履歴管理と誤削除防止
- ✅ **アクセスログ**: 別バケットにS3アクセスログを記録
- ✅ **パブリックアクセスブロック**: CloudFront経由のみアクセス可能

### CloudFront

- ✅ **セキュリティヘッダー**: Response Headers Policyで以下を設定
  - `Strict-Transport-Security`: HSTS有効化（1年間）
  - `X-Content-Type-Options`: MIMEスニッフィング防止
  - `X-Frame-Options`: クリックジャッキング防止（DENY）
  - `X-XSS-Protection`: XSS保護
  - `Content-Security-Policy`: CSP設定
  - `Referrer-Policy`: リファラー制御
- ✅ **アクセスログ**: CloudFrontアクセスログをS3に記録
- ✅ **HTTPS強制**: HTTPからHTTPSへ自動リダイレクト

### コスト

- ログバケット用のストレージ費用（小額）

## 🔒 Azure セキュリティ対策

### Storage Account

- ✅ **TLS 1.2最小バージョン**: 古いTLSプロトコルを無効化
- ✅ **HTTPS強制**: HTTPトラフィックを拒否
- ✅ **Blob バージョニング**: オブジェクトの履歴管理
- ✅ **削除保持ポリシー**:
  - Blob: 7日間の削除保持
  - コンテナ: 7日間の削除保持
- ✅ **デフォルト暗号化**: Azure Storage Service Encryption（AES256）

### Front Door

- ✅ **WAF（Web Application Firewall）**:
  - Microsoft Default Rule Set 2.1
  - Bot Manager Rule Set 1.0
  - カスタムレート制限（100リクエスト/分/IP）
- ✅ **HTTPS強制**: HTTP to HTTPSリダイレクト
- ✅ **セキュリティポリシー**: エンドポイント全体に適用

### コスト

- WAF料金（Front Door Standardに含まれる基本機能）
- ルール実行による追加課金の可能性

## 🔒 GCP セキュリティ対策

### Cloud Storage

- ✅ **バージョニング**: オブジェクトの履歴管理
- ✅ **ライフサイクル管理**: 古いバージョンを自動削除（3世代保持）
- ✅ **アクセスログ**: 別バケットにログを記録
- ✅ **ログ自動削除**: ログは30日後に自動削除
- ✅ **デフォルト暗号化**: Google管理の暗号化キー

### Cloud Armor（WAF）

- ✅ **レート制限**: 100リクエスト/分/IPでスロットリング
- ✅ **SQLインジェクション対策**: プリセットルールで検出・ブロック
- ✅ **XSS対策**: クロスサイトスクリプティング攻撃を検出・ブロック
- ✅ **エッジセキュリティポリシー**: バックエンドバケットに適用

### Load Balancer & CDN

- ✅ **Cloud CDN**: キャッシュによる負荷軽減
- ✅ **HTTPS対応**: カスタムドメイン時にマネージド証明書

### コスト

- Cloud Armorポリシー: 月額固定費用
- ルール評価による従量課金
- ログバケット用のストレージ費用

## 📊 セキュリティ機能比較

| 機能                 | AWS       | Azure        | GCP           |
| -------------------- | --------- | ------------ | ------------- |
| データ暗号化         | ✅ SSE-S3 | ✅ Azure SSE | ✅ Google管理 |
| バージョニング       | ✅        | ✅           | ✅            |
| アクセスログ         | ✅        | ❌\*         | ✅            |
| WAF                  | ❌\*\*    | ✅           | ✅            |
| レート制限           | ❌\*\*    | ✅           | ✅            |
| セキュリティヘッダー | ✅        | ❌\*\*\*     | ❌\*\*\*      |
| SQLi/XSS対策         | ❌\*\*    | ✅           | ✅            |
| HTTPS強制            | ✅        | ✅           | ✅            |
| 削除保持             | ❌        | ✅           | ❌            |

\*Azure診断ログは別途設定可能
**AWS WAFは別途追加可能（追加コスト）\***Front Door/Cloud CDNのレスポンスヘッダーカスタマイズで対応可能

## 🚨 セキュリティベストプラクティス

### 共通推奨事項

1. **定期的なログレビュー**: アクセスログを定期的に確認
2. **モニタリング設定**: 異常なトラフィックを検知
3. **最小権限の原則**: 必要最小限の権限のみ付与
4. **定期的なセキュリティ監査**: 設定の見直し

### 本番環境での追加推奨事項

#### AWS

- AWS WAFの追加（DDoS対策、レート制限）
- AWS Shield Standardの有効化（無料）
- CloudWatch Alarmsでモニタリング
- S3バケットのMFA Delete有効化

#### Azure

- Azure DDoS Protection Standardの検討
- Azure Monitorでアラート設定
- Private Endpointの使用（高セキュリティ環境）

#### GCP

- VPCファイアウォールルールの追加
- Cloud Monitoringでアラート設定
- Identity-Aware Proxy（IAP）の検討

## 📝 適用方法

各クラウドのディレクトリで以下を実行：

```bash
cd <aws|azure|gcp>/terraform
tofu plan
tofu apply
```

## ⚠️ 注意事項

- **コスト影響**: WAF、ログストレージで追加コストが発生します
- **ログ容量**: トラフィックに応じてログバケットのサイズが増加します
- **レート制限**: 正当なユーザーが制限に引っかからないよう調整が必要です
- **削除保護**: バージョニング有効化により、削除時に追加手順が必要になる場合があります

## 🔧 カスタマイズ

### レート制限の調整

各クラウドの設定ファイルでレート制限値を変更できます：

- **Azure**: `rate_limit_threshold = 100` (main.tf)
- **GCP**: `count = 100, interval_sec = 60` (main.tf)

### ログ保持期間

- **Azure**: `days = 7` (Blob削除保持)
- **GCP**: `age = 30` (ログバケットライフサイクル)

### CSPポリシー（AWS）

`content_security_policy`を要件に応じて調整してください。
