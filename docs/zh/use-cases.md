# zhi 使用场景大全

> 本文档通过真实场景演示 zhi CLI 的各种用法，帮助你快速找到适合自己的工作流。

---

---

## 一、日常办公场景

### 1.1 总结会议纪要

**场景**：产品评审会结束后，你手头有一份冗长的会议记录文本，需要快速整理成重点明确的纪要发给团队。

**操作步骤**：

使用内置的 `summarize` 技能，一行命令即可完成：

```bash
$ zhi run summarize 产品评审会议记录.txt
```

zhi 读取文件内容后，自动生成结构化摘要并保存到 `zhi-output/` 目录：

```
[file_read] 读取: 产品评审会议记录.txt (12.3KB)
[file_write] 写入: 产品评审会议记录-摘要.md (1.8KB)

文件已保存: zhi-output/产品评审会议记录-摘要.md
```

**预期效果**：输出一份 Markdown 格式的会议纪要，包含关键决策、待办事项和负责人。摘要通常是原文的 10%-20%，重点突出，方便分发。

你也可以在交互模式下操作，给出更具体的要求：

```bash
$ zhi
You [approve]: 帮我总结一下这份会议记录，重点提取待办事项和截止日期
```

---

### 1.2 翻译文档

**场景**：收到一份英文技术规格书，需要翻译成中文给团队评审。

**操作步骤**：

使用内置的 `translate` 技能：

```bash
$ zhi run translate api-specification.md
```

默认翻译为简体中文。如果需要翻译为其他语言，在交互模式下指定：

```bash
$ zhi -c "把 项目介绍.md 翻译成英文，保持 Markdown 格式不变"
```

输出示例：

```
[file_read] 读取: api-specification.md (8.5KB)
[file_write] 写入: api-specification-翻译.md (9.2KB)

文件已保存: zhi-output/api-specification-翻译.md
```

**预期效果**：保留原文档结构（标题层级、代码块、列表）的完整中文翻译。技术术语（如 API、JSON、HTTP）保留英文原词。

---

### 1.3 生成周报/日报

**场景**：周五下午需要写一份工作周报，手头有这一周的工作日志和 Git 提交记录。

**操作步骤**：

```bash
$ zhi
You [approve]: 根据本周的工作笔记生成一份周报，包含完成事项、进行中事项和下周计划
```

zhi 会请求读取你的工作笔记文件：

```
[file_read] 读取: 本周工作笔记.md (3.2KB)
  → 允许读取此文件? (y/n) y
[file_write] 写入: 周报-2026-02-23.md (1.5KB)
  → 允许创建此文件? (y/n) y

文件已保存: zhi-output/周报-2026-02-23.md
```

**预期效果**：一份格式规范的周报，按"本周完成"、"进行中"、"下周计划"三个板块组织。

如果需要结合 Git 记录，可以用管道传入：

```bash
$ git log --oneline --since="last monday" | zhi -c "根据这些 Git 提交记录生成本周工作总结"
```

---

## 二、数据提取与对比

### 2.1 对比两份文档的差异

**场景**：客户发来了合同的修订版，你需要快速找出两个版本之间的具体变更内容。

**操作步骤**：

使用内置的 `compare` 技能，一行命令即可完成：

```bash
$ zhi run compare 合同-v1.md 合同-v2.md
```

zhi 逐段对比两份文档，输出差异报告：

```
[file_read] 读取: 合同-v1.md (6.2KB)
[file_read] 读取: 合同-v2.md (6.8KB)
[file_write] 写入: 合同-差异对比.md (2.5KB)

文件已保存: zhi-output/合同-差异对比.md
```

**预期效果**：清晰列出两份文档之间的新增、删除和修改内容，用表格标注具体位置和变更前后的差异，方便逐项确认。

---

### 2.2 从财务报表提取关键数据

**场景**：收到一份季度财务报告 PDF，需要快速提取收入、利润等关键指标供管理层参考。

**操作步骤**：

```bash
$ zhi -c "读取 季度财务报表.pdf，提取收入、利润、同比增长等关键指标，保存为表格"
```

zhi 通过 OCR 识别 PDF 内容，提取结构化数据：

```
[ocr] 识别: 季度财务报表.pdf (4.5MB)
[file_write] 写入: 财务关键指标.xlsx (3.2KB)

文件已保存: zhi-output/财务关键指标.xlsx
```

**预期效果**：从 PDF 报表中自动识别并提取关键财务数据，整理成结构化的表格文件，包含同比和环比计算。省去手动抄录数据的繁琐工作。

---

### 2.3 整理客户联系人列表

**场景**：手头有一份混乱的客户联系人 CSV 文件，包含重复记录和格式不统一的数据，需要清洗整理后输出。

