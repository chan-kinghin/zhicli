---
hide:
  - navigation
  - toc
---

# zhi CLI

**Terminal AI assistant powered by Chinese LLMs**

zhi is an open-source command-line tool that brings Zhipu GLM models to your terminal. It combines intelligent chat with a powerful skill system for document processing, OCR, and automation — all with built-in safety guardrails.

---

## Features

<div class="grid cards" markdown>

- :material-brain: **Dual Model Architecture**

    GLM-5 for intelligent chat, GLM-4-flash for cost-effective skill execution (~10% the cost)

- :material-tools: **15 Built-in Skills**

    9 single-purpose + 6 composite workflows for documents, translation, OCR, and more

- :material-file-document: **7 Integrated Tools**

    File read/write, OCR, shell execution, web fetch, and skill creation

- :material-cog: **YAML Skill System**

    Create custom automation skills in minutes with simple YAML configuration

- :material-translate: **Bilingual Support**

    Full English and Chinese UI with automatic language detection

- :material-shield-check: **Security First**

    Output isolation to zhi-output/, path traversal protection, shell command confirmation

</div>

---

## Quick Start

```bash
# Install
pip install zhicli

# Configure (30 seconds)
zhi --setup

# Start chatting
zhi
```

[Get Started :material-arrow-right:](en/tutorials.md){ .md-button .md-button--primary }
[View on GitHub :material-github:](https://github.com/chan-kinghin/zhicli){ .md-button }
