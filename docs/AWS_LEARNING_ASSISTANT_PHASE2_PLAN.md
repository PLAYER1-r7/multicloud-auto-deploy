# AWS Learning Assistant - PHASE 2 実装計画

## 概要

PHASE 1で完成した教材生成パイプラインを、AWSの高度なサービスを活用して、学習者向けの豊かなコンテンツに変換します。

**期間**: 3週間（4週目から6週目）
**目標**: 完全な学習プラットフォーム（API + フロントエンド）
**主要成果**: 説明動画、個人化推薦、インタラクティブUI

---

## 1. Bedrock統合 - 解説拡張

### 目的

PHASE 1で生成された基本的な解説（outline + step）を、Bedrockの大規模言語モデル（Claude）を使用して、学習者向けの詳細な説明に拡張します。

### 実装パターン

```
PHASE 1: LearningMaterial
  ├─ outline[]: ステップの概要
  ├─ solutionSteps[]: 解答ステップ
  └─ commonMistakes[]: よくある間違い

↓ Bedrock Integration ↓

PHASE 2: EnhancedMaterial
  ├─ detailedExplanation: Claude生成の詳細説明
  ├─ conceptDeepDive: 概念の深掘り
  ├─ mistakeAnalysis: 間違いパターンの分析
  ├─ solutionInsight: 解答方法の洞察
  └─ learningResources: 関連学習リソース
```

### 実装詳細

#### 1.1 Bedrockクライアント初期化

ファイル: `services/api/bedrock_integration.py`

```python
import boto3
import json
from typing import Dict, List

class BedrockIntegration:
    def __init__(self):
        self.client = boto3.client('bedrock-runtime', region_name='us-east-1')
        self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"

    def generate_detailed_explanation(self, material: dict) -> str:
        """
        LearningMaterialから詳細な説明を生成
        """
        prompt = self._build_prompt(material)
        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps({
                "anthropic_version": "bedrock-2023-06-01",
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}]
            })
        )
        return json.loads(response['body'].read())['content'][0]['text']

    def _build_prompt(self, material: dict) -> str:
        """
        プロンプトを構築
        """
        problem = material['problemText']
        steps = '\n'.join([f"{i+1}. {s['brief']}"
                          for i, s in enumerate(material['outline'][:3])])

        return f"""
以下の数学問題の解答について、学習者向けの詳細な説明を生成してください。
各ステップを わかりやすく説明し、重要な概念や注意点を含めてください。

【問題】
{problem}

【解答ステップ】
{steps}

【出力形式】
1. **概要**: 問題のポイント（2-3文）
2. **ステップ解説**: 各ステップの詳細説明（各100-150字）
3. **重要概念**: この問題で学べる数学概念（3-4個）
4. **参考**: 関連する公式や定理

日本語で、中学～高校レベルの学習者が理解できる表現を使用してください。
"""
```

#### 1.2 FastAPIエンドポイント拡張

ファイル: `services/api/routes/learning.py` に追加

```python
from services.api.bedrock_integration import BedrockIntegration

bedrock = BedrockIntegration()

@router.post("/v1/learn/materials/{material_id}/enhance")
async def enhance_material(material_id: str):
    """
    PHASE 1の教材をBedrockで拡張
    """
    # キャッシュから教材を取得
    material = _material_cache.get(material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    # Bedrockで拡張
    explanation = bedrock.generate_detailed_explanation(material)

    # 拡張データを追加
    enhanced = {
        **material,
        "detailedExplanation": explanation,
        "enhanced_at": datetime.utcnow().isoformat()
    }

    # キャッシュに保存
    _material_cache[material_id] = enhanced

    return enhanced
```

### テスト実装

ファイル: `services/api/test_bedrock_enhancement.py`

```python
def test_bedrock_enhancement():
    """Bedrock統合テスト（モック）"""
    material = {
        "problemText": "∫ x/√(x²+1) dx を求めよ",
        "outline": [
            {"stepNumber": 1, "brief": "u = x²+1 と置換"},
            {"stepNumber": 2, "brief": "du/dx = 2x より dx = du/(2x)"}
        ]
    }

    # Mock Bedrockレスポンス
    mock_explanation = """
    【概要】
    この問題は置換積分の典型例です。...

    【ステップ解説】
    Step 1: u置換を選択する理由は...
    Step 2: 微分を利用して...
    """

    # 拡張データを生成
    enhanced = {
        **material,
        "detailedExplanation": mock_explanation
    }

    print("✅ Bedrock Enhancement Test Passed")
```

---

## 2. Polly統合 - 音声化

### 目的