**操作步骤**：

```bash
$ zhi -c "读取 客户联系人.csv，去除重复项，按公司名称排序，保存为新的 Excel 文件"
```

zhi 读取文件，自动识别并处理重复项：

```
[file_read] 读取: 客户联系人.csv (8.6KB)
[file_write] 写入: 客户联系人-整理.xlsx (5.1KB)

文件已保存: zhi-output/客户联系人-整理.xlsx
```

**预期效果**：自动去除重复记录，统一数据格式，按指定字段排序后输出为 Excel 文件。原始 CSV 文件不受影响。

---

### 2.4 跨文档信息汇总

**场景**：手头有多份项目进度报告，需要将各项目的关键信息汇总到一份文档中，方便整体把控。

**操作步骤**：

在交互模式下操作，逐一读取并汇总：

```bash
$ zhi
You [approve]: 依次读取 项目A-进度报告.md、项目B-进度报告.md 和 项目C-进度报告.md，\
...  提取各项目的完成进度、风险项和下阶段计划，汇总生成一份整体报告
```

```
[file_read] 读取: 项目A-进度报告.md (3.5KB)
[file_read] 读取: 项目B-进度报告.md (4.1KB)
[file_read] 读取: 项目C-进度报告.md (2.8KB)
[file_write] 写入: 项目汇总报告.md (3.6KB)

文件已保存: zhi-output/项目汇总报告.md
```

**预期效果**：从多份独立报告中提取关键信息，交叉对比后生成结构化的汇总文档，包含进度表格、风险清单和行动计划。

---

## 三、内容创作场景

### 3.1 文章摘要与改写

**场景**：你需要对一篇长文章进行压缩整理，或者调整文风适配不同的发布平台。

**操作步骤**：

生成简短摘要：

```bash
$ zhi run summarize 技术分享文章.md
```

在交互模式下要求改写：

```bash
$ zhi
You [approve]: 读取 技术分享文章.md，用更通俗易懂的语言改写，目标读者是非技术人员
```

```
[file_read] 读取: 技术分享文章.md (6.8KB)
[file_write] 写入: 技术分享-通俗版.md (5.2KB)

文件已保存: zhi-output/技术分享-通俗版.md
```

**预期效果**：在保留核心观点的前提下，调整语言风格和专业术语的使用深度。原始文件不会被修改，改写结果保存为新文件。

---

### 3.2 多语言内容翻译

**场景**：公司产品需要同时发布中文和英文版本的更新日志。

**操作步骤**：

```bash
$ zhi -c "读取 更新日志-v2.5.md，翻译成英文，保持 Markdown 格式和版本号不变"
```

```
[file_read] 读取: 更新日志-v2.5.md (2.1KB)
[file_write] 写入: changelog-v2.5-en.md (2.3KB)

文件已保存: zhi-output/changelog-v2.5-en.md
```

**预期效果**：翻译准确流畅，格式完全保留。版本号、代码片段、变量名等不被翻译。

---

### 3.3 Markdown 格式化输出

**场景**：需要将零散的笔记整理成结构化的 Markdown 文档。

**操作步骤**：

```bash
$ zhi
You [approve]: 读取 会议笔记-原始.txt，整理成格式规范的 Markdown 文档，添加标题层级和列表
```

```
[file_read] 读取: 会议笔记-原始.txt (1.8KB)
[file_write] 写入: 会议笔记-整理.md (2.0KB)

文件已保存: zhi-output/会议笔记-整理.md
```

**预期效果**：结构清晰的 Markdown 文件，包含正确的标题层级、有序/无序列表、引用块等元素。可直接粘贴到飞书、Notion 或 GitHub。

---

## 四、数据处理场景

### 4.1 PDF/图片 OCR 提取文字

**场景**：拿到一份扫描版的合同 PDF 或手写会议白板照片，需要将内容转为可编辑的文本。

**操作步骤**：

PDF 文件提取：

```bash
$ zhi -c "用 OCR 识别 合同扫描件.pdf 中的文字，保存为文本文件"
```

```
[ocr] 识别: 合同扫描件.pdf (3.2MB)
[file_write] 写入: 合同内容.txt (8.5KB)

文件已保存: zhi-output/合同内容.txt
```

图片文字识别：

```bash
$ zhi -c "识别 白板照片.jpg 中的文字内容，整理成条目列表"
```

**预期效果**：从 PDF 或图片中提取文字，并按要求整理格式。支持的格式包括 PDF、PNG、JPG、GIF、WEBP，文件大小上限 20MB。

批量处理多张图片：

```bash
$ zhi
You [approve]: 依次识别 截图1.png 和 截图2.png 的文字内容，合并整理成一个文档
```

