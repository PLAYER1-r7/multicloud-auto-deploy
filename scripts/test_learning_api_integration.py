#!/usr/bin/env python3
"""
AWS Learning Assistant - 統合テスト

ローカルで FastAPI サーバーを起動して、
学習教材API エンドポイントをテストします。

使用法:
  python scripts/test_learning_api_integration.py
"""

import sys
from pathlib import Path

# Python パスを設定
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "api"))

from app.main import app
from fastapi.testclient import TestClient


def create_mock_solve_response_dict() -> dict:
    """テスト用の模擬 SolveResponse をJSON形式で返す"""
    return {
        "requestId": "test-2025-tokyo-1",
        "status": "ok",
        "problemText": """
        問題：関数 f(x) = log(1 + x) について、以下の問いに答えよ。
        (1) f(x) の Taylor 級数展開を求めよ。
        (2) 定積分 ∫_0^1 [log(1 + x) / x] dx を計算せよ。
        """.strip(),
        "answer": {
            "final": "∫_0^1 [log(1 + x) / x] dx = π²/12",
            "latex": r"\frac{\pi^2}{12}",
            "steps": [
                "f(x) = log(1 + x) の Taylor 級数展開： f(x) = Σ_{n=1}^{∞} (-1)^{n+1} x^n / n (-1 < x ≤ 1)",
                "log(1 + x) / x = Σ_{n=1}^{∞} (-1)^{n+1} x^{n-1} / n",
                "∫_0^1 [log(1 + x) / x] dx = Σ_{n=1}^{∞} (-1)^{n+1} ∫_0^1 x^{n-1} / n dx",
                "= Σ_{n=1}^{∞} (-1)^{n+1} / (n² ) = η(2) = π²/12",
            ],
            "diagramGuide": None,
            "plotData": {"needPlot": False},
            "confidence": 0.95,
        },
        "meta": {
            "ocrProvider": "azure",
            "ocrSource": "azure_di_merged",
            "ocrScore": 1.389,
            "ocrCandidates": 5,
            "model": "gpt-4o",
            "latencyMs": 4230,
            "costUsd": 0.0045,
        },
    }


