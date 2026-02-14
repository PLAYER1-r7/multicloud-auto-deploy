# Azure クォータ申請ガイド

## 📋 申請情報

### サブスクリプション情報
- **Subscription Name**: sat0sh1kawada
- **Subscription ID**: `29031d24-d41a-4f97-8362-46b40129a7e8`
- **Plan Type**: Pay-As-You-Go (従量課金制)
- **Spending Limit**: Off

### 現在のクォータ状況
- **Location**: Japan East / East US
- **Resource**: App Service Plan
- **Current Limit (Basic VMs)**: 0
- **Current Limit (Dynamic VMs)**: 0

---

## 🚀 クォータ申請手順（Azure Portal）

### Step 1: Azure Portal にログイン
1. ブラウザで開く: https://portal.azure.com
2. アカウント: `sat0sh1kawada@outlook.com` でログイン

### Step 2: クォータ管理画面へ移動

**方法A: 検索バーから**
1. ポータル上部の **検索バー** をクリック
2. 「**quotas**」または「**クォータ**」と入力
3. 「**Quotas**」サービスを選択

**方法B: メニューから**
1. 左メニューの **すべてのサービス** をクリック
2. **管理とガバナンス** → **Quotas** を選択

### Step 3: App Service クォータを検索

1. **「My quotas」** タブを選択
2. フィルター設定:
   - **Provider**: `Compute` または `Microsoft.Web` を選択
   - **Region**: `Japan East` を選択（または `East US`）
3. 検索ボックスに以下のいずれかを入力:
   - `App Service`
   - `Basic VMs`
   - `Web Plan`

### Step 4: クォータ項目を選択

表示された項目から以下を探す:
- ✅ **Total Regional vCPUs** (推奨)
- ✅ **Basic App Service Plan vCPUs**
- ✅ **Standard App Service Plan vCPUs**

項目をクリックして選択

### Step 5: 増加リクエストを作成

1. 「**Request quota increase**」または「**新しいクォータのリクエスト**」ボタンをクリック
2. 以下のフォームに入力:

```
■ Subscription: sat0sh1kawada
■ Resource type: App Service Plan
■ Region: Japan East
■ Current limit: 0
■ New limit: 10 (推奨値: 5〜10)
■ Reason/Justification:
   "Function App deployment for CI/CD pipeline using Pulumi.
    Required for automated multi-cloud deployment project."
   
   または日本語:
   "Pulumi を使用した CI/CD パイプライン用の Function App デプロイに必要。
    マルチクラウド自動デプロイプロジェクトで使用します。"
```

### Step 6: サポートリクエスト詳細

次の画面で追加情報を入力:

```
■ Issue type: Service and subscription limits (quotas)
■ Subscription: sat0sh1kawada
■ Problem type: App Service
■ Problem subtype: App Service Plan
■ Severity: C - Minimal impact (開発環境の場合)
          B - Moderate impact (本番環境の場合)
■ Preferred contact method: Email
■ Email: sat0sh1kawada@outlook.com
```

### Step 7: 確認と送信

1. 入力内容を確認
2. 「**Create**」または「**作成**」ボタンをクリック
3. サポートリクエスト番号をメモ

---

## ⏱️ 承認までの時間

| アカウント種別 | 標準的な承認時間 | 最大時間 |
|--------------|----------------|---------|
| Pay-As-You-Go | 2〜8時間 | 24時間 |
| Enterprise | 1〜4時間 | 12時間 |
| Free Trial | 承認されない可能性 | - |

**あなたのケース**: Pay-As-You-Go → **2〜8時間** で承認される見込み

---

## 📧 承認確認方法

### メール通知
- 件名: "Your Azure support request has been updated"
- 内容: クォータ増加が承認されたことを確認

### Portal で確認
1. Azure Portal → **Quotas**
2. 同じリソース（App Service Plan）を検索
3. **Current limit** が 0 → 10 に変更されていることを確認

---

## 🔄 承認後の対応（自動デプロイ）

### クォータが承認されたら

現在のコードは既に正しい設定になっているため、**何も変更せずに再デプロイできます**：

```bash
# GitHub Actions で自動実行（推奨）
# mainブランチへのpushで自動的にデプロイされます

# または手動で実行:
gh workflow run deploy-azure.yml
```

### 期待される結果

クォータ承認後のデプロイは以下のリソースを作成します:

✅ Resource Group: `multicloud-auto-deploy-staging-rg`
✅ Storage Account (Functions): `mcadfuncXXXXXX`
✅ Storage Account (Frontend): `mcadfeXXXXXX`
✅ Application Insights: `multicloud-auto-deploy-staging-ai`
✅ App Service Plan: `multicloud-auto-deploy-staging-asp` (B1 tier)
✅ Function App: `multicloud-auto-deploy-staging-func`

**デプロイ時間**: 約3〜5分

---

## 🆘 申請が承認されない場合

### トラブルシューティング

1. **支払い方法を確認**:
   - Azure Portal → Cost Management → Payment methods
   - クレジットカードが有効か確認

2. **別のリージョンを試す**:
   - East US
   - West US 2
   - West Europe

3. **サポートに問い合わせ**:
   - Azure Portal → Help + support → New support request
   - クォータが0の理由を確認

4. **代替案: Container Apps**:
   - App Service Plan不要のアーキテクチャに変更
   - 実装時間: 1〜2時間

---

## 📝 申請状況の追跡

### サポートチケット確認
1. Azure Portal → **Help + support**
2. 「**All support requests**」タブ
3. あなたのリクエストのステータスを確認:
   - ⏳ **Open**: 処理中
   - ✅ **Resolved**: 承認完了
   - ❌ **Closed**: 却下された（再申請が必要）

---

## 📞 問い合わせ先

### Azure サポート
- **Portal**: https://portal.azure.com → Help + support
- **ドキュメント**: https://learn.microsoft.com/azure/quotas/

### このプロジェクトについて
- **リポジトリ**: https://github.com/PLAYER1-r7/multicloud-auto-deploy
- **設定ファイル**: `infrastructure/pulumi/azure/__main__.py`
- **ワークフロー**: `.github/workflows/deploy-azure.yml`

---

## ✅ チェックリスト

申請前に確認:
- [ ] Azure Portal にログインできる
- [ ] サブスクリプション `sat0sh1kawada` が表示される
- [ ] 支払い方法が登録されている
- [ ] クォータ管理画面にアクセスできる

申請後に確認:
- [ ] サポートリクエスト番号を受領
- [ ] メール通知を受信
- [ ] クォータが 0 → 10 に変更されたことを確認
- [ ] GitHub Actions で Azure デプロイを実行

---

**この手順に従ってクォータ申請を実施してください。承認されたら教えてください！**
