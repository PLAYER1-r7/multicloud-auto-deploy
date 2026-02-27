# OCR 数式マージ実装レポート

> 作成日: 2026-02-27
> 最終更新: 2026-02-27
> 対象ブランチ: develop
> 関連コミット: 608f98f / 4fa3394 / cc0956b / 731daac / 26e560a

---

## 1. 背景・問題定義

Azure Document Intelligence (DI) の `prebuilt-read` パスは日本語テキストを忠実に再現するが、
数式を断片化した ASCII 文字列として出力する（例: `lim n/71-+00/1/2/log/1+x%/2/dx`）。

一方、`prebuilt-layout + FORMULAS` パスは LaTeX 形式の数式を正確に抽出するが、
日本語テキストを欠落させることがある。

理想の出力は「日本語テキストを維持しつつ、数式を正確な LaTeX で置換」することであり、
これを実現する **2パスマージ** 戦略を実装した。

---

## 2. PDF テキスト抽出の日本語・数式品質改善

### 2-A. 日本語文字化け修正（commit 731daac）

**問題**: `pypdf` は CIDFont Type2（ToUnicode マップなし）の PDF に対応しておらず、
グリフ ID をそのまま Unicode コードポイントとして解釈するため、日本語が
シンハラ語・タイ語等の別文字列に化けていた。

```
# 修正前（pypdf）
1ඪฏ໘্ͷ఺ A (0 , 0) ɼB (0 , 1)…

# 修正後（pdfminer.six）
1 　座標平面上の点 A(0, 0)，B(0, 1)，C(1, 1)，D(1, 0) を考える。
```

**修正**: `_extract_text_from_pdf_bytes()` を `pdfminer.six` 優先・`pypdf` フォールバック構成に変更。
`pdfminer.six` は CIDFont の CMap を内部に保持しており日本語を正確に Unicode に変換する。

また、`pdfminer.six` が解決できなかった `(cid:N)` 表記を CID マッピングで変換する
`_fix_pdfminer_cid_chars()` を追加した。

| CID 表記    | 変換後   | 記号名                 |
| ----------- | -------- | ---------------------- |
| `(cid:53)`  | `≦`      | \leqq                  |
| `(cid:54)`  | `≧`      | \geqq                  |
| `(cid:90)`  | `∫`      | integral               |
| `(cid:88)`  | `∑`      | summation              |
| `(cid:81)`  | `∏`      | product                |
| `(cid:112)` | `∞`      | infinity               |
| `(cid:195)` | _(削除)_ | 大括弧アーティファクト |
| `(cid:33)`  | _(削除)_ | 大括弧アーティファクト |

**依存パッケージ追加**: `pdfminer.six==20260107` を全 requirements に追加。

---

### 2-B. PDF 数式テキスト正規化（commit 26e560a）

**問題**: `pdfminer.six` は縦組み数式（分数・積分上下限）を行分割して出力するため、
数式が断片化した状態でテキスト抽出される。

| 原文（PDF 内数式）  | pdfminer 生テキスト | 修正後      |
| ------------------- | ------------------- | ----------- |
| $\int_1^2$          | `∫ 2\n\n1\n`        | `∫_{1}^{2}` |
| $\lim_{n\to\infty}$ | `lim\nn→∞`          | `lim_{n→∞}` |
| $\frac{\pi}{6}$     | `π\n6`              | `π/6`       |
| $\frac{1}{2}$       | `1\n2`              | `1/2`       |
| $\frac{1}{z}$       | `1\nz`              | `1/z`       |
| $x^2$               | `x2`                | `x²`        |
| $\alpha^2$          | `α2`                | `α²`        |

**修正**: `_normalize_pdf_math_text()` を追加し、pdfminer 抽出後に自動適用。

