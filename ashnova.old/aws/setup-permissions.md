# AWS IAM権限設定手順

satoshiユーザーに静的ウェブサイトデプロイに必要な権限を付与します。

## 必要な権限

- **S3**: バケット作成、設定、オブジェクトアップロード
- **CloudFront**: ディストリビューション作成、OAC作成、キャッシュ無効化
- **IAM**: ポリシードキュメント読み取り（OpenTofuのdata source用）

## 方法1: カスタムポリシーを作成してアタッチ（推奨）

### 1. IAMポリシーを作成

```bash
# ポリシーを作成
aws iam create-policy \
  --policy-name AshnovaStaticWebsitePolicy \
  --policy-document file://iam-policy.json \
  --description "Policy for deploying static websites with S3 and CloudFront"

# ポリシーのARNを記録（出力に表示されます）
# 例: arn:aws:iam::278280499340:policy/AshnovaStaticWebsitePolicy
```

### 2. satoshiユーザーにポリシーをアタッチ

```bash
aws iam attach-user-policy \
  --user-name satoshi \
  --policy-arn arn:aws:iam::278280499340:policy/AshnovaStaticWebsitePolicy
```

### 3. 権限の確認

```bash
aws iam list-attached-user-policies --user-name satoshi
```

## 方法2: インラインポリシーとして追加

```bash
aws iam put-user-policy \
  --user-name satoshi \
  --policy-name AshnovaStaticWebsite \
  --policy-document file://iam-policy.json
```

## 方法3: AWSマネジメントコンソールで設定

1. [IAMコンソール](https://console.aws.amazon.com/iam/)を開く
2. 左メニューから「ポリシー」→「ポリシーを作成」
3. 「JSON」タブを選択
4. `iam-policy.json`の内容を貼り付け
5. ポリシー名を入力（例: `AshnovaStaticWebsitePolicy`）
6. 「ポリシーを作成」をクリック
7. 左メニューから「ユーザー」→「satoshi」を選択
8. 「許可を追加」→「ポリシーを直接アタッチ」
9. 作成したポリシーを選択してアタッチ

## より広い権限が必要な場合

開発環境で制限を緩和したい場合は、AWS管理ポリシーを使用できます：

```bash
# S3フルアクセス
aws iam attach-user-policy \
  --user-name satoshi \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

# CloudFrontフルアクセス
aws iam attach-user-policy \
  --user-name satoshi \
  --policy-arn arn:aws:iam::aws:policy/CloudFrontFullAccess
```

⚠️ **注意**: フルアクセスポリシーは広範な権限を持つため、本番環境では推奨されません。

## 権限付与後の確認

```bash
# 再度デプロイを実行
cd /Users/sat0sh1kawada/Workspace/ashnova/aws
./deploy.sh
```

## トラブルシューティング

### 権限が反映されない場合

1. AWS CLIの認証情報をリフレッシュ:

   ```bash
   aws sts get-caller-identity --profile satoshi
   ```

2. 数分待ってから再試行（IAM権限の伝播には時間がかかる場合があります）

### 最小権限の原則

本番環境では、実際に使用するリソースに応じてポリシーを調整してください：

- S3バケット名のプレフィックスを制限
- 特定のCloudFrontディストリビューションのみに権限を付与
- 必要なアクションのみを許可
