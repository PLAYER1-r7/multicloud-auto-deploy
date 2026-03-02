# テスト戦略と運用ダイアグラム

> 包括的なテスト戦略、QA フロー、本番運用手順を可視化したダイアグラム集

---

## 1. テストピラミッド（Test Pyramid）

単体テストから E2E テストまでの層構造と実行頻度。

```mermaid
graph TB
    subgraph "E2E テスト（遅い・貴重）"
        E2E["🌐 エンドツーエンド<br/>Staging 環境<br/>本物の 3 クラウド<br/>実 DB、実ネットワーク<br/>実行: デプロイ前<br/>約 30 分"]
    end

    subgraph "統合テスト（中速・重要）"
        INT1["🔗 API 統合テスト<br/>ローカル docker-compose<br/>Mock + 実 Python コード<br/>実行: 毎プッシュ<br/>約 2-3 分"]
        INT2["🔗 マイクロサービス<br/>統合テスト<br/>複数サービス連携仕様<br/>実行: CI/CD<br/>約 5 分"]
    end

    subgraph "単体テスト（速い・多数）"
        UNIT1["⚡ pytest コア機能<br/>テスト<br/>AWS/Azure/GCP<br/>バックエンド各1,000+ テスト<br/>実行: 毎プッシュ<br/>約 10 秒"]
        UNIT2["⚡ JavaScript<br/>フレームワークテスト<br/>React コンポーネント<br/>実行: 毎プッシュ<br/>約 5 秒"]
    end

    UNIT1 --> INT1
    UNIT2 --> INT1
    INT1 --> INT2
    INT2 --> E2E
```

---

## 2. テスト実行マトリックス（Test Matrix）

各クラウド・環境における テスト実行パターン。

```mermaid
graph LR
    subgraph "ローカル開発"
        LOCAL["💻 ローカル環境<br/>docker-compose<br/>速い（<1 分）<br/>リグレッション防止"]
    end

    subgraph "Staging 3 クラウド"
        STAGE_AWS["🟠 AWS Staging<br/>Lambda, API Gateway<br/>5-10 分"]
        STAGE_AZURE["🔵 Azure Staging<br/>Function App, AFD<br/>5-10 分"]
        STAGE_GCP["🟡 GCP Staging<br/>Cloud Run, CDN<br/>5-10 分"]
    end

    subgraph "Production 3 クラウド"
        PROD_AWS["🟠 AWS Production<br/>⚠️ スモークテストのみ<br/>3-5 分"]
        PROD_AZURE["🔵 Azure Production<br/>⚠️ スモークテストのみ<br/>3-5 分"]
        PROD_GCP["🟡 GCP Production<br/>⚠️ スモークテストのみ<br/>3-5 分"]
    end

    LOCAL -->|毎プッシュ| STAGE_AWS
    LOCAL -->|毎プッシュ| STAGE_AZURE
    LOCAL -->|毎プッシュ| STAGE_GCP

    STAGE_AWS -->|デプロイ前| PROD_AWS
    STAGE_AZURE -->|デプロイ前| PROD_AZURE
    STAGE_GCP -->|デプロイ前| PROD_GCP
```

---

## 3. テストメンテナンスカレンダー

定期的なテスト実行・更新スケジュール。

```mermaid
graph TB
    subgraph "日次"
        DAILY["🔄 毎日 0:00 UTC<br/>- Staging 全 E2E テスト（3 環境）<br/>- ストレステスト（100 コンカレント）<br/>- セキュリティスキャン"]
    end

    subgraph "週次"
        WEEKLY["🔂 毎週月曜 0:00 UTC<br/>- 本番スモークテスト全実行<br/>- Cross-cloud フェイルオーバーテスト<br/>- データ整合性チェック"]
    end

    subgraph "月次"
        MONTHLY["🔁 毎月 1 日 0:00 UTC<br/>- 災害復旧（DR）テスト<br/>- バックアップ復元テスト<br/>- セキュリティペネトレーション（外部）<br/>- パフォーマンスベンチマーク"]
    end

    subgraph "不定期"
        ONCALL["📋 本番インシデント時<br/>- root cause 分析テスト<br/>- 再発防止テスト追加<br/>- Runbook 検証"]
    end

    DAILY --> WEEKLY
    WEEKLY --> MONTHLY
    MONTHLY --> ONCALL
```

---

## 4. 本番運用フロー（Operations Workflow）

アラートから対応完了までのプロセス。

