# 配置参考

## 配置文件

zhi 将配置存储在平台特定路径的 YAML 文件中：

| 平台 | 路径 |
|------|------|
| macOS | `~/Library/Application Support/zhi/config.yaml` |
| Linux | `~/.config/zhi/config.yaml` |
| Windows | `%APPDATA%\zhi\config.yaml` |

配置文件由设置向导（`zhi --setup`）自动创建，权限设为 `0o600`（仅所有者可读写）以保护 API 密钥。

---

## 配置字段

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `api_key` | string | `""` | 智谱 API 密钥（所有操作必需） |
| `default_model` | string | `"glm-5"` | 交互对话的默认模型 |
| `skill_model` | string | `"glm-4-flash"` | 技能执行的默认模型 |
| `output_dir` | string | `"zhi-output"` | `file_write` 工具的输出目录 |
| `max_turns` | int | `30` | 每次请求的最大代理循环轮次（范围：1-100） |
| `log_level` | string | `"INFO"` | 日志级别（DEBUG、INFO、WARNING、ERROR、CRITICAL） |
| `language` | string | `"auto"` | 界面语言（`auto`、`en`、`zh`） |

### 示例 config.yaml

```yaml
api_key: "your-zhipu-api-key-here"
default_model: glm-5
skill_model: glm-4-flash
output_dir: zhi-output
max_turns: 30
log_level: INFO
language: auto
```

---

## 环境变量

环境变量覆盖配置文件的值。优先级顺序为：

**环境变量 > 配置文件 > 默认值**

| 变量 | 对应字段 | 示例 |
|------|----------|------|
| `ZHI_API_KEY` | `api_key` | `export ZHI_API_KEY="your-key"` |
| `ZHI_DEFAULT_MODEL` | `default_model` | `export ZHI_DEFAULT_MODEL="glm-4-flash"` |
| `ZHI_OUTPUT_DIR` | `output_dir` | `export ZHI_OUTPUT_DIR="output"` |
| `ZHI_LOG_LEVEL` | `log_level` | `export ZHI_LOG_LEVEL="DEBUG"` |
| `ZHI_LANGUAGE` | `language` | `export ZHI_LANGUAGE="zh"` |
| `NO_COLOR` | （禁用颜色） | `export NO_COLOR=1` |

!!! tip "免配置文件快速启动"
    可以跳过设置向导，直接设置 `ZHI_API_KEY`：
    ```bash
    export ZHI_API_KEY="your-key"
    zhi
    ```

---

## 语言检测

当 `language` 设为 `auto`（默认值）时，zhi 按以下顺序检测界面语言：

1. `ZHI_LANGUAGE` 环境变量
2. `LANG` 或 `LC_ALL` 环境变量（检查 `zh` 前缀）
3. 回退到 `en`（英文）

!!! info "语言前导指令"
    无论界面语言如何设置，所有技能提示都会附加语言前导指令，要求 LLM 以输入文档的语言进行回复。这确保中文文档得到中文回复，英文文档得到英文回复。

---

## 设置向导

运行设置向导进行首次配置或重新配置：

```bash
zhi --setup
```

向导包含三个步骤：

### 第 1 步：API 密钥

粘贴您的智谱 API 密钥（在 [open.bigmodel.cn](https://open.bigmodel.cn) 获取）。

### 第 2 步：默认设置

配置可选项：

| 设置 | 提示 | 默认值 |
|------|------|--------|
| 对话模型 | `对话默认模型 [glm-5]：` | `glm-5` |
| 技能模型 | `技能默认模型 [glm-4-flash]：` | `glm-4-flash` |
| 输出目录 | `输出目录 [zhi-output]：` | `zhi-output` |
| 语言 | `界面语言 [auto]：` | `auto` |

### 第 3 步：快速演示

可选的示例技能演示（按 Enter 或 `y` 尝试，`n` 跳过）。

---

## 验证

加载时，配置会进行验证：

| 检查项 | 行为 |
|--------|------|
| 缺少 API 密钥 | 记录警告，需要 API 的命令将失败 |
| `max_turns` 超出范围（1-100） | 自动修正到有效范围并警告 |
| 未知 `log_level` | 重置为 `INFO` 并警告 |
| 未知配置字段 | 静默忽略 |
| YAML 格式错误 | 回退到默认值并警告 |

---

## 文件权限

配置文件以 `0o600` 权限保存（仅所有者可读写）。如果无法设置权限（例如在 Windows 上），会记录警告：

```
Could not set restrictive permissions on config.yaml. API key may be readable by other users.
```

!!! warning "保护您的 API 密钥"
    配置文件以纯文本存储您的智谱 API 密钥。请确保文件不可被其他用户读取。在共享系统上，使用 `ZHI_API_KEY` 环境变量是更安全的选择。
