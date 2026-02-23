# 架构

## 概览

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI 层                                │
│  cli.py ─── 参数解析、模式分发                                │
│  repl.py ── 交互式 REPL + 斜杠命令                           │
│  ui.py ──── 基于 Rich 的终端输出                              │
├─────────────────────────────────────────────────────────────┤
│                       代理层                                 │
│  agent.py ── 代理循环（LLM → 工具 → LLM → ...）              │
│  client.py ─ 智谱 API 客户端                                  │
│  models.py ─ 模型注册表（GLM-5、GLM-4-flash、GLM-4-air）      │
├─────────────────────────────────────────────────────────────┤
│                       工具层                                 │
│  tools/base.py ──── BaseTool 抽象基类 + Registrable 协议      │
│  tools/__init__.py ─ ToolRegistry + 工厂函数                  │
│  tools/file_read.py、file_write.py、file_list.py              │
│  tools/ocr.py、shell.py、web_fetch.py、skill_create.py       │
│  tools/skill_tool.py ── 嵌套代理的 SkillTool 包装器           │
├─────────────────────────────────────────────────────────────┤
│                       技能层                                 │
│  skills/loader.py ── YAML 解析 + 验证                        │
│  skills/__init__.py ─ 发现机制（内置 + 用户目录）              │
│  skills/builtin/*.yaml ── 15 个内置技能配置                   │
├─────────────────────────────────────────────────────────────┤
│                       支持层                                 │
│  config.py ── 平台特定配置（YAML + 环境变量）                  │
│  i18n.py ──── 双语字符串目录 + 语言前导指令                    │
│  errors.py ── 结构化错误类型                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 双模型架构

zhi 使用两个具有不同性价比特征的模型：

| 模型 | 角色 | 层级 | 思考模式 | 使用场景 |
|------|------|------|----------|----------|
| **GLM-5** | 交互对话 | 高级 | 支持 | 对话、复杂推理 |
| **GLM-4-flash** | 技能执行 | 经济 | 不支持 | 批量任务、文档处理 |

**为什么使用两个模型？**

- 交互对话受益于 GLM-5 更深层的推理和思考模式
- 技能（总结、翻译、提取）运行确定性工作流，GLM-4-flash 足以胜任
- GLM-4-flash 的成本约为 GLM-5 的 10%，使批量操作具有成本效益
- 用户可以通过 `/model` 按会话覆盖，或在 YAML 配置中按技能覆盖

---

## 代理循环

zhi 的核心是 `agent.py` 中在 LLM 和工具之间迭代的代理循环：

```
用户输入 → Context → LLM（带工具 schema）
                         │
                    有工具调用？
                    │ 是           │ 否
                    ▼              ▼
              执行工具         返回响应
              追加结果
              循环 ←──────┘
```

### Context

`Context` 数据类保存单次代理运行的所有状态：

```python
@dataclass
class Context:
    config: Any              # ZhiConfig 实例
    client: ClientLike       # 智谱 API 客户端
    model: str               # 当前活跃模型
    tools: dict[str, ToolLike]  # 可用工具
    tool_schemas: list[dict]    # OpenAI 格式函数 schema
    permission_mode: PermissionMode  # approve 或 auto
    conversation: list[dict]        # 消息历史
    session_tokens: int = 0         # 累计 token 数
    max_turns: int = 30             # 轮次限制
    thinking_enabled: bool = True   # 扩展推理
    # UI 集成回调
    on_stream, on_thinking, on_tool_start, on_tool_end,
    on_permission, on_waiting
```

### 循环行为

1. 将对话 + 工具 schema 发送给 LLM
2. 如果响应包含工具调用：
   - 检查权限（approve 模式下的风险工具）
   - 执行每个工具，输出上限 50KB
   - 将结果追加到对话
   - 回到步骤 1
3. 如果响应为纯文本，返回（代理完成）
4. 如果达到 `max_turns`，返回 `None`

### 权限检查

```
工具有风险？
  │ 否 → 立即执行
  │ 是
  ▼
模式为 approve？
  │ 否（auto）→ 立即执行（shell 除外）
  │ 是
  ▼
调用 on_permission 回调 → 用户批准？ → 执行
                          用户拒绝？ → 返回"权限被拒绝"
```

!!! info "Shell 始终需要确认"
    `shell` 工具的 `risky = True`，代理循环始终检查其权限，无论权限模式如何。这在工具层面强制执行。

---

## 工具注册表

### BaseTool 抽象基类

所有内置工具继承自 `BaseTool`：

```python
class BaseTool(ABC):
    name: ClassVar[str]           # 唯一标识符
    description: ClassVar[str]    # LLM 看到的描述
    parameters: ClassVar[dict]    # 参数的 JSON Schema
    risky: ClassVar[bool] = False # 是否需要权限？

    @abstractmethod
    def execute(self, **kwargs) -> str: ...

    def to_function_schema(self) -> dict: ...
```

### ToolRegistry

注册表管理工具实例并生成 schema：

| 方法 | 说明 |
|------|------|
| `register(tool)` | 添加工具（重名时抛出 `ValueError`） |
| `get(name)` | 按名称查找工具 |
| `list_tools()` | 返回所有已注册工具 |
| `filter_by_names(names)` | 按名称列表筛选工具子集 |
| `to_schemas()` | 导出所有工具的 OpenAI 格式函数 schema |
| `to_schemas_filtered(names)` | 导出工具子集的 schema |

### 注册顺序

```python
# 1. 文件类工具（无外部依赖）
registry = create_default_registry()
# → file_read, file_write, file_list, web_fetch

# 2. 需要运行时依赖的工具
registry.register(OcrTool(client=client))
registry.register(ShellTool(permission_callback=...))

# 3. 技能工具（从 YAML 发现）
skills = discover_skills()
register_skill_tools(registry, skills, client)
# → skill_summarize, skill_translate, ...
```

---

## 技能系统

### 技能配置

技能以 YAML 文件定义，结构如下：

```yaml
name: summarize
description: 总结文本文件或文档
model: glm-4-flash
system_prompt: |
  你是一个简洁的摘要助手...
tools:
  - file_read
  - file_write
max_turns: 5
input:
  description: 要总结的文本文件
  args:
    - name: file
      type: file
      required: true
output:
  description: Markdown 摘要
  directory: zhi-output
```

### SkillConfig 数据类

```python
@dataclass
class SkillConfig:
    name: str
    description: str
    system_prompt: str
    tools: list[str]
    model: str = "glm-4-flash"
    max_turns: int = 15
    input_args: list[dict] = field(default_factory=list)
    output_description: str = ""
    output_directory: str = "zhi-output"
    source: str = ""  # "builtin" 或 "user"
```

### 技能发现

技能从两个目录中发现：

1. **内置**：`src/zhi/skills/builtin/*.yaml`（随包分发）
2. **用户**：用户定义的目录（同名时覆盖内置技能）

损坏的 YAML 文件会被跳过并记录警告。

### 组合技能

组合技能将其他技能引用为工具。当技能在 tools 中列出 `analyze` 时，系统将其解析为 `skill_analyze` 并包装为 `SkillTool`：

```yaml
# contract-review.yaml
tools:
  - file_read
  - ocr
  - file_write
  - analyze      # → 解析为 skill_analyze
  - compare      # → 解析为 skill_compare
  - proofread    # → 解析为 skill_proofread
```

### 递归保护

嵌套技能执行有三个安全机制：

| 机制 | 限制 | 行为 |
|------|------|------|
| **循环检测** | 不适用 | 如果技能名称出现在当前调用链中则阻止 |
| **深度限制** | 3 层 | 超过最大深度时阻止执行 |
| **最大轮次** | 每个技能独立 | 每个嵌套层有自己的轮次限制 |

---

## 国际化系统

### 语言前导指令

每个技能提示前都会附加语言前导指令：

> IMPORTANT: Always respond in the same language as the input document. If the document or user input is in Chinese, your ENTIRE output -- including all section headers, table headers, column names, labels, and structural elements -- MUST be in Chinese. Never mix languages in your response.

这确保整个技能链（包括嵌套的组合技能）中输出语言的一致性。

### 字符串目录

界面使用基于键的字符串目录，包含英文和中文翻译：

```python
t("repl.help")           # → 英文或中文帮助文本
t("ui.confirm_rich",     # → "允许 file_write(path)？"
   tool="file_write",
   args="path")
```

### 语言解析

```
显式调用 set_language("zh") → "zh"
                             ↓（如果是 "auto"）
ZHI_LANGUAGE 环境变量 → 检查 "zh" 前缀
                             ↓（未设置）
LANG / LC_ALL 环境变量 → 检查 "zh" 前缀
                             ↓（未设置）
默认 → "en"
```

---

## 安全模型

### 输出隔离

所有文件写入都指向 `zhi-output/`（可配置）。原始文件永远不会被修改。

| 检查项 | 说明 |
|--------|------|
| 仅限相对路径 | 绝对路径被拒绝 |
| 禁止路径遍历 | `..` 路径段被阻止 |
| 符号链接解析 | 解析后的路径必须在输出目录内 |
| 禁止覆盖 | 已存在的文件不能被替换 |

### Shell 安全

三级命令分类：

| 级别 | 示例 | 行为 |
|------|------|------|
| **封锁** | `rm -rf /`、fork 炸弹、`dd` 写设备 | 始终拒绝，无法确认执行 |
| **破坏性** | `rm`、`mv`、`chmod`、`sed -i`、`git reset --hard` | 额外警告 + 确认 |
| **标准** | `ls`、`wc`、`grep` | 标准确认 |

绕过模式（`eval`、`bash -c`、`sh -c`、`/bin/rm`）也被封锁。

### SSRF 防护

`web_fetch` 工具阻止访问：

- `localhost` 和已知元数据端点
- 私有 IP 范围（RFC 1918）
- 回环地址和链路本地地址

### 配置安全

- 配置文件权限：`0o600`（仅所有者可访问）
- API 密钥以纯文本存储（共享系统建议使用 `ZHI_API_KEY` 环境变量）
- 敏感输入不记录到 REPL 历史
