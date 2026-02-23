# zhi — 终端里的 AI 助手

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Tests: passing](https://img.shields.io/badge/tests-333%20passing-brightgreen)

> 一个开源的 Python 命令行工具，由智谱 GLM 大模型驱动。安装即用，让 AI 在终端中帮你处理文件、识别图片、执行任务。

## 为什么选择 zhi？ / Why zhi?

你不需要 ChatGPT 的月费来总结一个文档。你也不需要 OpenClaw 那样连接邮箱、日历、智能家居的全能助手。

**zhi 只做一件事：让 AI 在你的终端里处理文件任务。**

| | ChatGPT | OpenClaw | **zhi** |
|---|---|---|---|
| 安装方式 | 注册账号、打开浏览器 | Node ≥22 + 后台守护进程 + 消息平台授权 | **`pip install zhicli`** |
| 上手时间 | 即时 | 10-30 分钟 | **2 分钟**（安装 + API 密钥） |
| 读取本地文件 | 需手动上传 | 需配置权限 | **直接读取当前目录** |
| 运行成本 | $20/月订阅 | 按 API 用量计费 | **按用量付费，技能执行成本 <10%** |
| 权限范围 | 云端，文件上传到第三方 | 邮箱、日历、消息平台、智能家居 | **仅限当前目录和 `zhi-output/`** |
| 运行方式 | 浏览器 | 24/7 后台守护进程 | **用完即走，不占资源** |
| 自动化 | 不支持 | 支持 | **支持（管道、脚本、技能）** |

**核心理念**：

- **两分钟上手** — `pip install zhicli` → `zhi --setup` → 开始用。没有守护进程，没有平台授权，没有账号注册。
- **文件留在本地** — 你的文件不会上传到任何地方。AI 直接读取你磁盘上的文件，输出写在你能看到的 `zhi-output/` 目录。
- **做好简单的事** — 总结文档、翻译文件、识别图片文字、生成测试数据。这些重复性任务是 AI 最擅长的，也是 zhi 专注的。
- **安全是默认的** — 不能删除文件、不能修改原文件、Shell 命令每次都要确认。不需要信任它，因为它做不了危险的事。

## 项目简介

`zhi` 是一个终端 AI 助手，采用**双模型架构**平衡智能与成本：

- **交互对话**使用 GLM-5 — 擅长复杂推理、技能创建和开放式对话
- **技能执行**使用 GLM-4-flash — 运行预定义工作流，成本不到 GLM-5 的 10%

核心能力：

- 读取文件、OCR 识别图片/PDF、抓取网页内容
- 将结果写入 Markdown、CSV、Excel、Word 等格式
- 通过 YAML 自定义可复用的 AI 技能（Skill）
- 严格的文件安全机制 — 不删除、不修改原始文件

## 安装

```bash
pip install zhicli
```

如需 Excel (.xlsx) 和 Word (.docx) 支持：

```bash
pip install "zhicli[all]"
```

要求 Python 3.10 或更高版本。

## 快速入门

**1. 配置 API 密钥**

```bash
# 运行设置向导（推荐）
zhi --setup

# 或直接设置环境变量
export ZHI_API_KEY=sk-...
```

API 密钥从[智谱开放平台](https://open.bigmodel.cn)获取。

**2. 开始对话**

```bash
$ zhi
Welcome to zhi. Type /help for commands.

You [approve]: 帮我总结 report.pdf 的要点
zhi: [OCR 识别 report.pdf...]
zhi: 以下是报告的核心要点...
```

**3. 单次提问（不进入交互模式）**

```bash
zhi -c "什么是机器学习？"
```

**4. 运行内置技能**

```bash
zhi run summarize 会议记录.txt       # 总结文档
zhi run translate readme-en.md       # 翻译为中文
```

**5. 管道输入**

```bash
git log --oneline -20 | zhi -c "总结本周的工作内容"
```

完整教程请查看 [docs/tutorials-cn.md](docs/tutorials-cn.md)。

## 使用场景

以下是几个典型场景，更多示例请查看 [docs/use-cases-cn.md](docs/use-cases-cn.md)。

### 总结会议纪要

```bash
zhi run summarize 产品评审会议记录.txt
# → 输出结构化摘要到 zhi-output/
```

### 对比文档差异

```bash
zhi run compare 合同-v1.md 合同-v2.md
# → 高亮两个版本之间的修改内容，输出对比报告
```

### OCR 识别图片/PDF

```bash
zhi -c "识别 合同扫描件.pdf 中的文字，保存为文本文件"
# → 支持 PDF、PNG、JPG、GIF、WEBP，最大 20MB
```

### 从报表提取关键数据

```bash
zhi -c "读取 季度财务报表.pdf，提取关键财务指标，整理成表格保存"
# → OCR 识别 PDF 内容，提取收入、利润等关键数据
```

### 翻译文档

```bash
zhi run translate api-specification.md
# → 保留 Markdown 格式的完整中文翻译
```

### 自定义技能一键复用

```bash
zhi run monthly-report 销售数据.csv
# → 用 glm-4-flash 执行，成本仅为对话的 10%
```

### 组合技能：一键完成复杂工作流

组合技能将多个基础技能串联成完整的工作流。一条命令，AI 自动完成多个步骤。

**会后一条龙** — 会议记录 → 结构化纪要 → 领导摘要 → 英文版：

```bash
zhi run meeting-followup 周一产品会议.txt --translate_to english
# → 输出 3 个文件：完整纪要、executive summary、英文翻译
```

**合同审查** — 分析 + 新旧版对比 + 校对，一步到位：

```bash
zhi run contract-review 合同-v2.pdf 合同-v1.pdf
# → 结构分析、变更清单、语言问题、风险评估，一份报告全搞定
```

**发票批量入表** — 扫描件 → 提取表格 → 汇总 Excel：

```bash
zhi run invoice-to-excel 发票扫描件/
# → 从所有 PDF 提取行项目，合并为一张 Excel 表
```

## 教程

详细的分步教程请查看 **[docs/tutorials-cn.md](docs/tutorials-cn.md)**，涵盖：

| 教程 | 内容 |
|------|------|
| 快速入门 | 安装、配置、第一次对话 |
| 交互式对话 | 斜杠命令、模式切换、多行输入 |
| 文件处理 | 读取、写入、OCR 识别 |
| 技能系统 | 内置技能、自定义技能、YAML 配置 |
| Shell 命令 | 安全执行、确认机制、超时控制 |
| Web 内容获取 | 抓取网页、提取分析 |

## CLI 用法

```
zhi                          # 交互式 REPL
zhi -c "your message"        # 单次对话模式
zhi run <skill> [files...]   # 运行技能
zhi --setup                  # 设置向导
zhi --version                # 查看版本
zhi --debug                  # 启用调试日志
zhi --no-color               # 禁用彩色输出
```

## 斜杠命令

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助信息 |
| `/auto` | 切换到自动模式（安全工具不再弹出确认） |
| `/approve` | 切换到审批模式（默认，风险操作需确认） |
| `/model <name>` | 切换模型（glm-5, glm-4-flash, glm-4-air） |
| `/think` | 启用思考模式（仅 glm-5） |
| `/fast` | 关闭思考模式 |
| `/run <skill> [args]` | 运行技能 |
| `/skill list` | 列出已安装技能 |
| `/skill new` | 创建新技能 |
| `/skill show <name>` | 查看技能详情 |
| `/skill edit <name>` | 编辑技能 |
| `/skill delete <name>` | 删除技能（仅删除 YAML 文件） |
| `/reset` | 清空对话历史 |
| `/undo` | 撤销上一轮对话 |
| `/usage` | 查看 Token 用量和费用 |
| `/verbose` | 切换详细输出 |
| `/exit` | 退出 |

## 内置工具

| 工具 | 说明 | 风险 |
|------|------|------|
| `file_read` | 读取工作目录内的文本文件（最大 100KB） | 否 |
| `file_write` | 写入新文件到 `zhi-output/`（.md, .txt, .json, .csv, .xlsx, .docx） | 是 |
| `file_list` | 列出目录内容（文件名、大小、修改时间） | 否 |
| `ocr` | 图片/PDF 文字识别（PNG, JPG, PDF, GIF, WEBP；最大 20MB） | 否 |
| `shell` | 执行 Shell 命令（始终需要确认） | 是 |
| `web_fetch` | 获取并提取网页文本内容 | 否 |
| `skill_create` | 创建新的技能 YAML 配置 | 是 |

风险工具在审批模式下需要用户确认后才能执行。

## 技能系统

技能（Skill）是可复用的 AI 工作流，以 YAML 文件定义。默认使用 `glm-4-flash` 模型，成本低廉。

**基础技能**（9 个）：

| 技能 | 说明 | 用法示例 |
|------|------|----------|
| `summarize` | 总结文档要点 | `zhi run summarize report.pdf` |
| `translate` | 翻译文本（默认中文） | `zhi run translate readme-en.md` |
| `extract-text` | OCR 提取 PDF/图片中的文字 | `zhi run extract-text scan.pdf` |
| `extract-table` | 从文档中提取表格为 CSV | `zhi run extract-table invoice.pdf` |
| `analyze` | 深度分析文档内容和结构 | `zhi run analyze contract.pdf` |
| `proofread` | 校对文档，标注语法和拼写错误 | `zhi run proofread draft.md` |
| `reformat` | 格式转换（文本↔Markdown↔CSV↔Excel） | `zhi run reformat data.csv` |
| `meeting-notes` | 会议记录整理为结构化纪要和行动项 | `zhi run meeting-notes notes.txt` |
| `compare` | 对比两个文件，高亮差异 | `zhi run compare v1.md v2.md` |

**组合技能**（6 个）— 串联多个基础技能，一条命令完成完整工作流：

| 技能 | 组合了 | 说明 |
|------|--------|------|
| `daily-digest` | summarize | 扫描文件夹，汇总所有文档为一份日报 |
| `translate-proofread` | translate → proofread | 翻译文档并校对翻译质量 |
| `meeting-followup` | meeting-notes → summarize → translate | 会议记录 → 纪要 + 摘要 + 翻译 |
| `contract-review` | analyze + compare + proofread | 合同分析、版本对比、语言校对一步到位 |
| `invoice-to-excel` | extract-table → reformat | 发票扫描件批量提取为 Excel |
| `report-polish` | proofread → analyze → reformat | 校对 + 结构优化 + 格式整理 |

**基础技能 YAML 示例**：

```yaml
name: summarize
description: Summarize a text file or document
model: glm-4-flash
system_prompt: |
  You are a concise summarization assistant. Read the provided text
  and produce a clear, well-structured summary.
tools:
  - file_read
  - file_write
max_turns: 5
input:
  description: A text file to summarize
  args:
    - name: file
      type: file
      required: true
output:
  description: Markdown summary
  directory: zhi-output
```

**组合技能 YAML 示例** — 在 `tools` 中引用其他技能，AI 会自动编排调用：

```yaml
name: translate-proofread
description: Translate a document and then proofread the translation
model: glm-4-flash
system_prompt: |
  Workflow:
  1. Call skill_translate to translate the document.
  2. Call skill_proofread on the translation to check quality.
  3. Produce a polished final translation and a quality report.
tools:
  - file_read
  - file_write
  - translate      # ← 引用 translate 技能
  - proofread      # ← 引用 proofread 技能
max_turns: 12
input:
  description: A document to translate and proofread
  args:
    - name: file
      type: file
      required: true
output:
  description: Polished translation and quality report
  directory: zhi-output
```

使用 `/skill new` 交互式创建技能，或手动编写 YAML 文件。技能存储在系统配置目录的 `skills/` 下。

## 文件安全

`zhi` 执行严格的安全约束：

- **禁止删除文件** — 没有删除工具
- **禁止修改文件** — `file_write` 只创建新文件，不能覆盖
- **输出目录隔离** — 所有写入限定在 `./zhi-output/`，拒绝路径穿越（`..`）
- **Shell 始终确认** — 每条 Shell 命令都需要 `y/n` 确认，即使在 auto 模式下
- **危险命令警告** — `rm`、`mv`、`del` 等命令触发额外警告
- **灾难性命令拦截** — `rm -rf /` 等模式被永久禁止

## 配置

配置文件存储在系统配置目录中：

- **macOS**: `~/Library/Application Support/zhi/config.yaml`
- **Windows**: `%APPDATA%\zhi\config.yaml`
- **Linux**: `~/.config/zhi/config.yaml`

环境变量优先级高于配置文件：

| 环境变量 | 说明 | 默认值 |
|----------|------|--------|
| `ZHI_API_KEY` | 智谱 API 密钥（必需） | — |
| `ZHI_DEFAULT_MODEL` | 默认对话模型 | `glm-5` |
| `ZHI_OUTPUT_DIR` | 文件输出目录 | `zhi-output` |
| `ZHI_LOG_LEVEL` | 日志级别 | `INFO` |
| `NO_COLOR` | 禁用彩色输出（任意值） | — |

## Development

```bash
git clone https://github.com/chan-kinghin/zhicli.git
cd zhicli
pip install -e ".[dev,all]"

# Run tests
pytest tests/ -v

# Lint and format
ruff check src/zhi/
ruff format src/zhi/

# Type check
mypy --strict src/zhi/

# Coverage
pytest --cov=zhi --cov-report=term-missing
```

## 声明 / Disclaimer

`zhi` 是一个独立的社区开源项目，与智谱 AI（Zhipu AI）没有任何隶属或认可关系。

`zhi` is an independent, community-built project. It is not affiliated with or endorsed by Zhipu AI.

## 许可证 / License

MIT
