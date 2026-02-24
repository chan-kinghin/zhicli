# Comparison

How does zhi compare to other terminal AI tools? This page provides a factual comparison across key dimensions.

## Feature Matrix

| Feature | zhi | aider | Claude Code | GitHub Copilot CLI | Gemini CLI | shell-gpt | Qwen Code |
|---------|-----|-------|-------------|-------------------|------------|-----------|-----------|
| **Installation** | pip | pip | npm | gh extension | npm | pip | pip |
| **Setup time** | ~30s (1 API key) | ~2 min | ~1 min | GitHub login | Google auth | ~1 min | ~1 min |
| **Primary use** | Terminal AI + document processing | AI pair programming | Code agent | Shell suggestions | Code + terminal | Shell AI | Code agent |
| **LLM provider** | Zhipu GLM (Chinese) | OpenAI, Anthropic, etc. | Anthropic Claude | OpenAI / Anthropic / Google | Google Gemini | Various via OpenAI API | Alibaba Qwen |
| **File access** | Read + write + OCR (isolated output) | Read + edit (in-place) | Read + edit (in-place) | None | Read + edit | None | Read + edit |
| **Skill system** | 15 YAML skills + custom | None | Slash commands | None | None | None | None |
| **Cost model** | Dual-model (flash for skills, ~10% cost) | Single model | Single model + subscription | Subscription | Free tier + paid | Single model | Free |
| **Chinese LLM** | Native (GLM-5 / GLM-4-flash) | No | No | No | No | No | Native (Qwen) |
| **Output safety** | Isolated output dir, shell confirmation | In-place file editing | Sandbox + approval | N/A | In-place editing | N/A | In-place editing |

---

## Detailed Comparison

### vs aider

**aider** is an AI pair programming tool focused on code editing within git repositories.

| Aspect | zhi | aider |
|--------|-----|-------|
| Focus | Document processing + general terminal AI | Code editing in git repos |
| File editing | Writes to isolated `zhi-output/` directory | Edits files in-place, auto-commits |
| OCR | Built-in (PDF, images via Zhipu API) | No |
| Skills | 15 reusable YAML workflows | No equivalent |
| LLM | Zhipu GLM (optimized for Chinese) | Multi-provider (OpenAI, Anthropic, etc.) |
| Git integration | Via shell tool | Deep git integration |

**Choose zhi** for document processing, Chinese language tasks, and reusable workflows.
**Choose aider** for AI-assisted code editing with git integration.

### vs Claude Code

**Claude Code** is Anthropic's official CLI agent powered by Claude models.

| Aspect | zhi | Claude Code |
|--------|-----|-------------|
| Focus | Document processing + Chinese LLM | Code agent + general development |
| LLM | Zhipu GLM | Anthropic Claude |
| Cost | Dual-model (~10% cost for skills via flash) | Single model pricing |
| Skills | 15 YAML + composable | Slash commands (not composable) |
| File safety | Isolated output directory | Sandbox with approval prompts |
| Chinese | Native GLM support | English-focused |

**Choose zhi** for Chinese document workflows and cost-efficient batch processing.
**Choose Claude Code** for code-heavy development tasks with Claude's reasoning.

### vs GitHub Copilot CLI

**GitHub Copilot CLI** suggests shell commands and explains terminal output.

| Aspect | zhi | GitHub Copilot CLI |
|--------|-----|-------------------|
| Focus | Full agentic loop with tools | Shell command suggestions |
| File access | Read, write, OCR | None |
| Autonomy | Multi-turn agent with tool calls | Single suggestion |
| Skills | 15 reusable workflows | None |
| Pricing | Pay-per-token (Zhipu) | GitHub subscription |

**Choose zhi** for complex multi-step tasks.
**Choose Copilot CLI** for quick shell command suggestions.

### vs Gemini CLI

**Gemini CLI** is Google's terminal AI tool powered by Gemini models.

| Aspect | zhi | Gemini CLI |
|--------|-----|------------|
| Focus | Document processing + Chinese LLM | Code + general terminal |
| LLM | Zhipu GLM | Google Gemini |
| File editing | Isolated output | In-place |
| Skills | 15 YAML + composable | None |
| Pricing | Pay-per-token | Free tier available |

### vs shell-gpt

**shell-gpt** is a lightweight CLI for AI-powered shell commands.

| Aspect | zhi | shell-gpt |
|--------|-----|-----------|
| Agent loop | Multi-turn with tools | Single-turn |
| File access | Read + write + OCR | None |
| Skills | 15 reusable workflows | None |
| Shell safety | Blocked/warned/allowed tiers | Basic |

### vs Qwen Code

**Qwen Code** is Alibaba's code agent powered by Qwen models.

| Aspect | zhi | Qwen Code |
|--------|-----|-----------|
| Focus | Document processing | Code editing |
| Chinese LLM | Zhipu GLM | Alibaba Qwen |
| File editing | Isolated output | In-place |
| Skills | 15 YAML + composable | None |
| Pricing | Pay-per-token | Free |

---

## What Makes zhi Unique

### Native Chinese LLM + Document Processing

zhi is the only terminal AI tool that combines a native Chinese LLM (Zhipu GLM) with a full document processing pipeline including OCR, table extraction, and format conversion. This makes it ideal for Chinese-language office workflows.

### Dual-Model Architecture

zhi uses two models strategically:

- **GLM-5** (premium) for interactive chat -- intelligent, nuanced responses
- **GLM-4-flash** (economy) for skill execution -- fast, cost-effective (~10% the cost)

This means batch operations like summarizing 50 documents cost a fraction of what a single-model approach would.

### YAML Skill System

Skills are composable YAML configurations, not hardcoded features. You can:

- Create custom skills without writing code
- Compose skills together (e.g., `contract-review` uses `analyze` + `compare` + `proofread`)
- Share skills as `.yaml` files

### Safety by Design

zhi cannot delete your files — not because of a setting you might forget to enable, but because **no delete capability exists in the architecture**. There is no delete tool, no overwrite mode, and no way for the AI to remove or modify your original files. Safety is enforced in code, not in prompts — so it cannot be lost during context compression or ignored by the model.

This is a deliberate design choice: AI agents should never be able to cause irreversible damage to your data.

### Output Isolation

Unlike tools that edit files in-place, zhi writes all output to an isolated `zhi-output/` directory. Your original files are never modified, making it safe to experiment without risk.
