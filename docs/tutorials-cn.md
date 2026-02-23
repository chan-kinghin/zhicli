# zhi CLI 中文教程

> zhi 是一个开源的 Python 命令行工具，由智谱 GLM 大模型驱动。安装后即可在终端中获得一个智能助手，支持对话、文件处理、OCR 识别、自定义技能等功能。

---

## 目录

1. [快速入门](#1-快速入门教程)
2. [交互式对话](#2-交互式对话教程)
3. [文件处理](#3-文件处理教程)
4. [技能系统](#4-技能系统教程)
5. [Shell 命令](#5-shell-命令教程)
6. [Web 内容获取](#6-web-内容获取教程)

---

## 1. 快速入门教程

### 目标

从零开始安装 zhi，配置 API 密钥，完成第一次对话。

### 前提条件

- Python 3.11 或更高版本
- pip 包管理器
- 智谱开放平台账号（用于获取 API 密钥）

### 具体步骤

#### 第一步：安装 zhi

```bash
pip install zhicli
```

如果需要 Excel (.xlsx) 和 Word (.docx) 文件支持，安装完整版：

```bash
pip install "zhicli[all]"
```

验证安装成功：

```bash
zhi --version
```

输出示例：

```
zhi 0.1.0
```

#### 第二步：获取 API 密钥

1. 访问智谱开放平台：https://open.bigmodel.cn
2. 注册账号并登录
3. 在控制台中创建 API 密钥
4. 复制密钥备用

#### 第三步：配置 API 密钥

**方式一：运行设置向导（推荐）**

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

**方式二：通过环境变量配置**

```bash
# Linux / macOS
export ZHI_API_KEY="你的API密钥"

# Windows (PowerShell)
$env:ZHI_API_KEY = "你的API密钥"
```

#### 第四步：开始第一次对话

直接运行 `zhi` 进入交互模式：

```bash
zhi
```

输出：

```
Welcome to zhi. Type /help for commands.
You [approve]:
```

输入你的第一个问题：

```
You [approve]: 你好，请用一句话介绍你自己
```

zhi 会通过 GLM-5 模型生成回答并在终端中流式输出。

#### 快速单次对话

如果不想进入交互模式，可以使用 `-c` 参数：

```bash
zhi -c "什么是机器学习？"
```

执行后直接输出回答，然后退出。

### 注意事项

- API 密钥会保存在系统配置目录中（macOS: `~/Library/Application Support/zhi/config.yaml`，Linux: `~/.config/zhi/config.yaml`，Windows: `%APPDATA%\zhi\config.yaml`），文件权限设置为仅所有者可读写
- 环境变量 `ZHI_API_KEY` 的优先级高于配置文件
- 如果需要重新配置，随时运行 `zhi --setup`

---

## 2. 交互式对话教程

### 目标

掌握 REPL 交互模式的核心功能：斜杠命令、权限模式切换、模型切换、多行输入等。

### 具体步骤

#### 进入交互模式

```bash
zhi
```

```
Welcome to zhi. Type /help for commands.
You [approve]:
```

提示符中的 `[approve]` 表示当前的权限模式。

#### 查看帮助

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

#### 权限模式切换

zhi 有两种权限模式：

- **approve 模式**（默认）：执行有风险的操作（如写文件、运行 Shell 命令）时需要你确认
- **auto 模式**：跳过确认提示，自动执行所有操作

```
You [approve]: /auto
Mode switched to auto

You [auto]: /approve
Mode switched to approve
```

#### 切换模型

zhi 支持三个模型：

| 模型 | 类型 | 特点 |
|------|------|------|
| `glm-5` | 高级 | 默认对话模型，智能但较贵 |
| `glm-4-flash` | 经济 | 技能执行模型，快速且便宜 |
| `glm-4-air` | 经济 | 轻量替代方案 |

查看当前模型：

```
You [approve]: /model
Current model: glm-5. Available: glm-5, glm-4-flash, glm-4-air
```

切换模型：

```
You [approve]: /model glm-4-flash
Model switched to glm-4-flash
```

#### 思考模式

启用思考模式后，模型会展示推理过程（仅 glm-5 支持）：

```
You [approve]: /think
Thinking mode enabled

You [approve]: 解释为什么天空是蓝色的

You [approve]: /fast
Thinking mode disabled
```

#### 多行输入

在行末添加 `\` 可以输入多行内容：

```
You [approve]: 请帮我写一个 Python 函数，\
...  要求接受一个列表参数，\
...  返回列表中的最大值
```

#### 管理对话历史

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

#### 查看用量统计

```
You [approve]: /usage
```

会显示当前会话的 token 用量和预估费用。

#### 退出

```
You [approve]: /exit
Goodbye!
```

也可以按 `Ctrl+D` 退出，或按 `Ctrl+C` 取消当前输入。

### 注意事项

- 输入历史会自动保存，下次启动可以用上下方向键浏览历史记录
- 包含敏感信息（如 api_key、password、token）的输入不会被保存到历史记录
- Tab 键可以自动补全斜杠命令和模型名称
- 切换模型只影响当前会话，不会修改配置文件

---

## 3. 文件处理教程

### 目标

学会使用 zhi 读取文件、识别图片/PDF 中的文字、将结果写入新文件。

### 具体步骤

#### 读取文本文件

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

#### 列出目录内容

```
You [approve]: 列出当前目录下的所有文件
```

zhi 会调用 `file_list` 工具展示文件列表，包含文件名、大小和修改时间。

#### OCR 识别图片和 PDF

将图片或 PDF 中的文字提取出来：

```
You [approve]: 请识别 invoice.png 中的文字内容
```

```
You [approve]: 提取 report.pdf 中的文字并总结要点
```

`ocr` 工具支持的格式：
- 图片：PNG, JPG, JPEG, GIF, WEBP
- 文档：PDF
- 文件大小限制：20MB

#### 写入新文件

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
| Excel | `.xlsx` | sheets 数据（需安装 openpyxl） |
| Word | `.docx` | Markdown 文本（需安装 python-docx） |

示例对话：

```
You [approve]: 帮我创建一个 CSV 文件，包含以下三个人的信息：
张三, 25岁, 北京
李四, 30岁, 上海
王五, 28岁, 广州
```

zhi 会在 `zhi-output/` 下创建 CSV 文件。

#### 组合使用：读取 + 处理 + 写入

```
You [approve]: 读取 data.csv 文件，分析数据趋势，然后把分析报告写成 report.md
```

zhi 会依次调用 file_read 读取数据、分析内容、然后调用 file_write 生成报告。

### 注意事项

- `file_write` 只能创建新文件，不能覆盖已有文件
- 所有输出文件都在 `zhi-output/` 目录下，不会影响你的原始文件
- 路径不允许包含 `..`，防止写入工作目录以外的位置
- 如果需要 Excel 或 Word 支持，确保安装了对应的依赖：`pip install "zhicli[all]"`
- 没有安装 openpyxl 时，Excel 请求会自动降级为 CSV；没有安装 python-docx 时，Word 请求会降级为 Markdown

---

## 4. 技能系统教程

### 目标

学会使用内置技能、创建自定义技能、从命令行直接运行技能。

### 什么是技能？

技能（Skill）是一组预定义的 YAML 配置，指定了系统提示词、可用工具和模型。它让你可以将常用的工作流程保存下来，一键运行。技能默认使用 `glm-4-flash` 模型，成本不到 GLM-5 的 10%。

### 具体步骤

#### 使用内置技能

zhi 自带两个内置技能：

**summarize** - 文档总结

```bash
# 从命令行直接运行
zhi run summarize report.txt
```

```
# 在交互模式中运行
You [approve]: /run summarize report.txt
```

**translate** - 翻译文本

```bash
# 翻译文件（默认翻译为中文）
zhi run translate readme-en.md
```

#### 查看已安装的技能

```
You [approve]: /skill list
```

#### 创建自定义技能

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

#### 技能 YAML 字段说明

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

#### 可用工具列表

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

#### 查看技能详情

```
You [approve]: /skill show code-review
```

#### 运行自定义技能

```bash
# 命令行模式
zhi run code-review main.py

# 交互模式
You [approve]: /run code-review main.py
```

#### 删除技能

```
You [approve]: /skill delete code-review
```

注意：只能删除用户创建的技能 YAML 文件，不会影响任何其他文件。

### 注意事项

- 技能名称必须匹配 `^[a-zA-Z0-9][a-zA-Z0-9_-]*$`，不允许包含空格或特殊字符
- 技能使用 `glm-4-flash` 模型执行，成本远低于交互对话
- 每个技能只能访问其 `tools` 列表中声明的工具
- 技能的输出默认保存在 `zhi-output/` 目录

---

## 5. Shell 命令教程

### 目标

学会通过 zhi 安全地执行 Shell 命令，理解权限确认机制和安全限制。

### 具体步骤

#### 基本用法

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

#### 安全机制

Shell 工具有三层安全保护：

**1. 始终需要确认**

无论处于 approve 模式还是 auto 模式，Shell 命令都需要用户确认。这是 zhi 最重要的安全原则。

**2. 危险命令额外警告**

以下类型的命令会触发额外的破坏性警告：

- 文件删除：`rm`, `del`, `rmdir`
- 文件移动：`mv`
- 权限修改：`chmod`, `chown`
- 磁盘操作：`mkfs`, `dd`, `shred`, `truncate`
- 文件就地修改：`sed -i`
- Git 危险操作：`git reset --hard`, `git clean`

**3. 灾难性命令直接阻止**

以下命令被永久禁止，无法执行：

- `rm -rf /` 或 `rm -rf ~`
- `rm -rf /*` 或 `rm -rf ~/`
- `mkfs /dev/...`
- fork 炸弹等恶意命令
- `dd if=/dev/zero of=/dev/...`

#### 设置命令超时

Shell 命令默认超时 30 秒，最长可设置为 300 秒（5 分钟）。超时后 zhi 会终止整个进程组，确保不会有遗留进程。

```
You [approve]: 运行一个耗时较长的命令，比如编译项目
```

#### 查看命令输出

命令输出最大显示 100KB，超出部分会被截断并提示。

#### 实用示例

```
You [approve]: 查看系统的 Python 版本

You [approve]: 统计 src/ 目录下有多少行代码

You [approve]: 运行 pytest 测试并告诉我结果
```

### 注意事项

- Shell 命令的确认机制不可跳过，即使在 auto 模式下也需要确认
- 命令超时后会使用 `os.killpg` 杀死整个进程组，不会留下僵尸进程
- 命令输出上限为 100KB
- 跨平台支持：在 Windows 上使用 `CREATE_NEW_PROCESS_GROUP`，在 Unix 上使用 `start_new_session`
- 永远不要让 AI 运行你不理解的命令，即使 zhi 会请求确认

---

## 6. Web 内容获取教程

### 目标

学会使用 zhi 获取网页内容并进行分析处理。

### 具体步骤

#### 获取网页内容

```
You [approve]: 获取 https://example.com 的内容
```

zhi 会调用 `web_fetch` 工具抓取页面内容，自动将 HTML 转换为纯文本。

#### 分析网页内容

```
You [approve]: 获取这个网页的内容并总结要点：https://example.com/article
```

zhi 会先获取内容，然后基于 GLM 模型进行分析。

#### 获取并保存

```
You [approve]: 抓取 https://example.com/data 的内容，提取关键数据，保存为 CSV 文件
```

zhi 会组合使用 `web_fetch` 和 `file_write` 工具完成任务。

#### 在技能中使用

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

### 注意事项

- URL 必须以 `http://` 或 `https://` 开头
- 请求超时时间为 30 秒
- 响应内容上限为 50KB，超出部分会被截断
- HTML 页面会自动去除标签，转换为纯文本
- 如果页面无法提取到文本，会返回提示信息
- `web_fetch` 会自动跟随重定向

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

支持的环境变量覆盖：

| 环境变量 | 对应配置项 |
|----------|-----------|
| `ZHI_API_KEY` | `api_key` |
| `ZHI_DEFAULT_MODEL` | `default_model` |
| `ZHI_OUTPUT_DIR` | `output_dir` |
| `ZHI_LOG_LEVEL` | `log_level` |

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

安装可选依赖：`pip install "zhicli[all]"`。未安装时 Excel 会降级为 CSV，Word 会降级为 Markdown。
