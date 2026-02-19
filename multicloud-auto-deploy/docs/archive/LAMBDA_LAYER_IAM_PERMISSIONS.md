# Lambda Layer IAM 権限設定ガイド

> **AIエージェント向けメモ**: Lambda Layer 公開に必要な IAM 権限設定。


## 概要

Lambda Layerへのアクセス（特にクロスアカウントの公開Layer）に必要なIAM権限の設定方法を説明します。

## 必要な権限

### Lambda Layer アクセス権限

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaLayerAccess",
      "Effect": "Allow",
      "Action": [
        "lambda:GetLayerVersion",
        "lambda:GetLayerVersionByArn",
        "lambda:ListLayerVersions",
        "lambda:ListLayers"
      ],
      "Resource": "*"
    },
    {
      "Sid": "LambdaFunctionManagement",
      "Effect": "Allow",
      "Action": [
        "lambda:GetFunction",
        "lambda:GetFunctionConfiguration",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:PublishLayerVersion",
        "lambda:DeleteLayerVersion",
        "lambda:AddPermission",
        "lambda:RemovePermission",
        "lambda:ListFunctions",
        "lambda:CreateFunction",
        "lambda:DeleteFunction",
        "lambda:InvokeFunction"
      ],
      "Resource": "*"
    }
  ]
}
```

## 設定手順

### 1. IAMポリシーの作成

```bash
# ポリシーファイルを作成
cat > /tmp/lambda-layer-access-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "LambdaLayerAccess",
      "Effect": "Allow",
      "Action": [
        "lambda:GetLayerVersion",
        "lambda:GetLayerVersionByArn",
        "lambda:ListLayerVersions",
        "lambda:ListLayers"
      ],
      "Resource": "*"
    },
    {
      "Sid": "LambdaFunctionManagement",
      "Effect": "Allow",
      "Action": [
        "lambda:GetFunction",
        "lambda:GetFunctionConfiguration",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration",
        "lambda:PublishLayerVersion",
        "lambda:DeleteLayerVersion",
        "lambda:AddPermission",
        "lambda:RemovePermission",
        "lambda:ListFunctions",
        "lambda:CreateFunction",
        "lambda:DeleteFunction",
        "lambda:InvokeFunction"
      ],
      "Resource": "*"
    }
  ]
}
EOF

# ポリシーを作成
aws iam create-policy \
  --policy-name LambdaLayerFullAccess \
  --description "Allow access to Lambda Layers including cross-account public layers" \
  --policy-document file:///tmp/lambda-layer-access-policy.json
```

### 2. ポリシーのアタッチ

**IAMユーザーにアタッチ：**

```bash
aws iam attach-user-policy \
  --user-name YOUR_USERNAME \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/LambdaLayerFullAccess
```

**IAMロールにアタッチ：**

```bash
aws iam attach-role-policy \
  --role-name YOUR_ROLE_NAME \
  --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/LambdaLayerFullAccess
```

### 3. 権限の確認

```bash
# ユーザーのポリシー一覧を確認
aws iam list-attached-user-policies --user-name YOUR_USERNAME

# ロールのポリシー一覧を確認
aws iam list-attached-role-policies --role-name YOUR_ROLE_NAME
```

## 実装済み（当プロジェクト）

当プロジェクトの `administrator` ユーザーには、以下のポリシーが設定済みです：

```
✅ LambdaLayerFullAccess (arn:aws:iam::278280499340:policy/LambdaLayerFullAccess)
✅ APIGatewayV2FullAccess (arn:aws:iam::278280499340:policy/APIGatewayV2FullAccess)
```

## トラブルシューティング

### クロスアカウントLayerへのアクセスエラー

```
Error: User is not authorized to perform: lambda:GetLayerVersion 
because no resource-based policy allows the lambda:GetLayerVersion action
```

**原因：**
1. IAM権限が不足している → 上記の手順で権限を追加
2. Layer側のリソースベースポリシーで制限されている → Layer提供者側の設定問題

**解決策：**
- IAM権限を追加（このガイドの手順）
- Layer提供者に問い合わせ
- カスタムLayerを作成（推奨）

### 最小権限の原則

本番環境では、より厳格な権限設定を推奨：

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "lambda:GetLayerVersion",
        "lambda:GetLayerVersionByArn"
      ],
      "Resource": [
        "arn:aws:lambda:ap-northeast-1:YOUR_ACCOUNT_ID:layer:*",
        "arn:aws:lambda:ap-northeast-1:770693421928:layer:Klayers-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:UpdateFunctionConfiguration",
        "lambda:UpdateFunctionCode"
      ],
      "Resource": "arn:aws:lambda:ap-northeast-1:YOUR_ACCOUNT_ID:function:multicloud-auto-deploy-*"
    }
  ]
}
```

## 関連ドキュメント

- [Lambda Layer 最適化ガイド](LAMBDA_LAYER_OPTIMIZATION.md)
- [Lambda Layer 公開リソース活用ガイド](LAMBDA_LAYER_PUBLIC_RESOURCES.md)
- [AWS Lambda - IAM権限](https://docs.aws.amazon.com/lambda/latest/dg/lambda-permissions.html)
- [AWS Lambda Layers](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)

## まとめ

✅ IAM権限を正しく設定することで、Lambda Layerへのアクセスが可能になります  
✅ クロスアカウントLayerの場合、Layer側のリソースベースポリシーも重要  
✅ 問題がある場合は、カスタムLayerの使用が最も確実な解決策です  