```mermaid
graph TD
    subgraph "検出"
        ALERT["🚨 アラート発生<br/>(CloudWatch/Monitor/Logs)"]
        SLACK["💬 Slack 通知<br/>on-call エンジニアに通知"]
    end

    subgraph "初期対応（15 分以内）"
        PAGE["📞 エスカレーション"]
        DIAG["🔍 初期診断<br/>- ログ確認<br/>- メトリクス確認<br/>- 影響範囲把握"]
        IMPACT["📊 影響評価<br/>- SEV レベル判定<br/>- ユーザー数評価<br/>- 復旧時間推定"]
    end

    subgraph "対応判断（30 分以内）"
        DECIDE{対応方法<br/>判定}
        HOTFIX["🔧 ホットフィックス<br/>即時デプロイ"]
        ROLLBACK["⏮️ ロールバック<br/>前バージョンに戻す"]
        WORKAROUND["🛠️ ワークアラウンド<br/>一時的な対処"]
    end

    subgraph "実行（即時）"
        EXEC["⏳ 対応実行<br/>- コード修正・デプロイ<br/>- または<br/>- テラフォーム適用"]
        MONITOR["👁️ リアルタイム監視<br/>- CloudWatch ダッシュボード<br/>- ユーザー報告"]
    end

    subgraph "検証（対応後 10 分）"
        VERIFY["✅ 復旧確認<br/>- メトリクス正常化<br/>- テスト実行<br/>- ユーザー報告停止"]
    end

    subgraph "事後処理（24 時間以内）"
        DOC["📋 ドキュメント作成<br/>- Timeline<br/>- Root Cause Analysis<br/>- 再発防止策"]
        UPDATE["🔄 運用手順更新<br/>- Runbook 更新<br/>- チェックリスト追加<br/>- アラート閾値調整"]
        RETRO["🎯 チームレビュー<br/>- ポストモーテム会議<br/>- 学習共有<br/>- 改善タスク化"]
    end

    ALERT --> SLACK
    SLACK --> PAGE
    PAGE --> DIAG
    DIAG --> IMPACT
    IMPACT --> DECIDE

    DECIDE -->|軽微| HOTFIX
    DECIDE -->|重大| ROLLBACK
    DECIDE -->|一時| WORKAROUND

    HOTFIX --> EXEC
    ROLLBACK --> EXEC
    WORKAROUND --> EXEC

    EXEC --> MONITOR
    MONITOR --> VERIFY

    VERIFY --> DOC
    DOC --> UPDATE
    UPDATE --> RETRO
```

---

## 5. デプロイメント承認フロー

変更管理と承認プロセス。

```mermaid
graph LR
    DEV["👨‍💻 開発者<br/>Feature 作成"]

    PR["📝 Pull Request<br/>Create"]

    subgraph "レビュー段階"
        REVIEW["👀 コードレビュー<br/>- セキュリティチェック<br/>- パフォーマンス確認<br/>- テストカバレッジ確認"]
        APPROVE["✅ レビュー承認<br/>2 人以上の approve"]
    end

    subgraph "自動テスト"
        AUTO_TEST["🤖 自動テスト実行<br/>- Unit tests<br/>- Integration tests<br/>- E2E tests (Staging)"]
        TEST_PASS["✅ すべてのテスト<br/>成功"]
    end

    subgraph "本番デプロイ決定"
        DECIDE_DEPLOY{本番デプロイ<br/>対象？}
        STAGING["📦 Staging のみ<br/>デプロイ完了"]
        PROD_REVIEW["🔐 本番デプロイ<br/>承認リクエスト<br/>- Lead Engineer 承認<br/>- Ops Manager 確認<br/>- 変更ウィンドウ確認"]
    end

    subgraph "本番デプロイ実行"
        BLUE_GREEN["🟦 Blue-Green<br/>デプロイ<br/>- 新環境構築<br/>- トラフィック段階移行<br/>- ロールバック準備"]
        SMOKE_TEST["🔥 スモークテスト<br/>本番環境"]
        COMPLETE["✅ デプロイ完了<br/>旧環境削除"]
    end

    DEV --> PR
    PR --> REVIEW
    REVIEW --> APPROVE
    APPROVE --> AUTO_TEST
    AUTO_TEST --> TEST_PASS

    TEST_PASS --> DECIDE_DEPLOY
    DECIDE_DEPLOY -->|feature branch| STAGING
    DECIDE_DEPLOY -->|main branch| PROD_REVIEW

    PROD_REVIEW --> BLUE_GREEN
    BLUE_GREEN --> SMOKE_TEST
    SMOKE_TEST --> COMPLETE
```

