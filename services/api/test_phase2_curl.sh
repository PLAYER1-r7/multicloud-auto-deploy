#!/bin/bash
# PHASE 2 エンドポイント フルテスト
# サーバーが http://localhost:8000 で起動していることを前提

set -e

BASE_URL="http://localhost:8000"

echo "================================"
echo "🧪 PHASE 2 エンドポイント テスト"
echo "================================"
echo ""

# ========== Step 1: 教材生成 ==========
echo "📝 STEP 1: 教材生成"
echo "POST /v1/learn/materials/from-solve"

MATERIAL_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/learn/materials/from-solve" \
  -H "Content-Type: application/json" \
  -d '{
    "solve_response": {
      "request_id": "test-phase2-001",
      "status": "success",
      "problem_text": "次の不定積分を求めよ。\n\n∫ x/√(x²+1) dx",
      "answer": {
        "final": "√(x²+1) + C",
        "latex": "\\sqrt{x^2 + 1} + C",
        "steps": ["u = x²+1 と置換", "微分", "置換積分", "√u + C"],
        "confidence": 0.95
      },
      "meta": {
        "ocr_provider": "azure",
        "model": "azure-doc-intelligence",
        "latency_ms": 1200,
        "cost_usd": 0.05
      }
    },
    "exam": {
      "university": "tokyo",
      "year": 2025,
      "subject": "math",
      "question_no": "1"
    },
    "problem_image_url": "http://server-test.net/math/tokyo/q_jpg/2025_1.jpg"
  }')

MATERIAL_ID=$(echo "$MATERIAL_RESPONSE" | grep -o '"material_id":"[^"]*"' | head -1 | cut -d'"' -f4 || echo "$MATERIAL_RESPONSE" | grep -o '"materialId":"[^"]*"' | head -1 | cut -d'"' -f4)

if [ -z "$MATERIAL_ID" ]; then
  echo "❌ 教材生成失敗"
  echo "$MATERIAL_RESPONSE" | jq . 2>/dev/null || echo "$MATERIAL_RESPONSE"
  exit 1
fi

echo "✅ 教材生成成功"
echo "   Material ID: $MATERIAL_ID"
echo ""

# ========== Step 2: Bedrock 拡張 ==========
echo "🤖 STEP 2: Bedrock で拡張"
echo "POST /v1/learn/materials/$MATERIAL_ID/enhance"

ENHANCE_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/learn/materials/$MATERIAL_ID/enhance")

HAS_EXPLANATION=$(echo "$ENHANCE_RESPONSE" | grep -c "detailed_explanation\|detailedExplanation" || echo "0")

if [ "$HAS_EXPLANATION" -gt 0 ]; then
  echo "✅ Bedrock 拡張成功"
  echo "   Has detailed_explanation: true"
else
  echo "⚠️ Bedrock 拡張（要確認）"
fi

echo "$ENHANCE_RESPONSE" | jq '.detailed_explanation // .detailedExplanation' 2>/dev/null | head -3 || true
echo ""

# ========== Step 3: Polly 音声化 ==========
echo "🔊 STEP 3: Polly で音声化"
echo "POST /v1/learn/materials/$MATERIAL_ID/audio"

AUDIO_RESPONSE=$(curl -s -X POST "$BASE_URL/v1/learn/materials/$MATERIAL_ID/audio")

AUDIO_COUNT=$(echo "$AUDIO_RESPONSE" | grep -o '"[a-z_]*":"s3://' | wc -l)

if [ "$AUDIO_COUNT" -gt 0 ]; then
  echo "✅ Polly 音声化成功"
  echo "   Audio files: $AUDIO_COUNT"
  echo "$AUDIO_RESPONSE" | jq '.audio_urls // .audioUrls' 2>/dev/null || true
else
  echo "⚠️ Polly 音声化（要確認）"
  echo "$AUDIO_RESPONSE" | jq . 2>/dev/null || echo "$AUDIO_RESPONSE"
fi

echo ""

# ========== Step 4: Personalize 推薦 ==========
echo "👥 STEP 4: Personalize で推薦取得"
echo "GET /v1/learn/users/test-user-001/recommendations"

RECOMMEND_RESPONSE=$(curl -s -X GET "$BASE_URL/v1/learn/users/test-user-001/recommendations?num_results=3")

REC_COUNT=$(echo "$RECOMMEND_RESPONSE" | grep -o '"material_id"' | wc -l)

if [ "$REC_COUNT" -gt 0 ]; then
  echo "✅ Personalize 推薦成功"
  echo "   Recommendations: $REC_COUNT"
  echo "$RECOMMEND_RESPONSE" | jq '.recommendations' 2>/dev/null || true
else
  echo "⚠️ Personalize 推薦（要確認）"
fi

echo ""
echo "================================"
echo "✅ PHASE 2 エンドポイント テスト完了"
echo "================================"
