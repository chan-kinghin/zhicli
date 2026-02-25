# zhi CLI 中文教程

> zhi 是一个开源的 Python 命令行工具，由智谱 GLM 大模型驱动。安装后即可在终端中获得一个智能助手，支持对话、文件处理、OCR 识别、自定义技能等功能。

---

---

## 5 分钟快速入门

从零开始安装 zhi，配置 API 密钥，完成第一次对话。

### 前提条件

- 智谱开放平台账号（用于获取 API 密钥）
- **Windows 用户**有两种安装方式：
    1. 从 [GitHub Releases](https://github.com/chan-kinghin/zhicli/releases) 下载 `zhi.exe`（推荐，无需安装 Python）—— exe 已内置 Python 运行环境
    2. 通过 pip 安装（需要 Python 3.10+）
- **macOS 用户**需要 Python 3.10+。macOS 自带的 Python 版本可能较旧，建议通过以下方式安装：
    - `brew install python@3.11`（推荐，需先安装 [Homebrew](https://brew.sh)）
    - 或从 [python.org](https://www.python.org/downloads/) 下载安装包
- **Linux 用户**需要 Python 3.10+。大多数发行版已自带，如未安装：
    - Ubuntu/Debian: `sudo apt install python3 python3-pip`
    - Fedora: `sudo dnf install python3 python3-pip`
    - Arch: `sudo pacman -S python python-pip`

### 第一步：安装 zhi

**Windows（exe 方式，推荐）：**

从 [GitHub Releases](https://github.com/chan-kinghin/zhicli/releases) 下载 `zhi.exe`，放到你喜欢的目录，然后运行：

```powershell
.\zhi.exe --setup
```

**Windows（pip 方式）/ macOS / Linux：**

```bash
pip install zhicli
```

验证安装成功：

```bash
zhi --version
```

### 第二步：配置

运行设置向导（推荐）：

```bash
zhi --setup
```

向导会引导你完成三个步骤：

```
Welcome to zhi (v0.1.0)

Let's get you set up. This takes about 30 seconds.

Step 1/3: API Key
  Paste your Zhipu API key (get one at open.bigmodel.cn):
  > 你的API密钥

Step 2/3: Defaults
  Default model for chat [glm-5]:
  Default model for skills [glm-4-flash]:
  Output directory [zhi-output]:

Step 3/3: Quick Demo
  Want to try a sample skill? [Y/n]:

Setup complete. Type /help to see available commands.
```

也可以通过环境变量配置：

```bash
# Linux / macOS
export ZHI_API_KEY="你的API密钥"

# Windows (PowerShell)
$env:ZHI_API_KEY = "你的API密钥"
```

### 第三步：开始使用

**交互模式** -- 启动 REPL：

```bash
zhi
```

**单次提问** -- 问一个问题后退出：

```bash
zhi -c "什么是机器学习？"
```

**运行技能** -- 用内置技能处理文件：

```bash
zhi run summarize document.txt
```

完成！你已经可以开始使用了。

---

## 交互式对话教程

### 进入交互模式

```bash
zhi
```

```
Welcome to zhi. Type /help for commands.
You [approve]:
```

提示符中的 `[approve]` 表示当前的权限模式。

### 查看帮助

```
You [approve]: /help
```

输出所有可用命令：

```
Available commands:
  /help              Show this help message
  /auto              Switch to auto mode (no permission prompts)
  /approve           Switch to approve mode (default)
  /model <name>      Switch model (glm-5, glm-4-flash, glm-4-air)
  /think             Enable thinking mode
  /fast              Disable thinking mode
  /run <skill> [args]  Run a skill
  /skill list|new|show|edit|delete  Manage skills
  /reset             Clear conversation history
  /undo              Remove last exchange
  /usage             Show token/cost stats
  /verbose           Toggle verbose output
  /exit              Exit zhi
```

### 权限模式切换

zhi 有两种权限模式：

- **approve 模式**（默认）：执行有风险的操作（如写文件、运行 Shell 命令）时需要你确认
- **auto 模式**：跳过确认提示，自动执行所有操作

```
You [approve]: /auto
Mode switched to auto

You [auto]: /approve
Mode switched to approve
```

!!! warning
    Shell 命令始终需要确认，即使在 auto 模式下也不例外。这是一项不可绕过的安全特性。

### 切换模型

zhi 支持三个模型：

| 模型 | 类型 | 特点 |
|------|------|------|
| `glm-5` | 高级 | 默认对话模型，智能但较贵 |
| `glm-4-flash` | 经济 | 技能执行模型，快速且便宜 |
| `glm-4-air` | 经济 | 轻量替代方案 |

查看和切换模型：

```
You [approve]: /model
Current model: glm-5. Available: glm-5, glm-4-flash, glm-4-air

You [approve]: /model glm-4-flash
Model switched to glm-4-flash
```

### 思考模式

启用思考模式后，模型会展示推理过程（仅 glm-5 支持）：

```
You [approve]: /think
Thinking mode enabled

You [approve]: 解释为什么天空是蓝色的

You [approve]: /fast
Thinking mode disabled
```

### 多行输入

在行末添加 `\` 可以输入多行内容：

```
You [approve]: 请帮我写一个 Python 函数，\
...  要求接受一个列表参数，\
...  返回列表中的最大值
```

### 管理对话历史

撤销上一轮对话：

```
You [approve]: /undo
Last exchange removed
```

清空所有对话历史：

```
You [approve]: /reset
Conversation cleared
```

### 查看用量统计

```
You [approve]: /usage
```

会显示当前会话的 token 用量和预估费用。

### 退出

```
You [approve]: /exit
Goodbye!
```

也可以按 `Ctrl+D` 退出，或按 `Ctrl+C` 取消当前输入。

!!! tip
    - 输入历史会自动保存，下次启动可以用上下方向键浏览历史记录
    - 包含敏感信息（如 api_key、password、token）的输入不会被保存到历史记录
    - Tab 键可以自动补全斜杠命令和模型名称
    - 切换模型只影响当前会话，不会修改配置文件

---

## 文件处理教程

### 读取文本文件

在对话中让 zhi 读取文件：

```
You [approve]: 请读取 README.md 文件并总结其内容
```

zhi 会调用 `file_read` 工具读取文件内容，然后生成总结。

`file_read` 工具的特点：

- 只允许读取当前工作目录内的文件（相对路径）
- 单个文件最大 100KB，超出部分会被截断
- 自动检测编码，优先使用 UTF-8
- 不能读取二进制文件

### 列出目录内容

```
You [approve]: 列出当前目录下的所有文件
```

zhi 会调用 `file_list` 工具展示文件列表，包含文件名、大小和修改时间。

### OCR 识别图片和 PDF

将图片或 PDF 中的文字提取出来：

```
You [approve]: 请识别 invoice.png 中的文字内容

You [approve]: 提取 report.pdf 中的文字并总结要点
```

`ocr` 工具支持的格式：

- 图片：PNG, JPG, JPEG, GIF, WEBP
- 文档：PDF
- 文件大小限制：20MB

### 写入新文件

zhi 的所有文件输出都保存在 `zhi-output/` 目录中：

```
You [approve]: 请把刚才的总结写成一个 Markdown 文件
```

zhi 会调用 `file_write` 工具，提示你确认后（approve 模式下）写入文件。

`file_write` 支持多种格式：

| 格式 | 扩展名 | 内容格式 |
|------|--------|----------|
| 纯文本 | `.md`, `.txt` | 直接文本 |
| JSON | `.json` | 任意 JSON |
| CSV | `.csv` | headers + rows |
| Excel | `.xlsx` | sheets 数据 |
| Word | `.docx` | Markdown 文本 |

示例对话：

```
You [approve]: 帮我创建一个 CSV 文件，包含以下三个人的信息：
张三, 25岁, 北京
李四, 30岁, 上海
王五, 28岁, 广州
```

zhi 会在 `zhi-output/` 下创建 CSV 文件。

### 组合使用：读取 + 处理 + 写入

```
You [approve]: 读取 data.csv 文件，分析数据趋势，然后把分析报告写成 report.md
```

zhi 会依次调用 file_read 读取数据、分析内容、然后调用 file_write 生成报告。

!!! info
    - `file_write` 只能创建新文件，不能覆盖已有文件
    - 所有输出文件都在 `zhi-output/` 目录下，不会影响你的原始文件
    - 路径不允许包含 `..`，防止写入工作目录以外的位置
    - Excel (.xlsx) 和 Word (.docx) 格式开箱即用，无需额外安装

---

## 技能系统教程

### 什么是技能？

技能（Skill）是一组预定义的 YAML 配置，指定了系统提示词、可用工具和模型。它让你可以将常用的工作流程保存下来，一键运行。技能默认使用 `glm-4-flash` 模型，成本不到 GLM-5 的 10%。

### 内置技能

zhi 自带 **15 个内置技能** -- 9 个单一用途技能和 6 个组合技能（将多个单一技能串联成多步工作流）。

#### 单一用途技能（9 个）

| 技能 | 功能 | 用法 |
|------|------|------|
| `summarize` | 文档总结 | `zhi run summarize report.txt` |
| `translate` | 翻译文档（默认翻译为中文） | `zhi run translate readme-en.md` |
| `extract-text` | 从 PDF/图片中 OCR 提取文字 | `zhi run extract-text scan.pdf` |
| `extract-table` | 从文档中提取表格数据 | `zhi run extract-table invoice.pdf` |
| `analyze` | 深度分析文档结构与内容 | `zhi run analyze proposal.md` |
| `proofread` | 语法、拼写、风格校对 | `zhi run proofread draft.md` |
| `reformat` | 文档格式转换 | `zhi run reformat notes.txt` |
| `meeting-notes` | 将原始笔记整理为会议纪要 | `zhi run meeting-notes notes.txt` |
| `compare` | 对比两份文档并标注差异 | `zhi run compare v1.md v2.md` |

#### 组合技能（6 个）

这些技能将多个单一技能串联成多步工作流。详见下方[组合技能](#composite-skills)章节。

| 技能 | 流程 | 用法 |
|------|------|------|
| `contract-review` | 分析 + 对比 + 校对 | `zhi run contract-review contract.pdf` |
| `daily-digest` | 目录扫描 + 批量总结 | `zhi run daily-digest ./reports/` |
| `invoice-to-excel` | 表格提取 + 格式转换 | `zhi run invoice-to-excel invoices/` |
| `meeting-followup` | 会议纪要 + 总结 + 翻译 | `zhi run meeting-followup notes.txt` |
| `report-polish` | 校对 + 分析 + 格式优化 | `zhi run report-polish draft.md` |
| `translate-proofread` | 翻译 + 校对 | `zhi run translate-proofread doc.md` |

### 查看已安装的技能

```
You [approve]: /skill list
```

### 运行技能

从命令行直接运行：

```bash
zhi run summarize report.txt
```

在交互模式中运行：

```
You [approve]: /run summarize report.txt
```

### 创建自定义技能

**方式一：在对话中让 zhi 创建**

```
You [approve]: 帮我创建一个代码审查技能，名叫 code-review，
能读取源代码文件并给出改进建议
```

zhi 会调用 `skill_create` 工具生成 YAML 配置文件。

**方式二：手动编写 YAML 文件**

在配置目录的 `skills/` 下创建 YAML 文件。以下是一个技能配置示例：

```yaml
name: code-review
description: Review source code and suggest improvements
model: glm-4-flash
system_prompt: |
  You are an experienced code reviewer. Read the provided source code
  and give actionable suggestions for improvement. Focus on:
  - Code quality and readability
  - Potential bugs
  - Performance issues
  Output your review as structured markdown.
tools:
  - file_read
  - file_write
max_turns: 10
input:
  description: Source code file to review
  args:
    - name: file
      type: file
      required: true
output:
  description: Code review report in markdown
  directory: zhi-output
```

### 技能 YAML 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | 是 | 技能名称，只能包含字母、数字、连字符和下划线，最长 64 字符 |
| `description` | 是 | 技能描述 |
| `system_prompt` | 是 | 系统提示词，指导模型行为 |
| `tools` | 是 | 允许使用的工具列表 |
| `model` | 否 | 使用的模型，默认 `glm-4-flash` |
| `max_turns` | 否 | 最大执行轮次，默认 15 |
| `input` | 否 | 输入参数定义 |
| `output` | 否 | 输出配置（描述和目录） |

### 可用工具列表

创建技能时可以选择以下工具：

| 工具名 | 功能 | 风险等级 |
|--------|------|----------|
| `file_read` | 读取文本文件 | 低 |
| `file_write` | 写入新文件到 zhi-output/ | 高 |
| `file_list` | 列出目录内容 | 低 |
| `ocr` | 图片/PDF 文字识别 | 低 |
| `shell` | 执行 Shell 命令 | 高 |
| `web_fetch` | 获取网页内容 | 低 |
| `skill_create` | 创建新技能 | 高 |

### 管理技能

```
You [approve]: /skill show code-review   # 查看技能详情
You [approve]: /skill delete code-review # 删除自定义技能
```

!!! info
    - 技能名称必须匹配 `^[a-zA-Z0-9][a-zA-Z0-9_-]*$`，不允许包含空格或特殊字符
    - 每个技能只能访问其 `tools` 列表中声明的工具
    - 技能的输出默认保存在 `zhi-output/` 目录
    - 只能删除用户创建的技能 YAML 文件，内置技能受保护

---

## Shell 命令教程

### 基本用法

在对话中要求 zhi 执行命令：

```
You [approve]: 运行 ls -la 查看当前目录
```

zhi 会显示即将执行的命令，等待你确认：

```
zhi wants to run: ls -la
Allow? [y/n]:
```

输入 `y` 允许执行，输入 `n` 拒绝。

### 三层安全保护

#### 1. 始终需要确认

无论处于 approve 模式还是 auto 模式，Shell 命令都需要用户确认。这是 zhi 最重要的安全原则。

#### 2. 危险命令额外警告

以下类型的命令会触发额外的破坏性警告：

- 文件删除：`rm`, `del`, `rmdir`
- 文件移动：`mv`
- 权限修改：`chmod`, `chown`
- 磁盘操作：`mkfs`, `dd`, `shred`, `truncate`
- 文件就地修改：`sed -i`
- Git 危险操作：`git reset --hard`, `git clean`

#### 3. 灾难性命令直接阻止

以下命令被永久禁止，无法执行：

- `rm -rf /` 或 `rm -rf ~`
- `rm -rf /*` 或 `rm -rf ~/`
- `mkfs /dev/...`
- fork 炸弹等恶意命令
- `dd if=/dev/zero of=/dev/...`

### 命令超时

Shell 命令默认超时 30 秒，最长可设置为 300 秒（5 分钟）。超时后 zhi 会终止整个进程组，确保不会有遗留进程。

### 输出限制

命令输出最大显示 100KB，超出部分会被截断并提示。

### 实用示例

```
You [approve]: 查看系统的 Python 版本

You [approve]: 统计 src/ 目录下有多少行代码

You [approve]: 运行 pytest 测试并告诉我结果
```

!!! warning
    永远不要让 AI 运行你不理解的命令，即使 zhi 会请求确认。跨平台支持：在 Windows 上使用 `CREATE_NEW_PROCESS_GROUP`，在 Unix 上使用 `start_new_session`。

---

## Web 内容获取教程

### 获取网页内容

```
You [approve]: 获取 https://example.com 的内容
```

zhi 会调用 `web_fetch` 工具抓取页面内容，自动将 HTML 转换为纯文本。

### 分析网页内容

```
You [approve]: 获取这个网页的内容并总结要点：https://example.com/article
```

zhi 会先获取内容，然后基于 GLM 模型进行分析。

### 获取并保存

```
You [approve]: 抓取 https://example.com/data 的内容，提取关键数据，保存为 CSV 文件
```

zhi 会组合使用 `web_fetch` 和 `file_write` 工具完成任务。

### 在技能中使用

可以创建包含 `web_fetch` 的技能，自动化网页内容处理：

```yaml
name: web-summary
description: Fetch and summarize web pages
model: glm-4-flash
system_prompt: |
  Fetch the given URL, read the content, and produce a concise
  summary in Chinese. Save the summary as a markdown file.
tools:
  - web_fetch
  - file_write
max_turns: 5
```

然后运行：

```bash
zhi run web-summary
```

!!! info
    - URL 必须以 `http://` 或 `https://` 开头
    - 请求超时时间为 30 秒
    - 响应内容上限为 50KB，超出部分会被截断
    - HTML 页面会自动去除标签，转换为纯文本
    - `web_fetch` 会自动跟随重定向
    - 内置 SSRF 防护

---

## 组合技能 { #composite-skills }

组合技能将多个单一技能串联成自动化的多步工作流。它们同样使用 `glm-4-flash` 模型，保持低成本。

### contract-review（合同审查）

**流程：** analyze + compare + proofread

从三个角度审查合同文档：结构分析以识别关键条款和风险，可选的版本对比以标注变更内容，以及校对以发现模糊措辞。

```bash
# 审查单份合同
zhi run contract-review contract.pdf

# 对比两个版本
zhi run contract-review contract-v2.pdf contract-v1.pdf
```

**输出：** 一份全面的审查报告，包含执行摘要、结构分析、版本变更（如适用）、语言问题、风险评估和谈判建议。

### daily-digest（每日摘要）

**流程：** file_list + summarize（批量）

扫描文件夹中的所有文档，生成一份包含各文档摘要和跨文档洞察的综合摘要报告。

```bash
zhi run daily-digest ./inbox/
```

**输出：** 摘要报告列出每份文档的总结、共同主题、矛盾之处和建议的后续行动。

!!! tip
    支持的文件类型包括 `.txt`、`.md`、`.pdf`、`.csv`、`.docx`、`.xlsx`、`.png` 和 `.jpg`。二进制文件和系统文件会被自动跳过。

### invoice-to-excel（发票转 Excel）

**流程：** extract-table + reformat

通过 OCR 表格提取处理发票文件（PDF、图片或文本），然后将所有明细项整合到结构化的 Excel 表格中。

```bash
# 单张发票
zhi run invoice-to-excel invoice.pdf

# 批量处理发票文件夹
zhi run invoice-to-excel ./invoices/
```

**输出：** 一个 Excel 文件，包含两个工作表 -- "Line Items"（所有发票的逐行明细）和 "Invoice Summary"（每张发票的汇总）。日期统一为 YYYY-MM-DD 格式，货币符号已清理，总额已验证。

### meeting-followup（会议跟进）

**流程：** meeting-notes + summarize + translate

接收原始会议笔记，生成完整的会后跟进材料包：结构化的会议纪要、供领导参阅的执行摘要，以及可选的翻译版本。

```bash
# 基本跟进
zhi run meeting-followup raw-notes.txt

# 附带翻译
zhi run meeting-followup raw-notes.txt --to english
```

**输出：** 三个文件 -- 完整的会议纪要、1 页执行摘要，以及（可选的）翻译版摘要。待办事项同时出现在完整纪要和摘要中。

### report-polish（报告润色）

**流程：** proofread + analyze + reformat

接收草稿文档，通过语言校对、结构分析和格式优化，输出可发布的终稿。

```bash
zhi run report-polish draft-report.md

# 指定输出格式
zhi run report-polish draft.md --format docx
```

**输出：** 两个文件 -- 润色后的文档和一份修改日志，包含修改前后的质量评分、所有修正内容、结构改进和剩余建议。

### translate-proofread（翻译校对）

**流程：** translate + proofread

翻译文档后对译文进行校对，确保译文在目标语言中读起来自然流畅。

```bash
# 默认翻译为中文
zhi run translate-proofread article-en.md

# 指定目标语言
zhi run translate-proofread article.md --to english
```

**输出：** 两个文件 -- 校对后的最终译文和一份质量报告，包含检测到的源语言、翻译质量评分、发现并修正的问题，以及可能需要人工审核的段落。

---

## 附录

### 管道模式

可以通过管道将文本输入 zhi：

```bash
echo "翻译成英文：你好世界" | zhi

cat article.txt | zhi
```

### 调试模式

如果遇到问题，启用调试日志：

```bash
zhi --debug
```

### 禁用颜色输出

在不支持颜色的终端中：

```bash
zhi --no-color
```

或设置环境变量：

```bash
export NO_COLOR=1
```

### 配置文件完整参考

配置文件位于系统配置目录下的 `config.yaml`：

```yaml
api_key: "你的API密钥"
default_model: "glm-5"
skill_model: "glm-4-flash"
output_dir: "zhi-output"
max_turns: 30
log_level: "INFO"
```

**配置文件位置：**

- macOS: `~/Library/Application Support/zhi/config.yaml`
- Linux: `~/.config/zhi/config.yaml`
- Windows: `%APPDATA%\zhi\config.yaml`

**支持的环境变量覆盖：**

| 环境变量 | 对应配置项 |
|----------|-----------|
| `ZHI_API_KEY` | `api_key` |
| `ZHI_DEFAULT_MODEL` | `default_model` |
| `ZHI_OUTPUT_DIR` | `output_dir` |
| `ZHI_LOG_LEVEL` | `log_level` |

环境变量 `ZHI_API_KEY` 的优先级高于配置文件。

### 常见问题

**Q: 提示 "No API key configured"**

运行 `zhi --setup` 或设置环境变量 `ZHI_API_KEY`。

**Q: 文件写入失败提示 "File already exists"**

`file_write` 不能覆盖已有文件。删除或重命名 `zhi-output/` 中的同名文件后重试。

**Q: OCR 识别结果为空**

确认文件格式受支持（PDF, PNG, JPG, JPEG, GIF, WEBP）且文件大小不超过 20MB。图片清晰度会影响识别效果。

**Q: Shell 命令被阻止**

某些危险命令（如 `rm -rf /`）被永久禁止。这是安全特性，无法绕过。

**Q: 想用 Excel/Word 输出但报错**

Excel (.xlsx) 和 Word (.docx) 已包含在默认安装中。请确认安装了最新版本：`pip install --upgrade zhicli`。