拡張された解説をPollyで音声ファイルに変換し、学習者が音声で学習できるようにします。

### 実装パターン

```
EnhancedMaterial (text)
    ↓
    ├─ Polly: 標準テキスト → MP3音声ファイル
    ├─ 言語: 日本語 (ja-JP)
    ├─ 声優: Mizuki（女性）または Takumi（男性）
    └─ 出力: S3 (s3://learning-assets/audio/{materialId}.mp3)
```

### 実装詳細

#### 2.1 Pollyクライアント

ファイル: `services/api/polly_integration.py`

```python
import boto3
import io
from botocore.exceptions import ClientError

class PollyIntegration:
    def __init__(self):
        self.client = boto3.client('polly', region_name='us-east-1')
        self.s3 = boto3.client('s3')
        self.bucket = 'learning-assets'

    def synthesize_audio(self, text: str, material_id: str) -> dict:
        """
        テキストを音声ファイルに変換
        """
        try:
            response = self.client.synthesize_speech(
                Text=text,
                OutputFormat='mp3',
                VoiceId='Mizuki',  # 日本語女性声
                Engine='neural',  # ニューラルエンジン（自然な発音）
                LanguageCode='ja-JP'
            )

            # AudioStreamを取得
            audio_stream = response['AudioStream'].read()

            # S3にアップロード
            s3_key = f"audio/{material_id}/explanation.mp3"
            self.s3.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=audio_stream,
                ContentType='audio/mpeg',
                Metadata={'material_id': material_id}
            )

            # プリサインドURLを生成（24時間有効）
            url = self.s3.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': s3_key},
                ExpiresIn=86400
            )

            return {
                "status": "success",
                "audio_url": url,
                "s3_key": s3_key,
                "duration_seconds": response.get('RequestCharacters', 0) / 175  # 推定値
            }
        except ClientError as e:
            return {"status": "error", "message": str(e)}

    def batch_synthesize(self, materials: List[dict]) -> List[dict]:
        """
        複数の教材を処理（Polly batch processing）
        """
        results = []
        for material in materials:
            result = self.synthesize_audio(
                material['detailedExplanation'],
                material['materialId']
            )
            results.append({
                "material_id": material['materialId'],
                **result
            })
        return results
```

#### 2.2 FASTAPIエンドポイント

ファイル: `services/api/routes/learning.py` に追加

```python
from services.api.polly_integration import PollyIntegration

polly = PollyIntegration()

@router.post("/v1/learn/materials/{material_id}/audio")
async def generate_audio(material_id: str):
    """
    教材をPollyで音声化
    """
    material = _material_cache.get(material_id)
    if not material:
        raise HTTPException(status_code=404)

    if 'detailedExplanation' not in material:
        raise HTTPException(status_code=400,
                          detail="Material not enhanced yet")

    # 音声生成
    audio_result = polly.synthesize_audio(
        material['detailedExplanation'],
        material_id
    )

    # 音声メタデータを保存
    material['audio'] = audio_result
    _material_cache[material_id] = material

    return {
        "material_id": material_id,
        "audio": audio_result
    }

@router.get("/v1/learn/materials/{material_id}/audio")
async def get_audio(material_id: str):
    """
    教材の音声ファイルを取得
    """
    material = _material_cache.get(material_id)
    if not material or 'audio' not in material:
        raise HTTPException(status_code=404)

    return material['audio']
```

---

## 3. Personalize統合 - 推薦

### 目的

ユーザーの学習履歴に基づいて、次に学ぶべき関連問題を推薦します。

### 実装パターン

```
User Learning History
    ├─ viewed_materials[]
    ├─ quiz_scores{}
    └─ time_spent{}

↓ Personalize ↓

Recommendations
    ├─ similar_problems[] (75%+ similarity)
    ├─ next_difficulty_level
    └─ suggested_topics[]
```

### 実装詳細

#### 3.1 Personalizeクライアント

ファイル: `services/api/personalize_integration.py`

