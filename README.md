# zhi - 终端 AI 助手 | Terminal AI Assistant

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Tests: 684 passing](https://img.shields.io/badge/tests-684%20passing-brightgreen)

[English](#english) | [Documentation](https://chan-kinghin.github.io/zhicli/)

---

**由智谱 GLM 大模型驱动的智能终端助手**

- **双模型架构** -- 对话用 GLM-5，技能执行用 GLM-4-flash（成本仅 ~10%）
- **15 个内置技能** -- 从文档总结到合同审查，YAML 定义，可自由扩展
- **安全文件处理** -- 输出隔离、路径保护、Shell 确认，不删除不覆盖

```bash
pip install zhicli
zhi --setup
zhi
```

## 架构

```
┌─────────────────────────────────────────┐
│              zhi CLI                    │
├──────────────┬──────────────────────────┤
│  交互对话     │      技能执行            │
│  GLM-5       │      GLM-4-flash         │
│  (智能对话)   │      (成本仅 ~10%)       │
├──────────────┴──────────────────────────┤
│           工具层 (8 个工具)              │
│  file_read · file_write · file_list     │
│  ocr · shell · web_fetch · skill_create │
│  ask_user                               │
├─────────────────────────────────────────┤
│           安全层                         │
│  输出隔离 · 路径保护 · Shell 确认        │
└─────────────────────────────────────────┘
```

## 横向对比

| 特性 | zhi | aider | Claude Code | GitHub Copilot CLI | Gemini CLI | shell-gpt | Qwen Code |
|------|-----|-------|-------------|-------------------|------------|-----------|-----------|
| 安装方式 | pip install | pip install | npm | brew | npm | pip | pip |
| 配置复杂度 | 1 key (30秒) | API key + git | API key | GitHub login + VS Code | Google auth | API key | API key |
| 中文大模型 | ✅ 原生 | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| 文件处理 | 读取+写入+OCR | 读取+编辑 | 读取+编辑 | ❌ | 读取+编辑 | ❌ | 读取+编辑 |
| 技能系统 | ✅ YAML (15个内置) | ❌ | ❌ slash commands | ❌ | ❌ | ❌ | ❌ |
| 成本控制 | 双模型 (技能用 flash) | 单模型 | 单模型 | 订阅制 | 免费额度 | 单模型 | 免费 |
| 权限控制 | approve/auto 模式 | auto | auto with approval | N/A | auto | auto | auto |
| 输出安全 | 隔离目录 | 直接编辑 | 直接编辑 | N/A | 直接编辑 | N/A | 直接编辑 |

## 功能概览

### 15 个内置技能

基础技能（9 个）:

| 技能 | 说明 | 用法 |
|------|------|------|
| `summarize` | 总结文档要点 | `zhi run summarize report.pdf` |
| `translate` | 翻译文本（默认中文） | `zhi run translate readme-en.md` |
| `extract-text` | OCR 提取 PDF/图片文字 | `zhi run extract-text scan.pdf` |
| `extract-table` | 从文档提取表格为 CSV | `zhi run extract-table invoice.pdf` |
| `analyze` | 深度分析文档内容和结构 | `zhi run analyze contract.pdf` |
| `proofread` | 校对语法和拼写 | `zhi run proofread draft.md` |
| `reformat` | 格式转换 (文本/Markdown/CSV/Excel) | `zhi run reformat data.csv` |
| `meeting-notes` | 会议记录整理为结构化纪要 | `zhi run meeting-notes notes.txt` |
| `compare` | 对比两个文件的差异 | `zhi run compare v1.md v2.md` |

组合技能（6 个）:

| 技能 | 说明 | 组合流程 |
|------|------|----------|
| `translate-proofread` | 翻译并校对质量 | translate -> proofread |
| `meeting-followup` | 会议纪要 + 摘要 + 翻译 | meeting-notes -> summarize -> translate |
| `invoice-to-excel` | 发票扫描转 Excel 汇总 | extract-table -> reformat |
| `daily-digest` | 文件夹文档批量摘要 | file_list -> summarize (loop) |
| `contract-review` | 合同分析 + 版本对比 + 校对 | analyze -> compare -> proofread |
| `report-polish` | 文档润色至可发布状态 | proofread -> analyze -> reformat |

### 8 个工具

| 工具 | 说明 | 风险 |
|------|------|------|
| `file_read` | 读取工作目录内的文本文件（最大 100KB） | 否 |
| `file_write` | 写入新文件到 `zhi-output/` | 是 |
| `file_list` | 列出目录内容 | 否 |
| `ocr` | 图片/PDF 文字识别（最大 20MB） | 否 |
| `shell` | 执行 Shell 命令（始终需确认） | 是 |
| `web_fetch` | 获取网页文本内容 | 否 |
| `skill_create` | 创建新的技能 YAML | 是 |
| `ask_user` | 执行中向用户提问 | 否 |

风险工具在审批模式下需要用户确认后才能执行。

### 斜杠命令

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助信息 |
| `/auto` | 切换到自动模式 |
| `/approve` | 切换到审批模式（默认） |
| `/model <name>` | 切换模型 |
| `/think` | 启用思考模式（仅 GLM-5） |
| `/fast` | 关闭思考模式 |
| `/run <skill> [args]` | 运行技能 |
| `/skill list\|new\|show\|edit\|delete` | 管理技能 |
| `/status` | 显示当前会话状态 |
| `/reset` | 清空对话历史 |
| `/undo` | 撤销上一轮对话 |
| `/usage` | 查看 Token 用量和费用 |
| `/verbose` | 切换详细输出 |
| `/exit` | 退出 |

### 文件安全

- **禁止删除** -- 没有删除工具
- **禁止覆盖** -- `file_write` 只创建新文件
- **输出隔离** -- 所有写入限定在 `./zhi-output/`，拒绝路径穿越
- **Shell 确认** -- 每条命令都需要 `y/n` 确认
- **危险命令警告** -- `rm`、`mv`、`del` 等命令触发额外警告
- **灾难性命令拦截** -- `rm -rf /` 等模式被永久禁止

### 配置

配置文件位置：

- macOS: `~/Library/Application Support/zhi/config.yaml`
- Windows: `%APPDATA%\zhi\config.yaml`
- Linux: `~/.config/zhi/config.yaml`

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `ZHI_API_KEY` | 智谱 API 密钥（必需） | -- |
| `ZHI_DEFAULT_MODEL` | 默认对话模型 | `glm-5` |
| `ZHI_OUTPUT_DIR` | 文件输出目录 | `zhi-output` |
| `ZHI_LANGUAGE` | 界面语言 (en/zh) | auto |
| `ZHI_LOG_LEVEL` | 日志级别 | `INFO` |
| `NO_COLOR` | 禁用彩色输出 | -- |

## 安装与快速入门

### macOS / Linux

需要 Python 3.10+。Requires Python 3.10+.

**macOS**: 推荐用 Homebrew 安装 / Install via Homebrew:

```bash
brew install python@3.11
```

**Linux (Ubuntu/Debian)**:

```bash
sudo apt install python3 python3-pip
```

然后安装 zhi / Then install zhi:

```bash
pip install zhicli          # 含 Excel/Word 支持
```

### Windows 安装

**方式一：直接下载（推荐）**

从 [GitHub Releases](https://github.com/chan-kinghin/zhicli/releases) 下载 `zhi-*-windows-x64.exe`，无需安装 Python。

```powershell
.\zhi.exe --setup
.\zhi.exe
```

**方式二：pip 安装**

需要先安装 [Python 3.10+](https://www.python.org/downloads/)（安装时勾选 "Add Python to PATH"）。

```powershell
pip install zhicli
zhi --setup
```

要求 Python 3.10+。API 密钥从[智谱开放平台](https://open.bigmodel.cn)获取。

```bash
zhi --setup                 # 运行设置向导
zhi                         # 进入交互模式
zhi -c "什么是机器学习？"     # 单次提问
zhi run summarize report.pdf # 运行技能
```

完整文档请查看 [Documentation](https://chan-kinghin.github.io/zhicli/)。

## 开发

```bash
git clone https://github.com/chan-kinghin/zhicli.git
cd zhicli
pip install -e ".[dev,all]"
pytest tests/ -v            # 测试
ruff check src/zhi/         # 检查
ruff format src/zhi/        # 格式化
```

## 链接

- 📖 Documentation: https://chan-kinghin.github.io/zhicli/
- 🐛 Issues: https://github.com/chan-kinghin/zhicli/issues
- 📄 License: MIT

---

<a id="english"></a>

# English

**Intelligent terminal assistant powered by Zhipu GLM models**

- **Dual-model architecture** -- GLM-5 for chat, GLM-4-flash for skills (~10% of the cost)
- **15 built-in skills** -- From document summarization to contract review, YAML-defined, extensible
- **Safe file handling** -- Output isolation, path protection, shell confirmation, no deletes or overwrites

```bash
pip install zhicli
zhi --setup
zhi
```

## Architecture

```
┌─────────────────────────────────────────┐
│              zhi CLI                    │
├──────────────┬──────────────────────────┤
│  Chat        │      Skill Execution     │
│  GLM-5       │      GLM-4-flash         │
│  (reasoning) │      (~10% cost)         │
├──────────────┴──────────────────────────┤
│           Tool Layer (8 tools)          │
│  file_read · file_write · file_list     │
│  ocr · shell · web_fetch · skill_create │
│  ask_user                               │
├─────────────────────────────────────────┤
│           Safety Layer                  │
│  Output isolation · Path guard · Shell  │
└─────────────────────────────────────────┘
```

## Comparison

| Feature | zhi | aider | Claude Code | GitHub Copilot CLI | Gemini CLI | shell-gpt | Qwen Code |
|---------|-----|-------|-------------|-------------------|------------|-----------|-----------|
| Install | pip install | pip install | npm | brew | npm | pip | pip |
| Setup | 1 key (30s) | API key + git | API key | GitHub + VS Code | Google auth | API key | API key |
| Chinese LLM | ✅ native | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| File handling | read+write+OCR | read+edit | read+edit | ❌ | read+edit | ❌ | read+edit |
| Skill system | ✅ YAML (15 built-in) | ❌ | ❌ slash commands | ❌ | ❌ | ❌ | ❌ |
| Cost control | dual-model (flash for skills) | single model | single model | subscription | free tier | single model | free |
| Permissions | approve/auto mode | auto | auto with approval | N/A | auto | auto | auto |
| Output safety | isolated directory | direct edit | direct edit | N/A | direct edit | N/A | direct edit |

## Built-in Skills

Basic skills (9):

| Skill | Description | Usage |
|-------|-------------|-------|
| `summarize` | Summarize document key points | `zhi run summarize report.pdf` |
| `translate` | Translate text (default: Chinese) | `zhi run translate readme-en.md` |
| `extract-text` | OCR text from PDF/images | `zhi run extract-text scan.pdf` |
| `extract-table` | Extract tables to CSV | `zhi run extract-table invoice.pdf` |
| `analyze` | Deep analysis of document structure | `zhi run analyze contract.pdf` |
| `proofread` | Check grammar and spelling | `zhi run proofread draft.md` |
| `reformat` | Convert between formats | `zhi run reformat data.csv` |
| `meeting-notes` | Structure meeting notes into minutes | `zhi run meeting-notes notes.txt` |
| `compare` | Compare two files and highlight diffs | `zhi run compare v1.md v2.md` |

Composite skills (6):

| Skill | Description | Pipeline |
|-------|-------------|----------|
| `translate-proofread` | Translate and QA the translation | translate -> proofread |
| `meeting-followup` | Minutes + summary + translation | meeting-notes -> summarize -> translate |
| `invoice-to-excel` | Scanned invoices to Excel | extract-table -> reformat |
| `daily-digest` | Batch summarize a folder | file_list -> summarize (loop) |
| `contract-review` | Analyze + compare + proofread contract | analyze -> compare -> proofread |
| `report-polish` | Polish a document for publication | proofread -> analyze -> reformat |

## Tools (8)

| Tool | Description | Risky |
|------|-------------|-------|
| `file_read` | Read text files in working directory (max 100KB) | No |
| `file_write` | Write new files to `zhi-output/` | Yes |
| `file_list` | List directory contents | No |
| `ocr` | Image/PDF text recognition (max 20MB) | No |
| `shell` | Execute shell commands (always requires confirmation) | Yes |
| `web_fetch` | Fetch and extract web page text | No |
| `skill_create` | Create new skill YAML configs | Yes |
| `ask_user` | Ask the user a question mid-execution | No |

## Safety

- **No deletions** -- no delete tool exists
- **No overwrites** -- `file_write` only creates new files
- **Output isolation** -- all writes restricted to `./zhi-output/`, path traversal rejected
- **Shell confirmation** -- every command requires `y/n` approval
- **Dangerous command warnings** -- `rm`, `mv`, `del` trigger extra warnings
- **Catastrophic command blocking** -- patterns like `rm -rf /` are permanently blocked

## Install and Quick Start

### macOS / Linux

Requires Python 3.10+.

**macOS**: Install via Homebrew (recommended):

```bash
brew install python@3.11
```

**Linux (Ubuntu/Debian)**:

```bash
sudo apt install python3 python3-pip
```

Then install zhi:

```bash
pip install zhicli          # includes Excel/Word support
```

### Windows Install

**Option 1: Download exe (recommended for most users)**

Download `zhi-*-windows-x64.exe` from [GitHub Releases](https://github.com/chan-kinghin/zhicli/releases). No Python required.

```powershell
.\zhi.exe --setup
.\zhi.exe
```

**Option 2: pip install**

Requires [Python 3.10+](https://www.python.org/downloads/) (check "Add Python to PATH" during install).

```powershell
pip install zhicli
zhi --setup
```

Requires Python 3.10+. Get an API key from [Zhipu Open Platform](https://open.bigmodel.cn).

```bash
zhi --setup                 # run setup wizard
zhi                         # interactive mode
zhi -c "What is ML?"        # single query
zhi run summarize report.pdf # run a skill
```

Full documentation at [chan-kinghin.github.io/zhicli](https://chan-kinghin.github.io/zhicli/).

## Development

```bash
git clone https://github.com/chan-kinghin/zhicli.git
cd zhicli
pip install -e ".[dev,all]"
pytest tests/ -v            # tests
ruff check src/zhi/         # lint
ruff format src/zhi/        # format
```

## Links

- 📖 Documentation: https://chan-kinghin.github.io/zhicli/
- 🐛 Issues: https://github.com/chan-kinghin/zhicli/issues
- 📄 License: MIT

---

`zhi` 是一个独立的社区开源项目，与智谱 AI（Zhipu AI）没有任何隶属或认可关系。

`zhi` is an independent, community-built project. It is not affiliated with or endorsed by Zhipu AI.
