# CLI 参考

## 命令行用法

```
zhi                        # 交互式 REPL
zhi -c "消息"              # 单次消息模式
zhi run <技能> [文件]       # 运行技能
zhi --setup                # 配置向导
zhi --version              # 显示版本
zhi --debug                # 启用调试日志
zhi --no-color             # 禁用彩色输出
zhi --language <LANG>      # 设置界面语言（auto、en、zh）
```

## 模式

### 交互式 REPL

直接运行 `zhi` 启动 REPL：

```bash
zhi
```

功能特性：

- 持久化命令历史（保存到 `~/.config/zhi/history.txt`）
- 斜杠命令、模型名称和技能名称的 Tab 补全
- 使用 `\` 续行的多行输入
- 通过 prompt_toolkit 支持 CJK/输入法
- 包含敏感词（`api_key`、`password`、`token`、`secret`）的输入不会被记录到历史

### 单次消息模式

发送单条消息后退出：

```bash
zhi -c "当前目录有哪些文件？"
```

### 技能运行模式

运行指定技能并可选传入文件：

```bash
zhi run summarize report.txt
zhi run compare v1.md v2.md
zhi run extract-table invoices/receipt.pdf
```

### 管道模式

从标准输入读取文本：

```bash
echo "翻译这段文字为英文" | zhi
cat document.txt | zhi -c "总结这篇文档"
git log --oneline -20 | zhi -c "总结最近的更改"
```

!!! info "管道检测"
    zhi 会自动检测标准输入是否为终端，非终端时自动从中读取。

---

## 斜杠命令

REPL 支持 14 个斜杠命令来控制会话：

| 命令 | 说明 | 示例 |
|------|------|------|
| `/help` | 显示可用命令和提示 | `/help` |
| `/auto` | 切换到自动模式（跳过工具确认） | `/auto` |
| `/approve` | 切换到确认模式（执行风险工具前确认） | `/approve` |
| `/model <名称>` | 切换当前会话的 LLM 模型 | `/model glm-4-flash` |
| `/think` | 启用思考模式（扩展推理） | `/think` |
| `/fast` | 关闭思考模式（更快响应） | `/fast` |
| `/run <技能> [文件]` | 运行技能并可选传入文件 | `/run summarize report.txt` |
| `/skill list` | 列出所有可用技能 | `/skill list` |
| `/skill show <名称>` | 显示指定技能的详情 | `/skill show analyze` |
| `/status` | 显示当前会话状态 | `/status` |
| `/reset` | 清除对话历史（需确认） | `/reset` |
| `/undo` | 撤销最后一轮用户消息和 AI 回复 | `/undo` |
| `/usage` | 显示 token 使用统计 | `/usage` |
| `/verbose` | 切换详细输出 | `/verbose` |
| `/exit` | 退出 zhi（如有消耗显示使用统计） | `/exit` |

### 权限模式

| 模式 | 行为 | 切换命令 |
|------|------|----------|
| **approve**（默认） | 执行风险工具前确认（`file_write`、`shell`、`skill_create`） | `/approve` |
| **auto** | 跳过风险工具确认（shell 仍然始终确认） | `/auto` |

!!! warning "Shell 始终需要确认"
    `shell` 工具无论权限模式如何都需要确认。这是一项无法绕过的安全措施。

### 模型切换

可用模型：

| 模型 | 层级 | 思考模式 | 工具调用 |
|------|------|----------|----------|
| `glm-5` | 高级 | 支持 | 支持 |
| `glm-4-flash` | 经济 | 不支持 | 支持 |
| `glm-4-air` | 经济 | 不支持 | 支持 |

```
zhi> /model glm-4-flash
已切换到模型 glm-4-flash
```

### 状态显示

```
zhi> /status
模型：glm-5 | 模式：approve | 思考：开 | 详细：关 | 轮次：3 | Token：1523
```

---

## 全局选项

| 选项 | 说明 |
|------|------|
| `--version` | 打印版本号并退出 |
| `--setup` | 运行首次配置向导 |
| `--debug` | 设置日志级别为 DEBUG（显示 API 调用、工具执行详情） |
| `--no-color` | 禁用 Rich 格式和颜色（也遵循 `NO_COLOR` 环境变量） |
| `--language LANG` | 设置界面语言（`auto`、`en`、`zh`），覆盖配置文件设置 |
| `-c MESSAGE` | 单次模式：发送一条消息，打印回复后退出 |

---

## 退出

使用以下任一方式退出 REPL：

- `/exit` 命令
- `Ctrl+D`（EOF）
- `Ctrl+C` 取消当前输入但不退出

退出时，如果有 token 消耗，zhi 会显示会话 token 使用量。