```python
import boto3
from datetime import datetime, timedelta

class PersonalizeIntegration:
    def __init__(self):
        self.client = boto3.client('personalize-runtime', region_name='us-east-1')
        self.campaign_arn = "arn:aws:personalize:us-east-1:....:campaign/learning-recommendations"

    def get_recommendations(self, user_id: str, num_results: int = 5) -> dict:
        """
        ユーザーの学習履歴に基づいて推薦を取得
        """
        try:
            response = self.client.get_recommendations(
                campaignArn=self.campaign_arn,
                userId=user_id,
                numResults=num_results,
                context={
                    'DIFFICULTY': 'intermediate',
                    'SUBJECT': 'mathematics'
                }
            )

            recommendations = []
            for item in response.get('itemList', []):
                recommendations.append({
                    "material_id": item['itemId'],
                    "score": float(item['score']),
                    "reason": self._get_reason(item)
                })

            return {
                "user_id": user_id,
                "recommendations": recommendations,
                "generated_at": datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _get_reason(self, item: dict) -> str:
        """
        推薦理由を生成
        """
        score = float(item['score'])
        if score > 0.8:
            return "あなたの学習パターンから最適"
        elif score > 0.6:
            return "関連トピックのため推奨"
        else:
            return "難易度がちょうどいい"

    def track_event(self, user_id: str, material_id: str,
                   event_type: str, properties: dict = None):
        """
        ユーザーイベントをPersonalizeに記録
        event_type: 'view', 'quiz_complete', 'bookmark'
        """
        self.client.put_events(
            trackingId='learning-assistant-tracker',
            userId=user_id,
            sessionId=f"{user_id}-{datetime.utcnow().timestamp()}",
            eventList=[
                {
                    'eventId': f"{material_id}-{datetime.utcnow().timestamp()}",
                    'eventType': event_type,
                    'eventValue': 1.0,
                    'itemId': material_id,
                    'properties': json.dumps(properties or {}),
                    'sentAt': int(datetime.utcnow().timestamp())
                }
            ]
        )
```

#### 3.2 FASTAPIエンドポイント

ファイル: `services/api/routes/learning.py` に追加

```python
from services.api.personalize_integration import PersonalizeIntegration

personalize = PersonalizeIntegration()

@router.get("/v1/learn/users/{user_id}/recommendations")
async def get_user_recommendations(user_id: str, num_results: int = 5):
    """
    ユーザーへの推薦を取得
    """
    recommendations = personalize.get_recommendations(user_id, num_results)
    return recommendations

@router.post("/v1/learn/users/{user_id}/events")
async def track_user_event(user_id: str,
                          material_id: str,
                          event_type: str,
                          quiz_score: float = None):
    """
    ユーザーイベントを記録
    """
    properties = {}
    if quiz_score is not None:
        properties['quiz_score'] = quiz_score

    personalize.track_event(user_id, material_id, event_type, properties)

    return {
        "status": "tracked",
        "user_id": user_id,
        "material_id": material_id,
        "event_type": event_type
    }
```

---

## 4. React UI - フロントエンド

### 目的

生成された教材、音声、推薦をインタラクティブなWebアプリケーションで表示します。

### ファイル構造

```
services/frontend_react/
├── src/
│   ├── components/
│   │   ├── MaterialViewer.tsx       # 教材表示
│   │   ├── AudioPlayer.tsx          # 音声再生
│   │   ├── QuizComponent.tsx        # クイズUX
│   │   ├── RecommendationCard.tsx   # 推薦カード
│   │   └── Dashboard.tsx            # ダッシュボード
│   ├── hooks/
│   │   ├── useUserProfile.ts        # ユーザープロフィール
│   │   ├── useMaterialData.ts       # 教材取得
│   │   └── useRecommendations.ts    # 推薦取得
│   ├── services/
│   │   └── api.ts                   # API呼び出し
│   └── App.tsx
├── package.json
└── tsconfig.json
```

### 4.1 プロジェクト初期化

```bash
cd services/frontend_react
npx create-react-app . --template typescript
npm install axios react-router-dom zustand
```

### 4.2 主要コンポーネント例

#### MaterialViewer.tsx

```typescript
import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface Material {
  materialId: string;
  problemText: string;
  detailedExplanation: string;
  outline: Array<{ stepNumber: number; brief: string; details: string }>;
  keyConcepts: string[];
}

export const MaterialViewer: React.FC<{ materialId: string }> = ({ materialId }) => {
  const [material, setMaterial] = useState<Material | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchMaterial = async () => {
      const response = await axios.get(`/api/v1/learn/materials/${materialId}`);
      setMaterial(response.data);
      setLoading(false);
    };
    fetchMaterial();
  }, [materialId]);

  if (loading) return <div>読み込み中...</div>;
  if (!material) return <div>教材が見つかりません</div>;

  return (
    <div className="material-viewer">
      <h2>問題</h2>
      <div className="problem">{material.problemText}</div>

      <h3>詳細解説</h3>
      <div className="explanation">{material.detailedExplanation}</div>

      <h3>ステップ</h3>
      <ol>
        {material.outline.map((step) => (
          <li key={step.stepNumber}>
            <strong>{step.brief}</strong>
            <p>{step.details}</p>
          </li>
        ))}
      </ol>

      <h3>重要概念</h3>
      <ul>
        {material.keyConcepts.map((concept) => (
          <li key={concept}>{concept}</li>
        ))}
      </ul>
    </div>
  );
};
```