```python
def _normalize_pdf_math_text(self, text: str) -> str:
    # Rule 1: 積分上下限  ∫ 2\n1\n   → ∫_{1}^{2}
    # Rule 2: lim 添字    lim\nn→∞   → lim_{n→∞}
    # Rule 3: 縦分割分数  π\n6       → π/6
    # Rule 4: 上付き文字  x2/α2     → x²/α²  (大文字ラベル A2,T2 は除外)
    # Rule 5: 余分な空行を最大2行に圧縮
```

**誤変換防止**: 上付き変換（Rule 4）は小文字ラテン・ギリシャ小文字のみ対象とし、
`A2`, `T2` 等の大文字インデックスラベルは変換しない。

---

## 3. 検出したバグと修正（Azure DI 2パスマージ）

> ※ 旧 §2 をリナンバー

### Bug 1: display 数式がサイレントに消える

**現象**: `azure_di_merged` 候補に display 数式が含まれない。
**根本原因**: ポリゴンマッチング失敗時、unmatched な display 数式が何も出力されずに捨てられていた。

**修正** (commit 608f98f):

- オーバーラップ閾値を 0.5 → 0.3 に引き下げ
- Point オブジェクト形式ポリゴン (`hasattr(p, "y")`) への対応追加
- Safety net: マッチしなかった display 数式を末尾に `[display] latex` として追記

### Bug 2: bytes 型による JSON シリアライズエラー

**現象**: `{"error": "TypeError", "message": "Object of type bytes is not JSON serializable"}`
**根本原因**: Azure DI SDK の一部バージョンが `polygon`, `content`, `value`, `kind` を `bytes` 型で返す。

**修正** (commit 4fa3394):

- `_ocr_read_pass`: `isinstance(raw_poly, (bytes, bytearray))` → None 扱い
- `_ocr_read_pass`: `content` が bytes なら `.decode("utf-8", errors="replace")`
- `_ocr_layout_formulas_pass`: `value`, `kind`, `polygon` に同様のガード追加

### Bug 3: ポリゴンデータが常に None でマッチング失敗

**現象**: bytes ガード後、polygon が全て None → Pass 1 が常にゼロマッチ → 数式が末尾に追記されるだけ。
**根本原因**: Bug 2 の修正で bytes ポリゴンを None にしたが、SDK がポリゴンを bytes でしか返さない環境だった。

**修正** (commit cc0956b): ヒューリスティック検出によるフォールバック（後述）。

---

## 4. ヒューリスティック数式領域検出

### 設計思想

`prebuilt-read` が数式を断片化した場合でも、その行群には以下の特徴がある：

- CJK 文字を含まない
- 短い（≤ 80 文字）
- `lim`, `log`, `\\`, `∫`, `dx`, 複数の演算子記号などを含む

これらの特徴を利用して「数式断片行の連続ブロック」を検出し、display 数式と紐付ける。

### 実装メソッド（`base_math_solver.py` に共通化）

#### `_is_formula_candidate(content: str) → bool`

弱い条件でフィルタ。CJK なし、`(N)` ラベルでない、80文字以内。

#### `_has_formula_signal(lines: list[str]) → bool`

グループに強い数学シグナルがあるか確認。
正規表現: `[\\∞∫∑∏√]|lim|log|sin|cos|tan|...|[+\-*/^=<>]{2,}`

#### `_find_formula_regions(read_lines: list[dict]) → list[tuple[int, int]]`

連続する候補行グループかつ数学シグナルあり → `(start, end)` インデックスリストを返す。

#### `_merge_read_with_formulas(read_lines, rich_formulas) → str`

2パス戦略：

```
Pass 1: ポリゴン Y オーバーラップ ≥ 30% でマッチング
Pass 2: Pass 1 でマッチしなかった display 数式を
        _find_formula_regions() の結果と文書順にペアリング
Safety net: Pass 2 でもマッチしなかったものは末尾に [display] として追记
Inline 数式: 常に末尾に [inline] として追記
```

### マッチング出力例

`prebuilt-read` 出力の断片行群:

```
lim n/71-+00
1/2
log
1+x%/2
dx
```

