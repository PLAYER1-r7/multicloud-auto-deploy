#!/usr/bin/env bash
# install.sh — Multi-Cloud Cost Monitor を xbar にインストールする
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_FILE="${SCRIPT_DIR}/cost-monitor.1h.py"
ENV_SAMPLE="${SCRIPT_DIR}/cost-monitor.env.sample"
ENV_FILE="${SCRIPT_DIR}/.env"
XBAR_PLUGINS_DIR="${HOME}/Library/Application Support/xbar/plugins"

echo "═══════════════════════════════════════════════════════"
echo "  Multi-Cloud Cost Monitor — xbar インストーラー"
echo "═══════════════════════════════════════════════════════"
echo ""

# ── xbar インストール確認 ─────────────────────────────────────
if ! command -v xbar &>/dev/null && [[ ! -d "/Applications/xbar.app" ]]; then
    echo "⚠️  xbar が見つかりません。先にインストールしてください:"
    echo "   https://xbarapp.com  または  brew install --cask xbar"
    echo ""
    echo "   インストール後、もう一度このスクリプトを実行してください。"
    exit 1
fi
echo "✅ xbar 検出済み"

# ── plugins フォルダ作成 ──────────────────────────────────────
mkdir -p "${XBAR_PLUGINS_DIR}"
echo "✅ plugins フォルダ: ${XBAR_PLUGINS_DIR}"

# ── シンボリックリンク作成 ────────────────────────────────────
LINK_PATH="${XBAR_PLUGINS_DIR}/cost-monitor.1h.py"
if [[ -L "${LINK_PATH}" ]]; then
    echo "ℹ️  既存のシンボリックリンクを更新します"
    rm "${LINK_PATH}"
fi
ln -s "${PLUGIN_FILE}" "${LINK_PATH}"
chmod +x "${PLUGIN_FILE}"
echo "✅ リンク作成: ${LINK_PATH} → ${PLUGIN_FILE}"

# ── .env セットアップ ─────────────────────────────────────────
if [[ ! -f "${ENV_FILE}" ]]; then
    cp "${ENV_SAMPLE}" "${ENV_FILE}"
    echo ""
    echo "📝 .env ファイルを作成しました:"
    echo "   ${ENV_FILE}"
    echo ""
    echo "   以下の値を設定してください:"
    echo "   - AZURE_SUBSCRIPTION_ID"
    echo "   - GCP_BILLING_ACCOUNT"
    echo "   - GITHUB_TOKEN (read:org スコープ)"
    echo "   - GH_ORG または GH_REPO"
else
    echo "✅ .env は既に存在します (上書きしません)"
fi

# ── Python 依存パッケージ ─────────────────────────────────────
echo ""
echo "📦 依存パッケージの確認..."
if ! /usr/bin/env python3 -c "import boto3" 2>/dev/null; then
    echo ""
    echo "   boto3 がインストールされていません。インストールしますか？ [y/N]"
    read -r answer
    if [[ "$(echo "$answer" | tr '[:upper:]' '[:lower:]')" == "y" ]]; then
        pip3 install --user boto3 --quiet
        echo "✅ boto3 をインストールしました"
    else
        echo "⚠️  boto3 なしでも動作しますが、AWS コストは取得できません"
    fi
else
    echo "✅ boto3 インストール済み"
fi

# ── xbar リフレッシュ ─────────────────────────────────────────
echo ""
echo "🔄 xbar をリフレッシュ中..."
if open -a xbar 2>/dev/null; then
    sleep 1
    # xbar のメニューバーアイコンをリフレッシュ (osascript でメニューを操作)
    osascript -e 'tell application "xbar" to reloadAll' 2>/dev/null || true
    echo "✅ xbar が起動しました"
else
    echo "ℹ️  xbar を手動で起動してください (Applications > xbar)"
fi

echo ""
echo "═══════════════════════════════════════════════════════"
echo "  インストール完了！"
echo ""
echo "  メニューバーに「☁ \$X.XX」が表示されます。"
echo "  表示されない場合: xbar > Preferences > Refresh All"
echo ""
echo "  .env を編集して認証情報を設定してください:"
echo "  open -e \"${ENV_FILE}\""
echo "═══════════════════════════════════════════════════════"
