# 監視・アラート設定ガイド

Multi-Cloud Auto Deployの監視・アラート設定を行います。

## 概要

3つのクラウドすべてに統一された監視・アラート機能を実装：

- **AWS**: CloudWatch Alarms + SNS
- **Azure**: Azure Monitor Alerts + Action Groups  
- **GCP**: Cloud Monitoring Alert Policies + Notification Channels

## 監視対象

### AWS
- **Lambda関数**
  - エラーレート (> 10 errors/5分)
  - スロットル
  - 実行時間 (> 30秒)
- **API Gateway**
  - 5xxエラーレート (> 10/5分)
  - 4xxエラーレート (> 50/5分)
  - レイテンシ (> 5秒)
- **CloudFront**
  - 5xxエラーレート (> 5%)
- **コスト異常検出** (本番環境のみ)

### Azure
- **Function App**
  - HTTP 5xxエラー (> 10/5分)
  - レスポンスタイム (> 5秒)
  - メモリ使用量 (> 90%)
- **Cosmos DB**
  - スロットルリクエスト (429エラー)
  - レイテンシ (> 1秒)
- **Front Door**
  - エラー率 (> 5%)

### GCP
- **Cloud Functions**
  - エラーレート (> 10%)
  - 実行時間 (> 10秒)
  - メモリ使用量 (> 90%)
- **Firestore**
  - ドキュメント読み込み (> 10000/分)
- **コスト予算アラート** (本番環境のみ)
  - 50%, 80%, 100%の予算消費時に通知

## セットアップ手順

### 1. メール通知アドレスの設定

各クラウドのPulumiスタックにアラート通知先メールアドレスを設定します。

#### AWS (Staging)
```bash
cd infrastructure/pulumi/aws
pulumi config set alarmEmail your-email@example.com --stack staging
```

#### AWS (Production)
```bash
pulumi config set alarmEmail your-email@example.com --stack production
```

#### Azure (Staging)
```bash
cd ../azure
pulumi config set alarmEmail your-email@example.com --stack staging
```

#### Azure (Production)
```bash
pulumi config set alarmEmail your-email@example.com --stack production
```

#### GCP (Staging)
```bash
cd ../gcp
pulumi config set alarmEmail your-email@example.com --stack staging
```

#### GCP (Production)
```bash
pulumi config set alarmEmail your-email@example.com --stack production
# 月次コスト予算も設定 (デフォルト: $50)
pulumi config set monthlyBudgetUsd 100 --stack production
```

### 2. 監視設定のデプロイ

各クラウドで`pulumi up`を実行して監視設定をデプロイします。

#### AWS
```bash
cd infrastructure/pulumi/aws
pulumi up --stack staging  # Stagingデプロイ
pulumi up --stack production  # Productionデプロイ
```

**確認項目**:
- SNSトピック作成
- CloudWatch Alarms作成 (Lambda x3, API Gateway x3, CloudFront x1)
- メールサブスクリプション確認リンクが届く

**重要**: AWSからのメール確認リンクをクリックして、SNSサブスクリプションを有効化してください。

#### Azure
```bash
cd ../azure
pulumi up --stack staging
pulumi up --stack production
```

**確認項目**:
- Action Group作成
- Azure Monitor Alerts作成 (Function App x3, Cosmos DB x2, Front Door x1)

#### GCP
```bash
cd ../gcp
pulumi up --stack staging
pulumi up --stack production
```

**確認項目**:
- Notification Channel作成
- Alert Policies作成 (Cloud Functions x3, Firestore x1)
- Billing Budget作成 (本番環境のみ)

### 3. アラート動作確認

#### テスト方法

**AWS Lambda エラー**:
```bash
# Lambda関数を直接実行してエラーを発生させる
aws lambda invoke \
  --function-name multicloud-auto-deploy-staging-api \
  --payload '{"error": true}' \
  /dev/null
```

**API Gateway エラー**:
```bash
# 存在しないエンドポイントに複数回リクエスト
for i in {1..20}; do
  curl https://your-api-endpoint.execute-api.us-east-1.amazonaws.com/invalid
done
```

**GCP Cloud Functions エラー**:
```bash
# 関数にエラーを発生させるペイロードを送信
gcloud functions call multicloud-auto-deploy-staging-api \
  --data '{"error": true}'
```