---

### 4.2 CSV/Excel 数据整理

**场景**：手头有一份混乱的 CSV 数据，需要清洗整理后输出为 Excel 格式。

**操作步骤**：

```bash
$ zhi
You [approve]: 读取 销售数据-原始.csv，按地区汇总销售额，生成新的 Excel 文件
```

```
[file_read] 读取: 销售数据-原始.csv (15.6KB)
[file_write] 写入: 销售汇总-按地区.xlsx (4.8KB)

文件已保存: zhi-output/销售汇总-按地区.xlsx
```

也支持 CSV 到 CSV 的处理：

```bash
$ zhi -c "读取 用户列表.csv，去除重复项，按注册日期排序，保存为新的 CSV"
```

**预期效果**：数据经过清洗、汇总或转换后保存为指定格式。Excel 文件需要安装 `openpyxl`（`pip install zhicli[all]`），否则自动降级输出为 CSV。

---

### 4.3 网页内容抓取与分析

**场景**：需要从某个网页获取信息并整理成报告。

**操作步骤**：

```bash
$ zhi
You [approve]: 抓取 https://example.com/tech-trends-2026 的内容，提取要点并整理成中文摘要
```

```
[web_fetch] 抓取: https://example.com/tech-trends-2026 (28.5KB)
[file_write] 写入: 技术趋势摘要.md (2.1KB)

文件已保存: zhi-output/技术趋势摘要.md
```

**预期效果**：从网页中提取正文内容，去除广告和导航元素，生成结构化的中文摘要。网页内容上限 50KB，超出部分自动截断。

结合翻译使用：

```bash
$ zhi -c "抓取 https://example.com/release-notes 的内容，翻译成中文并保存"
```

---

## 五、自定义技能场景

zhi 支持通过 YAML 文件定义自定义技能。技能一旦创建，就可以像内置功能一样反复使用。技能使用 `glm-4-flash` 模型执行，成本仅为交互聊天的 10%。

### 5.1 创建合同审查技能

**场景**：法务团队需要一个标准化的合同审查清单，每次收到新合同时执行相同的检查流程，确保关键条款不遗漏。

**操作步骤**：

在交互模式中让 zhi 创建技能：

```bash
$ zhi
You [approve]: 帮我创建一个合同审查技能，要求检查以下方面：\
...  关键条款是否齐全、截止日期条款、责任限制、\
...  终止条件、付款条款
```

```
[skill_create] 创建技能: contract-review
  → 允许创建此技能? (y/n) y

技能 'contract-review' 已创建
```

使用该技能：

```bash
$ zhi run contract-review 供应商服务合同.md
```

**预期效果**：每份合同都经过统一标准的审查，输出格式一致的审查报告。法务团队成员可快速定位需要补充或修改的条款。

!!! tip
    zhi 还内置了一个 `contract-review` 组合技能，将 analyze、compare 和 proofread 串联起来进行全面审查。内置版本适合综合审查，自定义版本适合针对特定审查清单。

---

### 5.2 创建邮件草稿技能

**场景**：每天需要发送多封格式类似的工作邮件，希望自动生成草稿。

**操作步骤**：

```bash
$ zhi
You [approve]: 创建一个邮件草稿技能，能根据简要描述生成正式的工作邮件，包含称呼、正文和结尾
```

```
[skill_create] 创建技能: email-draft
  → 允许创建此技能? (y/n) y

技能 'email-draft' 已创建
```

使用示例：

```bash
$ zhi -c "用 email-draft 技能写一封邮件：告知客户王总项目验收时间推迟到下周三"
```

**预期效果**：一键生成格式规范的邮件草稿，可直接复制粘贴到邮件客户端。

---

### 5.3 创建数据分析技能

**场景**：每月需要对销售数据做固定格式的分析报告。

**操作步骤**：

```bash
$ zhi
You [approve]: 创建一个月度数据分析技能，功能包括：读取 CSV 数据、\
...  计算环比增长、按维度汇总、生成 Markdown 报告和 Excel 汇总表
```

使用该技能：

```bash
$ zhi run monthly-report 2026年1月销售数据.csv
```

输出：

```
[file_read] 读取: 2026年1月销售数据.csv (25.6KB)
[file_write] 写入: 月度分析报告-2026-01.md (3.8KB)
[file_write] 写入: 月度汇总表-2026-01.xlsx (5.2KB)

文件已保存:
  zhi-output/月度分析报告-2026-01.md
  zhi-output/月度汇总表-2026-01.xlsx
```

**预期效果**：每月只需一行命令，即可生成完整的分析报告和 Excel 数据表。报告格式固定、口径统一，适合直接提交给管理层。

---

