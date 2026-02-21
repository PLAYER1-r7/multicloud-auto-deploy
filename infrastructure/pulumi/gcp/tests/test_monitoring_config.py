"""
GCP Monitoring Configuration Unit Tests

このテストは monitoring.py の閾値計算ロジックを検証します。

背景 (Bug History):
    Feb 18, 2026 — production でメモリアラートが誤検知。
    原因: threshold_value=0.9 (バイト) と設定されており、
          実際のメモリ使用量 (123,850,752 bytes = ~118MB) が
          常に 0.9 bytes を超えるため無限にアラートが発火。
    修正: commit 9429a67 で calculate_memory_threshold_bytes() を導入し、
          threshold_value を正しくバイト数 (例: 483,183,820 bytes for 512MB) に変更。

使い方:
    # GCP pulumi ディレクトリから実行
    cd infrastructure/pulumi/gcp
    python -m pytest tests/test_monitoring_config.py -v

    # プロジェクトルートから実行
    python -m pytest multicloud-auto-deploy/infrastructure/pulumi/gcp/tests/ -v
"""

import os
import sys
import types
import unittest
from unittest.mock import MagicMock


# =========================================================
# Pulumi / pulumi_gcp を mock してから monitoring.py をインポート
# (テスト環境では Pulumi SDK が不要なため)
# spec なしの MagicMock を使うことで任意の属性アクセス・呼び出しが全て通る
# =========================================================
class _ModuleMock(MagicMock):
    """sys.modules に登録できる MagicMock サブクラス"""
    pass


def _register_mock(name: str) -> MagicMock:
    mock = _ModuleMock()
    mock.__name__ = name
    mock.__path__ = []
    mock.__package__ = name
    sys.modules[name] = mock
    return mock


# 親モジュールを先に登録し、サブモジュールを親の属性にも設定
_pulumi = _register_mock("pulumi")
_pulumi_gcp = _register_mock("pulumi_gcp")
_pulumi_gcp.monitoring = _register_mock("pulumi_gcp.monitoring")
_pulumi_gcp.projects = _register_mock("pulumi_gcp.projects")
_pulumi_gcp.firebase = _register_mock("pulumi_gcp.firebase")
_pulumi_gcp.storage = _register_mock("pulumi_gcp.storage")
_pulumi_gcp.compute = _register_mock("pulumi_gcp.compute")
_pulumi_gcp.secretmanager = _register_mock("pulumi_gcp.secretmanager")
_pulumi_gcp.serviceaccount = _register_mock("pulumi_gcp.serviceaccount")
_pulumi_gcp.billing = _register_mock("pulumi_gcp.billing")
_pulumi_gcp.cloudrunv2 = _register_mock("pulumi_gcp.cloudrunv2")

# パスを通す (monitoring.py が infrastructure/pulumi/gcp/ にある)
_GCP_DIR = os.path.join(os.path.dirname(__file__), "..")
if _GCP_DIR not in sys.path:
    sys.path.insert(0, _GCP_DIR)

from monitoring import calculate_memory_threshold_bytes  # noqa: E402


