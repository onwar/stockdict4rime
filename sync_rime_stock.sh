#!/bin/bash
# sync_rime_stock.sh
# 从 GitHub 拉取最新 A 股词库，部署到雾凇拼音并重新部署 RIME
#
# 使用前请修改下方两个变量：
#   REPO_DIR  ：本地 git 仓库路径
#   RIME_DIR  ：鼠须管用户数据目录（通常无需修改）

set -euo pipefail

# ─── 配置区（请按实际情况修改） ───────────────────────────────
REPO_DIR="$HOME/rime-a-stock"                         # 本地仓库目录
RIME_DIR="$HOME/Library/Rime"                         # 鼠须管用户数据目录
DICT_SRC="$REPO_DIR/dict/a_stock.dict.yaml"           # 仓库中的词库文件
DICT_DST="$RIME_DIR/cn_dicts/a_stock.dict.yaml"       # 部署目标路径
LOG_FILE="$HOME/.rime_stock_sync.log"                 # 日志文件
# ──────────────────────────────────────────────────────────────

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "===== 开始同步 A 股词库 ====="

# 1. 首次运行：若仓库不存在则 clone
# 请将下方 URL 替换为你自己的仓库地址
REPO_URL="https://github.com/YOUR_USERNAME/rime-a-stock.git"

if [ ! -d "$REPO_DIR/.git" ]; then
    log "本地仓库不存在，正在 clone..."
    git clone "$REPO_URL" "$REPO_DIR"
else
    log "拉取最新词库..."
    git -C "$REPO_DIR" pull --ff-only 2>&1 | tee -a "$LOG_FILE"
fi

# 2. 检查源文件是否存在
if [ ! -f "$DICT_SRC" ]; then
    log "错误：词库文件不存在 $DICT_SRC，退出"
    exit 1
fi

# 3. 对比文件，若无变化则跳过部署
if [ -f "$DICT_DST" ] && diff -q "$DICT_SRC" "$DICT_DST" > /dev/null 2>&1; then
    log "词库无变化，跳过部署"
    exit 0
fi

# 4. 复制词库到 cn_dicts 目录
mkdir -p "$RIME_DIR/cn_dicts"
cp "$DICT_SRC" "$DICT_DST"
log "词库已更新：$DICT_DST"

# 5. 触发鼠须管重新部署
/Library/Input Methods/Squirrel.app/Contents/MacOS/Squirrel --reload 2>&1 | tee -a "$LOG_FILE" || true
log "鼠须管重新部署完成"

log "===== 同步完成 ====="
