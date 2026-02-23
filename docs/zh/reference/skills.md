# 技能参考

zhi 内置 **15 个技能**，分为两类：单一用途技能（执行单个任务）和组合技能（编排多个技能协同工作）。

## 单一用途技能

### summarize

将文本文件或文档生成简明的 markdown 摘要。

| 属性 | 值 |
|------|-----|
| 模型 | `glm-4-flash` |
| 工具 | `file_read`、`file_write` |
| 最大轮次 | 5 |

**用法：**

```bash
zhi run summarize report.txt
```

**输出：** 保存到 `zhi-output/` 的 markdown 摘要，包含要点、主要论点和重要细节。

---

### translate

在不同语言之间翻译文本，默认翻译为中文（简体）。

| 属性 | 值 |
|------|-----|
| 模型 | `glm-4-flash` |
| 工具 | `file_read`、`file_write` |
| 最大轮次 | 5 |

**参数：**

| 名称 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `file` | file | 否 | - | 要翻译的文件 |
| `text` | string | 否 | - | 要翻译的文本 |
| `to` | string | 否 | `chinese` | 目标语言 |

**用法：**

```bash
zhi run translate readme-en.md
```

---

### extract-text

使用 OCR 从 PDF 或图片文件中提取文本，保存为纯文本。

| 属性 | 值 |
|------|-----|
| 模型 | `glm-4-flash` |
| 工具 | `ocr`、`file_write`、`file_list` |
| 最大轮次 | 5 |

**用法：**

```bash
zhi run extract-text invoice.pdf
```

**输出：** 清理后的 `.txt` 文件，保留文档结构（标题、段落、列表）。页眉页脚被移除，表格以对齐文本呈现。

---

### extract-table

从文档中提取表格并保存为 CSV 或 Excel。

| 属性 | 值 |
|------|-----|
| 模型 | `glm-4-flash` |
| 工具 | `ocr`、`file_read`、`file_write`、`file_list` |
| 最大轮次 | 8 |

**用法：**

```bash
zhi run extract-table report.pdf
```

**输出：** 包含正确列标题的 CSV 文件。多个表格分别保存为独立文件（`table1.csv`、`table2.csv`），或在结构相同时合并。

!!! tip "Excel 输出"
    在提示中指定 `.xlsx` 输出格式，技能将生成 Excel 文件而非 CSV。

---

### analyze

对文档进行深度分析，生成结构化见解。

| 属性 | 值 |
|------|-----|
| 模型 | `glm-4-flash` |
| 工具 | `file_read`、`ocr`、`file_write`、`file_list` |
| 最大轮次 | 8 |

**用法：**

```bash
zhi run analyze proposal.md
```

**输出：** 包含四个部分的 markdown 报告：

1. **文档概览** -- 类型、长度、结构、主要语言
2. **关键发现** -- 主要话题、论点、数据点
3. **结构分析** -- 组织方式、逻辑流程、不足之处
4. **可操作建议** -- 隐含的决策、未解问题、后续步骤

---

### proofread

校对文档并输出修正报告。

| 属性 | 值 |
|------|-----|
| 模型 | `glm-4-flash` |
| 工具 | `file_read`、`ocr`、`file_write` |
| 最大轮次 | 5 |

**用法：**

```bash
zhi run proofread draft.md
```

**输出：** markdown 报告，包含：

- 总体质量评分（满分 10 分）
- 逐条修正：位置、原文、修改后文本、错误类型（拼写 / 语法 / 标点 / 风格 / 清晰度）
- 常见错误模式总结

---

### reformat

在不同格式之间转换文档。

| 属性 | 值 |
|------|-----|
| 模型 | `glm-4-flash` |
| 工具 | `file_read`、`ocr`、`file_write`、`file_list` |
| 最大轮次 | 8 |

**参数：**

| 名称 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `file` | file | 是 | - | 要转换的文件 |
| `format` | string | 否 | `markdown` | 目标格式 |

**支持的转换：**

| 源格式 | 目标格式 |
|--------|----------|
| 纯文本 | Markdown |
| Markdown | 纯文本 |
| CSV | Markdown 表格 |
| CSV | Excel (`.xlsx`) |
| 任意文本 | CSV |
| 任意文本 | JSON |
| PDF/图片（OCR） | Markdown / 文本 / CSV |

**用法：**

```bash
zhi run reformat data.csv
```

---

### meeting-notes

将原始会议记录整理为结构化会议纪要。

| 属性 | 值 |
|------|-----|
| 模型 | `glm-4-flash` |
| 工具 | `file_read`、`ocr`、`file_write` |
| 最大轮次 | 5 |

**用法：**

```bash
zhi run meeting-notes notes.txt
```

**输出：** 结构化 markdown 会议纪要，包含：

- **参会人员** -- 参与者列表
- **议题** -- 每个话题的讨论要点和决定
- **待办事项** -- 任务、负责人、截止日期表格
- **关键决定** -- 编号列表
- **后续步骤** -- 跟进事项和下次会议日期

---

### compare

比较两个文档并标注差异。

| 属性 | 值 |
|------|-----|
| 模型 | `glm-4-flash` |
| 工具 | `file_read`、`ocr`、`file_write`、`file_list` |
| 最大轮次 | 8 |

**参数：**

| 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | file | 是 | 第一个文件 |
| `file2` | file | 是 | 第二个文件 |

**用法：**

```bash
zhi run compare v1.md v2.md
```

**输出：** markdown 差异报告，包含比较摘要、新增/删除/修改的部分和未变化的部分。聚焦有意义的差异，忽略空白格式变化。