## 六、开发者工作流

### 6.1 使用自定义技能做代码审查

**场景**：在提交代码前想做一次快速的自动化审查。

**操作步骤**：

创建代码审查技能：

```yaml
name: code-review
description: Review source code and suggest improvements
model: glm-4-flash
system_prompt: |
  You are an experienced code reviewer. Read the provided source code and
  give actionable suggestions. Focus on:
  - Code quality and readability
  - Potential bugs or edge cases
  - Performance issues
  - Security concerns (injection, hardcoded secrets, etc.)
  Output as structured markdown with severity levels.
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
  description: Code review report
  directory: zhi-output
```

运行：

```bash
$ zhi run code-review src/auth.py
```

**预期效果**：一份带有严重程度标注的结构化审查报告，可直接粘贴到 Pull Request 评论中。

### 6.2 生成测试数据

**场景**：开发或演示时需要真实感的测试数据。

**操作步骤**：

```bash
$ zhi -c "生成 50 行真实感的用户测试数据：\
  中文姓名、邮箱、手机号（中国格式）、注册日期（2024-2026）、\
  账号状态。保存为 CSV。"
```

```
[file_write] 写入: test-users.csv (4.2KB)

文件已保存: zhi-output/test-users.csv
```

**预期效果**：一份包含真实感数据的 CSV 文件，符合本地化格式。不使用任何真实个人信息。

### 6.3 总结 Git 历史

**场景**：需要根据最近的提交记录撰写发布说明或变更日志。

**操作步骤**：

```bash
$ git log --oneline --since="2026-02-01" | zhi -c "将这些提交整理成变更日志，按类别分组（新功能、修复、维护）"
```

**预期效果**：结构化的变更日志，提交记录按类别分组并用友好的语言描述。

更详细的版本：

```bash
$ git log --format="%h %s (%an, %ar)" --since="last month" | zhi -c "根据这些提交撰写 v2.5 的发布说明"
```

### 6.4 低成本批量处理

**场景**：需要批量处理大量文件，但希望控制成本。

!!! info "成本对比"
    技能默认使用 `glm-4-flash`，成本约为 **GLM-5 的 10%**。批量操作时，这个差异非常显著。

**策略**：对重复性任务使用技能而非交互对话：

```bash
# 以约 10% 的对话成本处理 20 份文档
for f in docs/*.md; do
  zhi run summarize "$f"
done

# 或使用 daily-digest 组合技能生成一份汇总报告
zhi run daily-digest ./docs/
```

**成本对比示例**：

| 方式 | 模型 | 单文档成本 | 20 份文档 |
|------|------|-----------|----------|
| 交互对话 | GLM-5 | ~0.05 元 | ~1.00 元 |
| 技能执行 | GLM-4-flash | ~0.005 元 | ~0.10 元 |

技能是任何可重复的、基于文件的工作流的首选方案。

---

## 附录：常用命令速查

| 操作 | 命令 |
|------|------|
| 启动交互模式 | `zhi` |
| 单次提问 | `zhi -c "你的问题"` |
| 管道输入 | `cat 文件.txt \| zhi -c "总结这段内容"` |
| 运行技能 | `zhi run <技能名> [文件...]` |
| 首次配置 | `zhi --setup` |
| 查看版本 | `zhi --version` |
| 调试模式 | `zhi --debug` |

### 交互模式下的斜杠命令

| 命令 | 说明 |
|------|------|
| `/help` | 查看帮助信息 |
| `/model glm-5` | 切换到 GLM-5 模型（更智能、更贵） |
| `/model glm-4-flash` | 切换到 GLM-4-flash（更快、更便宜） |
| `/auto` | 自动模式（跳过工具确认弹窗） |
| `/approve` | 审批模式（默认，每次工具调用都需确认） |
| `/think` | 开启思考模式（仅 GLM-5 支持） |
| `/fast` | 关闭思考模式 |
| `/run <技能> [文件]` | 在交互模式内运行技能 |
| `/skill list` | 列出已安装的技能 |
| `/skill new` | 创建新技能 |
| `/reset` | 清空对话历史 |
| `/undo` | 撤销最近一轮对话 |
| `/usage` | 查看当前会话的 Token 用量 |
| `/exit` | 退出 zhi |

### 安全提示

- **所有文件写入**都保存到 `zhi-output/` 目录，不会修改你的原始文件
- **Shell 命令**每次执行前都需要手动确认（即使在 `/auto` 模式下）
- **危险命令**（`rm`、`mv` 等）会显示额外警告
- **灾难性命令**（`rm -rf /` 等）被完全禁止执行
- **OCR 文件**大小上限 20MB
- **技能名称**只允许字母、数字、连字符和下划线