→ `prebuilt-layout+FORMULAS` の display 数式を適用:

```
$$\lim_{n\to\infty} n \int_1^2 \log\left(1 + \frac{x}{n}\right)^{1/2} dx$$
```

---

## 5. OCR ソース評価スコア体系

| ソース                     | ボーナス | 特性                                                     |
| -------------------------- | -------: | -------------------------------------------------------- |
| `local_reference_pdf`      |    +0.44 | ローカル PDF テキスト（最高品質）                        |
| `pdf_direct`               |    +0.34 | URL から直接取得した PDF テキスト                        |
| `gcp_vision_api`           |    +0.30 | Google Cloud Vision API                                  |
| `azure_di_merged`          |    +0.30 | Azure DI 2パスマージ（日本語 + LaTeX in-place）          |
| `gcp_vision_merged`        |    +0.28 | GCP Vision + Gemini Vision 数式マージ (本リリース)       |
| `azure_di_read+formulas`   |    +0.26 | Azure DI 日本語テキスト + 数式末尾追記（フォールバック） |
| `azure_di_layout_markdown` |    +0.12 | Azure DI Markdown（LaTeX 精度高いが日本語欠落リスク）    |
| `azure_di_read`            |     0.00 | Azure DI テキスト（数式なし）                            |

---

## 6. GCP 実装

### 設計

Azure DI に相当する `FORMULAS` 機能が GCP Vision API にはないため、
**Gemini Vision（マルチモーダル）** で数式抽出パスを担当させる。

```
Pass 1: Cloud Vision API (DOCUMENT_TEXT_DETECTION) → 日本語テキスト忠実再現
Pass 2: Gemini Vision → 画像から LaTeX 数式一覧を JSON 抽出
Merge:  _find_formula_regions() + _merge_read_with_formulas() で in-place 置換
→ candidate: gcp_vision_merged
```

### 実装メソッド（`gcp_math_solver.py`）

#### `_extract_formulas_with_gemini_vision(image_bytes) → list[dict]`

Gemini マルチモーダルに画像と以下プロンプトを渡す：

```
この数学問題の画像から、すべての数式を LaTeX で抽出してください。
display 数式（独立行）は "display"、inline 数式（文中）は "inline" として分類し、
以下の JSON 形式のみで返してください:
[{"kind":"display","value":"..."}, ...]
```

#### `_ocr_vision_pass(image_bytes) → tuple[str, list[dict]]`

Vision API テキスト + `rich_lines` リスト（polygon=None）を返す。

#### `_extract_text_with_vision_api_merged(image_bytes) → list[tuple[str, str]]`

`_extract_text_with_vision_api` の拡張版。
`gcp_vision_merged` 候補を追加して返す。

---

## 7. 検証結果（東京大学 2025 年入試数学 6 問）

実施日: 2026-02-27
API エンドポイント: `https://multicloud-auto-deploy-staging-func-d8a2guhfere0etcq.japaneast-01.azurewebsites.net/api/v1/solve`

| 問    | OCR ソース      | スコア | 問題概要                                         |
| ----- | --------------- | ------ | ------------------------------------------------ |
| 第1問 | azure_di_merged | 1.3955 | ベジェ曲線 (A,B,C,D 座標・面積・曲線長)          |
| 第2問 | azure_di_merged | 0.9285 | log 不等式 + lim 積分 (display 数式 in-place ✅) |
| 第3問 | azure_di_merged | 1.1995 | 平行四辺形 ABCD・長方形 EFGH・∠ABC=π/6           |
| 第4問 | azure_di_merged | 1.1265 | 平方数・fa(x)=x²+x-a・Na=1⟺4a+1 が素数           |
| 第5問 | azure_di_merged | 1.4058 | カードソート（バブルソート類似）・Cn 漸化式      |
| 第6問 | azure_di_merged | 1.1025 | 複素数平面・中心 1/2 半径 1/2 の円・α²+β² の範囲 |

全 6 問で `azure_di_merged` が最高スコアで選択され、display 数式の in-place 置換が機能していることを確認。