def test_learning_api_integration():
    """FastAPI エンドポイントの統合テストを実行"""
    print("=" * 80)
    print("AWS Learning Assistant - 統合テスト（FastAPI エンドポイント）")
    print("=" * 80)
    print()

    # テストクライアントを初期化
    client = TestClient(app)
    print("✓ TestClient を初期化しました")
    print()

    # Test 1: 教材生成エンドポイント
    print("📝 [Test 1] POST /v1/learn/materials/from-solve")
    print()

    solve_response_dict = create_mock_solve_response_dict()
    exam_dict = {
        "university": "tokyo",
        "year": 2025,
        "subject": "math",
        "questionNo": "1",
    }

    request_body = {
        "solve_response": solve_response_dict,
        "exam": exam_dict,
        "problem_image_url": "http://server-test.net/math/tokyo/q_jpg/2025_1.jpg",
    }

    response = client.post("/v1/learn/materials/from-solve", json=request_body)

    if response.status_code == 200:
        print(f"  ✅ Status: {response.status_code}")
        material = response.json()
        material_id = material["materialId"]
        print(f"  ✅ Material ID: {material_id}")
        print(f"  ✅ Outline steps: {len(material['outline'])}")
        print(f"  ✅ Key concepts: {material['keyConcepts']}")
        print(f"  ✅ Difficulty: {material['difficultyLevel']}")
        print()
    else:
        print(f"  ❌ Status: {response.status_code}")
        print(f"  Error: {response.json()}")
        return False

    # Test 2: 単一教材取得エンドポイント
    print("📚 [Test 2] GET /v1/learn/materials/{material_id}")
    print()

    response = client.get(f"/v1/learn/materials/{material_id}")
    if response.status_code == 200:
        print(f"  ✅ Status: {response.status_code}")
        material = response.json()
        print(f"  ✅ Retrieved material: {material['materialId']}")
        print()
    else:
        print(f"  ❌ Status: {response.status_code}")
        return False

    # Test 3: アウトラインエンドポイント
    print("📖 [Test 3] GET /v1/learn/materials/{material_id}/outline")
    print()

    response = client.get(f"/v1/learn/materials/{material_id}/outline")
    if response.status_code == 200:
        print(f"  ✅ Status: {response.status_code}")
        outline_data = response.json()
        print(f"  ✅ Outline steps: {len(outline_data['outline'])}")
        for step in outline_data["outline"][:2]:
            print(f"      Step {step['step_number']}: {step['brief'][:50]}...")
        print()
    else:
        print(f"  ❌ Status: {response.status_code}")
        return False

    # Test 4: クイズエンドポイント
    print("❓ [Test 4] GET /v1/learn/materials/{material_id}/quiz")
    print()

    response = client.get(f"/v1/learn/materials/{material_id}/quiz")
    if response.status_code == 200:
        print(f"  ✅ Status: {response.status_code}")
        quiz_data = response.json()
        print(f"  ✅ Quiz questions: {len(quiz_data['quiz_questions'])}")
        for q in quiz_data["quiz_questions"][:2]:
            print(f"      Q: {q['questionText'][:50]}...")
        print()
    else:
        print(f"  ❌ Status: {response.status_code}")
        return False

    # Test 5: よくある間違いエンドポイント
    print("⚠️  [Test 5] GET /v1/learn/materials/{material_id}/mistakes")
    print()

    response = client.get(f"/v1/learn/materials/{material_id}/mistakes")
    if response.status_code == 200:
        print(f"  ✅ Status: {response.status_code}")
        mistakes_data = response.json()
        print(f"  ✅ Common mistakes: {len(mistakes_data['common_mistakes'])}")
        for mistake in mistakes_data["common_mistakes"][:2]:
            print(f"      - {mistake['mistakeDescription']}")
        print()
    else:
        print(f"  ❌ Status: {response.status_code}")
        return False

    # Test 6: 参考問題エンドポイント
    print("🔗 [Test 6] GET /v1/learn/materials/{material_id}/references")
    print()

    response = client.get(f"/v1/learn/materials/{material_id}/references")
    if response.status_code == 200:
        print(f"  ✅ Status: {response.status_code}")
        refs_data = response.json()
        print(f"  ✅ Reference problems: {len(refs_data['reference_problems'])}")
        for ref in refs_data["reference_problems"][:2]:
            print(f"      - {ref['university']} {ref['year']} 問{ref['questionNo']}")
        print()
    else:
        print(f"  ❌ Status: {response.status_code}")
        return False

    # Test 7: 404 エラーハンドリング
    print("🔍 [Test 7] 404 エラーハンドリング")
    print()

    response = client.get("/v1/learn/materials/nonexistent-id")
    if response.status_code == 404:
        print("  ✅ Correctly returned 404 for nonexistent material")
        print()
    else:
        print(f"  ❌ Expected 404, got {response.status_code}")
        return False

    # 最終結果
    print("=" * 80)
    print("✅ すべての統合テストが成功しました！")
    print("=" * 80)
    print()
    print("実装済み機能:")
    print("  ✓ LearningMaterial モデル定義")
    print("  ✓ MaterialGenerator - Azure解答から教材生成")
    print("  ✓ FastAPI ルート統合")
    print("  ✓ 複数のGETエンドポイント（アウトライン、クイズ等）")
    print()
    print("次のステップ:")
    print("  1. → AWS Bedrock との統合（解説拡張）")
    print("  2. → Amazon Personalize との統合（推薦エンジン）")
    print("  3. → Amazon Polly との統合（音声化）")
    print("  4. → フロントエンドUI実装")
    print("  5. → データベース永続化（DynamoDB/Cosmos DB/Firestore）")
    print()

    return True


if __name__ == "__main__":
    try:
        success = test_learning_api_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
