# stockdict4rime

自动采集沪深 A 股股票名称，生成供 [雾凇拼音 rime-ice](https://github.com/iDvel/rime-ice) 使用的词库，并通过 launchd 自动同步到 macOS 鼠须管输入法。

## 工作流程

```
GitHub Actions（每周一）
  └─ 运行 scripts/generate_dict.py
      └─ 采集沪深 A 股名称（akshare）
          └─ 生成 dict/a_stock.dict.yaml
              └─ 自动 commit & push

Mac launchd（每天 09:00）
  └─ 运行 sync_rime_stock.sh
      └─ git pull 最新词库
          └─ 复制到 ~/Library/Rime/cn_dicts/
              └─ 触发鼠须管重新部署
```

## 使用方法

### 一、Fork 或 Use this template 建立你自己的仓库

### 二、配置雾凇拼音挂载词库

在 `~/Library/Rime/rime_ice.dict.yaml` 的 `import_tables` 中添加一行：

```yaml
import_tables:
  - cn_dicts/a_stock   # ← 添加这一行
  # ... 其他词库
```

### 三、Mac 端首次设置

```bash
# 1. clone 你自己的仓库
git clone https://github.com/YOUR_USERNAME/rime-a-stock.git ~/rime-a-stock

# 2. 给脚本添加执行权限
chmod +x ~/rime-a-stock/sync_rime_stock.sh

# 3. 编辑脚本，修改 REPO_URL 为你自己的仓库地址
#    （文件顶部配置区）

# 4. 手动运行一次，验证同步正常
~/rime-a-stock/sync_rime_stock.sh

# 5. 安装 launchd 定时任务
#    先编辑 plist，将 YOUR_USERNAME 替换为你的用户名
cp ~/rime-a-stock/com.user.rime-stock-sync.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.user.rime-stock-sync.plist
```

### 四、验证 launchd 已加载

```bash
launchctl list | grep rime-stock
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `.github/workflows/update_dict.yml` | GitHub Actions 定时工作流 |
| `scripts/generate_dict.py` | 采集股票数据、生成词库的 Python 脚本 |
| `dict/a_stock.dict.yaml` | 生成的词库文件（自动更新） |
| `sync_rime_stock.sh` | Mac 端同步 + 部署脚本 |
| `com.user.rime-stock-sync.plist` | launchd 定时任务配置 |

## 日志查看

```bash
# 同步日志
cat ~/.rime_stock_sync.log

# launchd 输出
cat /tmp/rime-stock-sync.log
cat /tmp/rime-stock-sync.err
```