#### 確認内容
1. アラートが発火するまで約5分待つ
2. 設定したメールアドレスに通知が届くことを確認
3. クラウドコンソールでアラート状態を確認:
   - AWS: CloudWatch → Alarms
   - Azure: Monitor → Alerts
   - GCP: Monitoring → Alerting

## 監視ダッシュボード

### AWS CloudWatch
https://console.aws.amazon.com/cloudwatch/

- **Alarms**: すべてのアラームの状態を確認
- **Metrics**: Lambda, API Gateway, CloudFrontのメトリクスをグラフ表示
- **Cost Anomaly Detection**: 異常なコスト増加を検出

### Azure Portal
https://portal.azure.com/#blade/Microsoft_Azure_Monitoring/AzureMonitoringBrowseBlade/alerts

- **Alerts**: すべてのアラートの状態を確認
- **Metrics**: Function App, Cosmos DB, Front Doorのメトリクスをグラフ表示
- **Application Insights**: 詳細なアプリケーショントレース

### GCP Cloud Console
https://console.cloud.google.com/monitoring

- **Alerting**: すべてのアラートポリシーの状態を確認
- **Metrics Explorer**: Cloud Functions, Firestoreのメトリクスをグラフ表示
- **Billing**: 予算とコストの推移を確認

## アラート通知の種類

### 即座に対応が必要 (Critical)
- Lambda/Function エラーレート高騰
- API Gateway 5xx エラー多発
- CloudFront/Front Door 5xx エラー
- データベーススロットル (Cosmos DB 429エラー)

### 監視が必要 (Warning)
- Lambda/Function 実行時間遅延
- API Gateway 4xx エラー増加
- メモリ使用量高騰
- コスト予算超過

### 情報提供 (Info)
- コスト予算50%到達
- 日次/週次レポート

## トラブルシューティング

### アラートメールが届かない

**AWS**:
- SNSサブスクリプションを確認してメール確認リンクをクリックしたか確認
- `pulumi stack output monitoring_sns_topic_arn`でSNSトピックが作成されているか確認

**Azure**:
- Action Groupのメールアドレスが正しいか確認
- スパムフォルダを確認

**GCP**:
- Notification Channelが正しく作成されているか確認
- `pulumi stack output monitoring_notification_channel_id`で確認

### アラートが発火しない

1. **メトリクスデータの確認**:
   - 各クラウドのコンソールでメトリクスが正しく収集されているか確認
   - Lambda/Functionが実際に実行されているか確認

2. **閾値の調整**:
   - `monitoring.py`の閾値を調整して再デプロイ
   - テスト環境では閾値を低く設定することも検討

3. **評価期間の確認**:
   - デフォルトは5分間なので、すぐにはアラートが発火しない
   - テスト時は評価期間を短く設定することも可能

### アラート通知が多すぎる

1. **閾値の調整**:
   ```python
   # monitoring.pyの閾値を上げる
   threshold_value=20,  # 10 → 20に変更
   ```

2. **評価期間の延長**:
   ```python
   # 5分 → 10分に変更
   duration="600s",
   ```

3. **通知頻度の制限**:
   - AWS: Alarm Actions の設定で通知間隔を調整
   - Azure: Action Groupの設定で通知頻度を制限
   - GCP: Alert Policyの設定で通知間隔を調整

## コスト

監視機能自体のコスト概算:

### AWS
- **CloudWatch Alarms**: $0.10/アラーム/月 × 8アラーム = $0.80
- **SNS**: 1,000通知まで無料、以降$0.50/1,000通知
- **Cost Anomaly Detection**: 無料
- **月次コスト**: 約$1-2

### Azure
- **Azure Monitor Alerts**: 最初の10アラートルール無料、以降$0.10/ルール/月
- **Action Group**: 1,000通知まで無料
- **月次コスト**: 約$0-1 (10ルール以内なら無料)

### GCP
- **Cloud Monitoring Alert Policies**: 最初の100ポリシー無料、以降$0.18/ポリシー/月
- **Notification Channels**: 無料
- **月次コスト**: 約$0 (100ポリシー以内なら無料)

**合計**: 約$1-3/月 (3クラウド合計)

## 次のステップ

1. ✅ 監視・アラート設定 (本ドキュメント)
2. ⏳ カスタムドメイン設定
3. ⏳ 秘密値の検証と更新
4. ⏳ セキュリティ強化 (Rate Limiting, IP制限など)
5. ⏳ いいね機能の実装

監視設定が完了したら、次は**カスタムドメイン設定**に進んでください。