---

## 6. ロールバック決定ツリー

本番インシデント時のロールバック判定フロー。

```mermaid
graph TD
    INCIDENT["🚨 本番インシデント<br/>検出"]

    Q1{ユーザーに<br/>影響あり？}

    Q2{15 分で<br/>根本原因<br/>特定できた？}

    Q3{修正は<br/>テスト済み？}

    Q4{デプロイから<br/>24 時間内？}

    Q5{安全なロール<br/>バック経路<br/>ある？}

    ROLLBACK["⏮️ ロールバック<br/>実行（推奨）"]
    HOTFIX["🔧 ホットフィックス<br/>デプロイ"]
    WORKAROUND["🛠️ ワークアラウンド<br/>実装<br/>並行で修正開発"]
    CONTINUE["⏸️ 監視継続<br/>修正方針検討"]

    INCIDENT → Q1

    Q1 -->|NO| CONTINUE
    Q1 -->|YES| Q2

    Q2 -->|NO| ROLLBACK
    Q2 -->|YES| Q3

    Q3 -->|NO| HOTFIX
    Q3 -->|YES| Q4

    Q4 -->|NO| HOTFIX
    Q4 -->|YES| Q5

    Q5 -->|NO| HOTFIX
    Q5 -->|YES| ROLLBACK
```

---

## 7. 本番運用カレンダー

定期保守ウィンドウと緊急対応タイムゾーン。

```mermaid
graph TB
    subgraph "定期保守（計画済み）"
        WINDOW["🔧 変更ウィンドウ<br/>毎週金曜 22:00 UTC<br/>（土曜 7:00 JST）<br/>最大 4 時間<br/>本番デプロイ・インフラ変更"]
    end

    subgraph "緊急枠"
        EMERGENCY["🚨 緊急対応<br/>24/7 on-call<br/>SEV1・SEV2：即座対応<br/>SEV3：次のウィンドウで対応"]
    end

    subgraph "監視・アラート"
        WATCH["👁️ 常時監視<br/>- CloudWatch（AWS）<br/>- Azure Monitor<br/>- Cloud Logging（GCP）<br/>- 異常検知<br/>- Slack bot"]
    end

    subgraph "オンコール体制"
        ONCALL["📞 on-call ローテーション<br/>- 日本側担当者：9:00-18:00 JST<br/>- エスカレーション：Lead Engineer<br/>- バックアップ：Manager"]
    end

    WINDOW --> WATCH
    EMERGENCY --> WATCH
    WATCH --> ONCALL
```

---

## 8. 監視・アラート設定マトリックス

重要なメトリクスと通知ルール。

```mermaid
graph TB
    subgraph "API パフォーマンス"
        API["📊 レスポンスタイム<br/>- P95 < 500ms → SEV3<br/>- P95 > 1s → SEV2<br/>- 5xx エラー > 1% → SEV1"]
    end

    subgraph "インフラ"
        INFRA["🔧 リソース使用率<br/>- CPU > 80% → Warning<br/>- Memory > 90% → SEV2<br/>- Disk > 95% → SEV1"]
    end

    subgraph "ユーザー体験"
        UX["👥 ユーザー影響<br/>- ログイン失敗率 > 5% → SEV1<br/>- 投稿失敗 > 2% → SEV2<br/>- 遅延 > 2s → SEV3"]
    end

    subgraph "セキュリティ"
        SEC["🔒 セキュリティ指標<br/>- 不正ログイン試行 > 100/min → Immediate<br/>- WAF ブロック > 1000/h → Alert<br/>- SQL インジェクション検知 → Block + Alert"]
    end

    subgraph "通知ルーティング"
        NOTIFY["📣 通知先別<br/>- SEV1 → Slack + SMS + Phone<br/>- SEV2 → Slack + Phone<br/>- SEV3 → Slack<br/>- Warning → Logs 記録"]
    end

    API --> NOTIFY
    INFRA --> NOTIFY
    UX --> NOTIFY
    SEC --> NOTIFY
```

---

## 参照

- [AI_AGENT_05_CICD.md](AI_AGENT_05_CICD.md) — CI/CD パイプラインの詳細
- [AI_AGENT_07_RUNBOOKS.md](AI_AGENT_07_RUNBOOKS.md) — 手順書と自動化スクリプト
- [AI_AGENT_13_TESTING.md](AI_AGENT_13_TESTING.md) — テストガイド
- [AI_AGENT_06_STATUS.md](AI_AGENT_06_STATUS.md) — 環境ステータス