class TestCalculateMemoryThresholdBytes(unittest.TestCase):
    """
    calculate_memory_threshold_bytes() のユニットテスト

    --- リグレッションテストの目的 ---
    「threshold_value=0.9 バグ」が再発しないことを保証する。
    関数が返す値が必ず 1MB (1,048,576 bytes) を超えていれば、
    比率(0.9)を誤って渡した場合は即座に検出できる。
    """

    # テスト対象のメモリサイズ (Cloud Functions Gen2 で選択可能な値)
    VALID_MEMORY_SIZES_MB = [128, 256, 512, 1024, 2048, 4096, 8192]

    # ---- 基本的な正確性 ------------------------------------------------

    def test_512mb_returns_correct_bytes(self):
        """512MB の90%が正しくバイトで返ること (production 設定値)"""
        result = calculate_memory_threshold_bytes(512)
        expected = 483_183_820  # int(512 * 1024 * 1024 * 0.9)
        self.assertEqual(result, expected)

    def test_256mb_returns_correct_bytes(self):
        """256MB の90%が正しくバイトで返ること"""
        result = calculate_memory_threshold_bytes(256)
        expected = int(256 * 1024 * 1024 * 0.9)
        self.assertEqual(result, expected)

    def test_1024mb_returns_correct_bytes(self):
        """1024MB の90%が正しくバイトで返ること"""
        result = calculate_memory_threshold_bytes(1024)
        expected = int(1024 * 1024 * 1024 * 0.9)
        self.assertEqual(result, expected)

    # ---- リグレッション: 0.9バイトバグ防止 --------------------------------

    def test_threshold_is_never_less_than_1mb(self):
        """
        [REGRESSION TEST] 閾値は必ず 1MB (1,048,576 bytes) を超えること。

        このテストが失敗する場合、threshold_value に比率(0.9等)を
        バイト数として渡している可能性がある。
        Background: Feb 18, 2026 の誤検知アラートの根本原因。
        """
        min_bytes = 1_048_576  # 1MB
        for memory_mb in self.VALID_MEMORY_SIZES_MB:
            threshold = calculate_memory_threshold_bytes(memory_mb)
            self.assertGreater(
                threshold,
                min_bytes,
                msg=(
                    f"{memory_mb}MB の閾値 {threshold} bytes が 1MB 未満です。"
                    f" threshold_value に比率(0.9)を渡していないか確認してください。"
                    f" (Bug history: Feb 18, 2026 の誤検知アラート参照)"
                ),
            )

    def test_ratio_value_would_fail_this_check(self):
        """
        [DOCUMENTATION TEST] 旧バグの値 0.9 がどれほど小さいかを示す。
        0.9 bytes は 1MB より遥かに小さいため、上記テストが確実に検出できる。
        """
        buggy_value = 0.9  # 旧コードの誤った threshold_value
        self.assertLess(
            buggy_value,
            1_048_576,
            msg="0.9 bytes は 1MB 未満であることを確認 (リグレッション文書化)",
        )

    # ---- 戻り値の型 ------------------------------------------------

    def test_returns_int(self):
        """戻り値が int 型であること (float だと Pulumi SDK がエラーになる場合がある)"""
        result = calculate_memory_threshold_bytes(512)
        self.assertIsInstance(result, int)

    # ---- 比例関係 ------------------------------------------------

    def test_threshold_proportional_to_memory(self):
        """メモリが2倍になれば閾値もほぼ2倍になること (整数切り捨ての誤差1byte以内)"""
        threshold_512 = calculate_memory_threshold_bytes(512)
        threshold_1024 = calculate_memory_threshold_bytes(1024)
        # int() の切り捨てにより最大1バイトの誤差が生じる可能性がある
        diff = abs(threshold_1024 - threshold_512 * 2)
        self.assertLessEqual(diff, 1, msg="2倍のメモリに対する閾値は2倍±1バイト以内であるべき")

    def test_threshold_is_90_percent_of_allocated(self):
        """閾値が割当メモリの90%であること"""
        for memory_mb in self.VALID_MEMORY_SIZES_MB:
            threshold = calculate_memory_threshold_bytes(memory_mb)
            allocated_bytes = memory_mb * 1024 * 1024
            ratio = threshold / allocated_bytes
            self.assertAlmostEqual(
                ratio,
                0.9,
                places=5,
                msg=f"{memory_mb}MB の閾値比率が 0.9 でありません: {ratio}",
            )


class TestMemoryThresholdValues(unittest.TestCase):
    """既知の memory サイズに対する閾値の期待値テーブルを検証"""

    EXPECTED = {
        # (memory_mb, expected_threshold_bytes)
        128: int(128 * 1024 * 1024 * 0.9),    # 120,795,955
        256: int(256 * 1024 * 1024 * 0.9),    # 241,591,910
        512: int(512 * 1024 * 1024 * 0.9),    # 483_183_820
        1024: int(1024 * 1024 * 1024 * 0.9),  # 966_367_641
        2048: int(2048 * 1024 * 1024 * 0.9),  # 1_932_735_283
    }

    def test_expected_values(self):
        for memory_mb, expected in self.EXPECTED.items():
            with self.subTest(memory_mb=memory_mb):
                result = calculate_memory_threshold_bytes(memory_mb)
                self.assertEqual(result, expected,
                                 msg=f"{memory_mb}MB の閾値が想定値と異なります")


if __name__ == "__main__":
    unittest.main()
