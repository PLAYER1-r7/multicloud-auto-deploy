# カスタムドメイン設定手順（AWS）

## 現在の状況

- 基本的なインフラは構築済み
- CloudFrontは現在デフォルトドメインで動作中
- カスタムドメイン www.aws.ashnova.jp を設定するには証明書が必要

## 設定手順

### ステップ1: DNSレコードの準備

まず、ashnova.jpのDNSゾーンに以下のレコードを追加する準備をします。

**注意**: このレコードは証明書を作成する前に追加するのが理想的です。

### ステップ2: 証明書の作成とDNS検証レコードの追加

1. terraform.tfvarsを編集してカスタムドメインを有効化：

```bash
cd /Users/sat0sh1kawada/Workspace/ashnova/aws/terraform
cat > terraform.tfvars <<EOF
domain_name = "www.aws.ashnova.jp"
EOF
```

2. インフラをデプロイして証明書を作成：

```bash
tofu apply -auto-approve
```

3. DNS検証レコード情報を取得：

```bash
tofu output acm_certificate_validation_records
```

出力例：

```
tomap({
  "www.aws.ashnova.jp" = {
    "name" = "_xxxxx.www.aws.ashnova.jp."
    "type" = "CNAME"
    "value" = "_yyyyy.acm-validations.aws."
  }
})
```

4. **すぐに** ashnova.jpのDNSゾーンに上記のCNAMEレコードを追加：

```
名前: _xxxxx.www.aws.ashnova.jp
タイプ: CNAME
値: _yyyyy.acm-validations.aws.
```

### ステップ3: 証明書の検証完了を待つ

DNSレコード追加後、証明書が自動的に検証されます（通常5〜30分）。

検証状況の確認：

```bash
cd /Users/sat0sh1kawada/Workspace/ashnova/aws/terraform
watch -n 30 'aws acm describe-certificate --certificate-arn $(tofu output -raw acm_certificate_arn) --region us-east-1 --profile satoshi --query "Certificate.Status" --output text'
```

または：

```bash
aws acm describe-certificate \
  --certificate-arn $(tofu output -raw acm_certificate_arn) \
  --region us-east-1 \
  --profile satoshi \
  --query 'Certificate.{Status:Status,DomainValidationOptions:DomainValidationOptions[0].ValidationStatus}' \
  --output json
```

ステータスが `ISSUED` になれば完了です。

### ステップ4: CloudFrontにカスタムドメインを適用

証明書が検証されたら、OpenTofuを再実行してCloudFrontにカスタムドメインを適用します：

```bash
cd /Users/sat0sh1kawada/Workspace/ashnova/aws/terraform
tofu apply -auto-approve
```

この時点でCloudFrontに証明書が適用され、`www.aws.ashnova.jp` がaliasとして追加されます。

### ステップ5: CNAMEレコードを追加

最後に、ashnova.jpのDNSゾーンに以下のCNAMEレコードを追加します：

```bash
# CloudFrontドメイン名を確認
cd /Users/sat0sh1kawada/Workspace/ashnova/aws/terraform
tofu output -raw cloudfront_domain_name
```

DNSレコード：

```
名前: www.aws.ashnova.jp
タイプ: CNAME
値: [上記で取得したCloudFrontドメイン名]
```

例：

```
名前: www.aws.ashnova.jp
タイプ: CNAME
値: d2w2fmi85qbw24.cloudfront.net
```

### ステップ6: 動作確認

DNS伝播後（通常5〜60分）、以下のコマンドで確認：

```bash
# DNS解決の確認
dig www.aws.ashnova.jp

# HTTPSアクセスの確認
curl -I https://www.aws.ashnova.jp
```

ブラウザでアクセス：

```
https://www.aws.ashnova.jp
```

## トラブルシューティング

### 証明書の検証が進まない

1. DNSレコードが正しく追加されているか確認：

```bash
dig _xxxxx.www.aws.ashnova.jp CNAME
```

2. DNS伝播を確認（オンラインツール）：
   - https://www.whatsmydns.net/
   - https://dnschecker.org/

3. 証明書の詳細情報を確認：

```bash
aws acm describe-certificate \
  --certificate-arn $(tofu output -raw acm_certificate_arn) \
  --region us-east-1 \
  --profile satoshi
```

### CloudFrontの更新エラー

証明書が `ISSUED` 状態になっていることを確認してから再度 `tofu apply` を実行してください。

## 重要な注意事項

1. **DNS検証レコードは永続的に保持してください** - 証明書の自動更新に必要です
2. **証明書はus-east-1リージョンに作成されます** - CloudFrontの要件です
3. **DNS伝播には時間がかかります** - 最大48時間（通常は数分〜数時間）
4. **証明書検証のタイムアウト** - Terraform/OpenTofuは10分でタイムアウトしますが、証明書自体の作成は継続されます

## 現在の設定を元に戻す（必要な場合）

カスタムドメインを無効化する場合：

```bash
cd /Users/sat0sh1kawada/Workspace/ashnova/aws/terraform
cat > terraform.tfvars <<EOF
# domain_name = ""
EOF
tofu apply -auto-approve
```

これでCloudFrontはデフォルトドメインに戻ります。