---

## 组合技能

组合技能通过 `skill_<名称>` 工具包装器编排多个单一用途技能。它们有更高的轮次限制以适应多步骤工作流。

### contract-review

多步骤合同分析，结合分析、比较和校对。

| 属性 | 值 |
|------|-----|
| 模型 | `glm-4-flash` |
| 工具 | `file_read`、`ocr`、`file_write`、`file_list`、`skill_analyze`、`skill_compare`、`skill_proofread` |
| 最大轮次 | 15 |

**参数：**

| 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | file | 是 | 要审查的合同 |
| `file2` | file | 否 | 用于比较的旧版本 |

**用法：**

```bash
zhi run contract-review contract-v2.pdf contract-v1.pdf
```

**输出：** 综合审查报告，包含：

- 执行摘要及总体评估
- 结构分析（关键条款、义务、风险）
- 版本比较（如提供旧版本）
- 语言和一致性问题
- 风险评估（责任、赔偿、终止）
- 编号建议

---

### daily-digest

批量汇总文件夹中的所有文档为一份摘要。

| 属性 | 值 |
|------|-----|
| 模型 | `glm-4-flash` |
| 工具 | `file_list`、`file_read`、`ocr`、`file_write`、`skill_summarize` |
| 最大轮次 | 15 |

**支持的文件类型：** `.txt`、`.md`、`.pdf`、`.csv`、`.docx`、`.xlsx`、`.png`、`.jpg`

**用法：**

```bash
zhi run daily-digest ./reports/
```

**输出：** 单个 markdown 摘要，包含：

- 概览（文档数量、关键主题）
- 每个文档的单独摘要
- 跨文档洞察（共同主题、矛盾、跟进行动）

---

### invoice-to-excel

OCR 识别发票并将明细合并为 Excel 表格。

| 属性 | 值 |
|------|-----|
| 模型 | `glm-4-flash` |
| 工具 | `file_list`、`file_read`、`ocr`、`file_write`、`skill_extract-table`、`skill_reformat` |
| 最大轮次 | 15 |

**用法：**

```bash
zhi run invoice-to-excel invoices/
```

**输出：** Excel 文件，包含：

- **工作表 1 "Line Items"**：发票号、日期、供应商、项目、数量、单价、金额、税额、合计
- **工作表 2 "Invoice Summary"**（多张发票时）：发票号、日期、供应商、小计、税额、合计、状态

!!! info "数据标准化"
    货币已标准化（去除符号，统一小数格式）。日期格式为 `YYYY-MM-DD`。缺失字段显示 `N/A`。

---

### meeting-followup

从原始会议记录生成结构化纪要、执行摘要和可选翻译。

| 属性 | 值 |
|------|-----|
| 模型 | `glm-4-flash` |
| 工具 | `file_read`、`ocr`、`file_write`、`skill_meeting-notes`、`skill_summarize`、`skill_translate` |
| 最大轮次 | 15 |

**参数：**

| 名称 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | file | 是 | 原始会议记录 |
| `translate_to` | string | 否 | 摘要翻译目标语言 |

**用法：**

```bash
zhi run meeting-followup standup-notes.txt
```

**输出：** 最多三个文件：

1. `[会议]-minutes.md` -- 完整结构化会议纪要
2. `[会议]-summary.md` -- 执行摘要（最多 1 页）
3. `[会议]-summary-en.md` -- 翻译后的摘要（如适用）

---

### report-polish

校对、分析结构并生成润色后的最终版文档。

| 属性 | 值 |
|------|-----|
| 模型 | `glm-4-flash` |
| 工具 | `file_read`、`ocr`、`file_write`、`skill_proofread`、`skill_analyze`、`skill_reformat` |
| 最大轮次 | 12 |

**参数：**

| 名称 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `file` | file | 是 | - | 草稿文档 |
| `format` | string | 否 | `markdown` | 输出格式（markdown、docx、txt） |

**用法：**

```bash
zhi run report-polish draft-report.md
```

**输出：** 两个文件：

1. `[文件名]-final.[扩展名]` -- 润色后的文档
2. `[文件名]-changes.md` -- 变更日志，包含修改前后质量评分、语言修正、结构改进和剩余建议

---

### translate-proofread

翻译文档并校对译文质量。

| 属性 | 值 |
|------|-----|
| 模型 | `glm-4-flash` |
| 工具 | `file_read`、`ocr`、`file_write`、`skill_translate`、`skill_proofread` |
| 最大轮次 | 12 |

**参数：**

| 名称 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `file` | file | 是 | - | 要翻译的文档 |
| `to` | string | 否 | `chinese` | 目标语言 |

**用法：**

```bash
zhi run translate-proofread whitepaper.md
```

**输出：** 两个文件：

1. `[文件名]-translated.[扩展名]` -- 润色后的最终译文
2. `[文件名]-translation-report.md` -- 质量报告，包含检测到的源语言、质量评分（1-10）、已修复的问题和需要人工审查的段落

---

## 创建自定义技能

您可以通过编写 YAML 配置文件创建自定义技能。将文件放置在用户技能目录中，或使用 `skill_create` 工具。

```yaml
name: my-skill
description: 这个技能的功能描述
model: glm-4-flash
system_prompt: |
  给模型的指令...
tools:
  - file_read
  - file_write
max_turns: 10
```

!!! info "技能命名规则"
    技能名称必须匹配 `^[a-zA-Z0-9][a-zA-Z0-9_-]*$`，最长 64 个字符。不允许空格、斜杠或特殊字符。
