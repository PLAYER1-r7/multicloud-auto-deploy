#!/bin/bash

# API統合テストスクリプト
# Lambda + API Gateway + DynamoDB の完全な動作テスト

set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 設定
API_ENDPOINT="${API_ENDPOINT:-}"
VERBOSE="${VERBOSE:-false}"

# ヘルプメッセージ
show_help() {
    cat << EOF
使用方法: $0 [OPTIONS]

API統合テストを実行します。全てのCRUD操作をテストします。

オプション:
    -e, --endpoint URL    APIエンドポイントURL（必須）
    -v, --verbose         詳細な出力を表示
    -h, --help            このヘルプメッセージを表示

例:
    $0 -e https://abc123.execute-api.ap-northeast-1.amazonaws.com
    $0 --endpoint https://abc123.execute-api.ap-northeast-1.amazonaws.com --verbose

EOF
}

# 引数パース
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--endpoint)
            API_ENDPOINT="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}エラー: 不明なオプション: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# エンドポイントチェック
if [ -z "$API_ENDPOINT" ]; then
    echo -e "${RED}エラー: APIエンドポイントが指定されていません${NC}"
    show_help
    exit 1
fi

# APIエンドポイントから末尾のスラッシュを削除
API_ENDPOINT="${API_ENDPOINT%/}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}API統合テスト${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "エンドポイント: $API_ENDPOINT"
echo ""

# テスト結果カウンター
TESTS_PASSED=0
TESTS_FAILED=0
TOTAL_TESTS=0

# テスト実行関数
run_test() {
    local test_name="$1"
    local method="$2"
    local path="$3"
    local data="$4"
    local expected_status="$5"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo -n "テスト $TOTAL_TESTS: $test_name ... "
    
    # リクエスト実行
    if [ -z "$data" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API_ENDPOINT$path" \
            -H "Content-Type: application/json")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" "$API_ENDPOINT$path" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi
    
    # レスポンスボディとステータスコードを分離
    response_body=$(echo "$response" | head -n -1)
    status_code=$(echo "$response" | tail -n 1)
    
    # ステータスコードチェック
    if [ "$status_code" -eq "$expected_status" ]; then
        echo -e "${GREEN}✅ PASS${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        
        if [ "$VERBOSE" = true ]; then
            echo "  ステータス: $status_code"
            echo "  レスポンス: $response_body" | jq . 2>/dev/null || echo "$response_body"
        fi
    else
        echo -e "${RED}❌ FAIL${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo "  期待: $expected_status"
        echo "  実際: $status_code"
        echo "  レスポンス: $response_body"
    fi
    
    echo ""
    
    # レスポンスボディを返す（次のテストで使用するため）
    echo "$response_body"
}

# テスト1: ヘルスチェック
echo -e "${YELLOW}=== ヘルスチェック ===${NC}"
run_test "ヘルスチェック" "GET" "/" "" 200 > /dev/null

# テスト2: メッセージ一覧取得（初期状態）
echo -e "${YELLOW}=== メッセージ一覧取得 ===${NC}"
messages_response=$(run_test "メッセージ一覧取得" "GET" "/api/messages/" "" 200)

# テスト3: メッセージ作成
echo -e "${YELLOW}=== メッセージ作成 ===${NC}"
create_data='{
  "content": "統合テストメッセージ",
  "author": "Test Script"
}'
created_message=$(run_test "メッセージ作成" "POST" "/api/messages/" "$create_data" 200)

# 作成されたメッセージのIDを取得
MESSAGE_ID=$(echo "$created_message" | jq -r '.id' 2>/dev/null)

if [ -z "$MESSAGE_ID" ] || [ "$MESSAGE_ID" == "null" ]; then
    echo -e "${RED}エラー: メッセージIDを取得できませんでした${NC}"
    echo "レスポンス: $created_message"
    exit 1
fi

echo "作成されたメッセージID: $MESSAGE_ID"
echo ""

# テスト4: メッセージ一覧取得（作成後）
echo -e "${YELLOW}=== メッセージ一覧取得（作成後） ===${NC}"
run_test "メッセージ一覧取得" "GET" "/api/messages/" "" 200 > /dev/null

# テスト5: 特定のメッセージ取得
echo -e "${YELLOW}=== 特定のメッセージ取得 ===${NC}"
run_test "メッセージ取得" "GET" "/api/messages/$MESSAGE_ID" "" 200 > /dev/null

# テスト6: メッセージ更新
echo -e "${YELLOW}=== メッセージ更新 ===${NC}"
update_data='{
  "content": "更新されたテストメッセージ ✅"
}'
run_test "メッセージ更新" "PUT" "/api/messages/$MESSAGE_ID" "$update_data" 200 > /dev/null

# テスト7: 更新後のメッセージ取得
echo -e "${YELLOW}=== 更新後のメッセージ取得 ===${NC}"
updated_message=$(run_test "更新後メッセージ取得" "GET" "/api/messages/$MESSAGE_ID" "" 200)

# 更新内容の確認
updated_content=$(echo "$updated_message" | jq -r '.content' 2>/dev/null)
if echo "$updated_content" | grep -q "更新されたテストメッセージ"; then
    echo -e "${GREEN}✅ 更新内容が正しく反映されています${NC}"
else
    echo -e "${RED}❌ 更新内容が反映されていません${NC}"
    echo "期待: 更新されたテストメッセージ ✅"
    echo "実際: $updated_content"
fi
echo ""

# テスト8: メッセージ削除
echo -e "${YELLOW}=== メッセージ削除 ===${NC}"
run_test "メッセージ削除" "DELETE" "/api/messages/$MESSAGE_ID" "" 200 > /dev/null

# テスト9: 削除後のメッセージ取得（404が期待される）
echo -e "${YELLOW}=== 削除後のメッセージ取得（エラーテスト） ===${NC}"
run_test "削除後メッセージ取得" "GET" "/api/messages/$MESSAGE_ID" "" 404 > /dev/null

# テスト10: ページネーションテスト
echo -e "${YELLOW}=== ページネーション ===${NC}"
run_test "ページネーション（page=1）" "GET" "/api/messages/?page=1&page_size=5" "" 200 > /dev/null

# テスト11: 無効なメッセージID（エラーハンドリングテスト）
echo -e "${YELLOW}=== エラーハンドリング ===${NC}"
run_test "無効なID取得" "GET" "/api/messages/invalid-id-12345" "" 404 > /dev/null

# テスト12: 空のコンテンツでメッセージ作成（バリデーションエラー期待）
echo -e "${YELLOW}=== バリデーションテスト ===${NC}"
invalid_data='{
  "content": "",
  "author": "Test"
}'
run_test "空コンテンツ作成" "POST" "/api/messages/" "$invalid_data" 422 > /dev/null

# テスト結果サマリー
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}テスト結果サマリー${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "総テスト数: $TOTAL_TESTS"
echo -e "${GREEN}成功: $TESTS_PASSED${NC}"
echo -e "${RED}失敗: $TESTS_FAILED${NC}"
echo ""

SUCCESS_RATE=$(awk "BEGIN {printf \"%.1f\", ($TESTS_PASSED/$TOTAL_TESTS)*100}")
echo "成功率: $SUCCESS_RATE%"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 全てのテストが成功しました！${NC}"
    exit 0
else
    echo -e "${RED}⚠️  一部のテストが失敗しました${NC}"
    exit 1
fi