#### AudioPlayer.tsx

```typescript
import React, { useRef } from 'react';

export const AudioPlayer: React.FC<{ audioUrl: string }> = ({ audioUrl }) => {
  const audioRef = useRef<HTMLAudioElement>(null);

  return (
    <div className="audio-player">
      <button onClick={() => audioRef.current?.play()}>▶ 再生</button>
      <button onClick={() => audioRef.current?.pause()}>⏸ 一時停止</button>
      <audio ref={audioRef} src={audioUrl} />
    </div>
  );
};
```

---

## 5. 統合テスト

### ファイル: `services/api/test_phase2_integration.py`

```python
def test_phase2_full_flow():
    """PHASE 2全体の統合テスト"""
    print("🧪 PHASE 2 統合テスト開始")

    # 1. PHASE 1の教材を取得
    material_id = "test-material-001"
    material = get_mock_phase1_material()

    # 2. Bedrock統合テスト
    print("\n✓ Step 1: Bedrock Enhancement...")
    enhanced = bedrock.generate_detailed_explanation(material)
    assert len(enhanced) > 100, "Explanation too short"

    # 3. Polly統合テスト
    print("✓ Step 2: Polly Audio Synthesis...")
    audio_result = polly.synthesize_audio(enhanced, material_id)
    assert audio_result['status'] == 'success', "Polly synthesis failed"

    # 4. Personalize統合テスト
    print("✓ Step 3: Personalize Recommendations...")
    user_id = "test-user-001"
    recommendations = personalize.get_recommendations(user_id)
    assert len(recommendations['recommendations']) > 0, "No recommendations"

    # 5. ユーザーイベント記録
    print("✓ Step 4: Track User Events...")
    personalize.track_event(user_id, material_id, 'view')
    personalize.track_event(user_id, material_id, 'quiz_complete', {'quiz_score': 0.85})

    print("\n✅ PHASE 2 統合テスト完了")
```

---

## 6. デプロイ手順

### 6.1 環境変数設定

```bash
# .env.phase2
AWS_BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
AWS_POLLY_LANGUAGE=ja-JP
AWS_PERSONALIZE_CAMPAIGN_ARN=arn:aws:personalize:...
LEARNING_ASSETS_BUCKET=learning-assets
```

### 6.2 AWS IAMロール設定

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "polly:SynthesizeSpeech",
        "s3:*",
        "personalize:*"
      ],
      "Resource": "*"
    }
  ]
}
```

### 6.3 デプロイコマンド

```bash
# 1. 依存関係を追加
pip install boto3 pydantic

# 2. テストを実行
python3 services/api/test_phase2_integration.py

# 3. FastAPIサーバーを起動
cd services/api && uvicorn main:app --reload --port 8000

# 4. React UIをビルド
cd services/frontend_react
npm run build
npm run deploy
```

---

## 7. 期待される成果

### 成果物

- ✅ BedrockAPI連携モジュール（500行）
- ✅ Polly音声生成機能（200行）
- ✅ Personalize推薦エンジン（300行）
- ✅ React UIコンポーネント（800行）
- ✅ 統合テストスイート（300行）

### KPI

| 指標                    | 目標      | 達成条件                     |
| ----------------------- | --------- | ---------------------------- |
| API応答時間             | <2秒      | Bedrock: <1.5s, Polly: <0.5s |
| 音声品質                | 4.5/5.0   | ユーザーテストで確認         |
| 推薦精度                | >75%      | CTR測定                      |
| React UI パフォーマンス | LCP <2.5s | Lighthouse スコア >90        |

---

## 8. スケジュール

| 週  | タスク                  | 状態       | 備考                 |
| --- | ----------------------- | ---------- | -------------------- |
| 4   | Bedrock + Polly基本実装 | ▶ 開始予定 | モック実装から始める |
| 5   | Personalize + API整備   | ⏳ 予定    | 本番レベルの実装     |
| 6   | React UI + 統合テスト   | ⏳ 予定    | E2Eテストを含める    |

---

## 準備チェックリスト

- [ ] AWSアカウント設定確認
- [ ] Bedrockのモデルアクセスをリクエスト
- [ ] Pollyのニューラルエンジンはサポート確認
- [ ] PersonalizeのCampaignを作成
- [ ] PHASE 1のテストデータが使用可能か確認
- [ ] React環境（Node.js 16+）確認

---

**次ステップ**: Bedrock統合の実装を開始します。