### 既知の軽微な品質問題

- **第2問**: `ェ>0` が `x>0` の代わりに出力（CJK 類似文字の OCR 誤認識）
- **第5問**: `[display] \quad` が誤検出（`_has_formula_signal` の偽陽性）
- **第6問**: 中心座標 `1/2` が `112` になる（分数の OCR 誤認識）

---

## 8. 実装ファイル一覧

| ファイル                                         | 変更概要                                                                                                                                                                                                                                                                           |
| ------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `services/api/app/services/base_math_solver.py`  | `_is_formula_candidate`, `_has_formula_signal`, `_find_formula_regions`, `_merge_read_with_formulas`, `_poly_y_range`, `_y_overlap_ratio` を共通メソッドとして追加；`_fix_pdfminer_cid_chars`, `_normalize_pdf_math_text`, `_extract_text_from_pdf_bytes`（pdfminer 優先化）を追加 |
| `services/api/app/services/azure_math_solver.py` | bytes ガード、ポリゴン処理、2パスマージ実装；共通メソッドは base から継承                                                                                                                                                                                                          |
| `services/api/app/services/gcp_math_solver.py`   | `_ocr_vision_pass`, `_extract_formulas_with_gemini_vision` 追加；GCP Vision + Gemini Vision 2パスマージ実装                                                                                                                                                                        |
| `services/api/requirements.txt`                  | `pdfminer.six==20260107` 追加                                                                                                                                                                                                                                                      |
| `services/api/requirements-gcp.txt`              | `pdfminer.six==20260107`, `google-cloud-vision==3.8.1`, `google-cloud-aiplatform==1.77.0` 追加                                                                                                                                                                                     |
| `services/api/requirements-azure.txt`            | `pdfminer.six==20260107` 追加                                                                                                                                                                                                                                                      |
| `services/api/requirements-layer.txt`            | `pdfminer.six==20260107` 追加                                                                                                                                                                                                                                                      |

---

## 9. GCP 稼働までに解決した問題

| 問題                                                | 原因                                                     | 対処                                                                   |
| --------------------------------------------------- | -------------------------------------------------------- | ---------------------------------------------------------------------- |
| HTTP 404                                            | GCP Cloud Run は `/v1/solve`（Azure は `/api/v1/solve`） | パスを修正                                                             |
| HTTP 503 `SOLVE_ENABLED=false`                      | env var 未設定がデフォルト false                         | `gcloud run services update --update-env-vars SOLVE_ENABLED=true`      |
| HTTP 502 `parents[4] IndexError`                    | Cloud Run デプロイパスが浅く `parents[4]` が範囲外       | `try/except IndexError` で None を返すよう修正                         |
| HTTP 502 `ModuleNotFoundError: google-cloud-vision` | `requirements-gcp.txt` に未記載                          | `google-cloud-vision==3.8.1`, `google-cloud-aiplatform==1.77.0` を追加 |
| HTTP 404 Vertex AI モデルなし                       | `gemini-2.0-flash-001` は `asia-northeast1` 未対応       | モデル名 `gemini-2.0-flash`・ロケーション `us-central1` に変更         |
| Vertex AI API 無効                                  | プロジェクト `ashnova` で API が未有効                   | `gcloud services enable aiplatform.googleapis.com`                     |

---

## 10. 今後の改善案

1. **`_has_formula_signal` の偽陽性減少**: `\quad` 単体などをブラックリスト化
2. **OCR 後処理の正規化**: `ェ` → `x` などの CJK-Latin 誤認識を修正
3. **GCP Document AI の活用**: `processors/math` で数式抽出をさらに高精度化
4. **`_normalize_pdf_math_text` の拡張**: `x 1\n2` → `x^{1/2}` 等のより複雑な縦組み数式への対応
5. **CI/CD 連携**: GCP デプロイ後の `SOLVE_ENABLED=true` を terraform/env ファイルで恒久化
