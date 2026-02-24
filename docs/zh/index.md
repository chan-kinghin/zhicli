---
hide:
  - navigation
  - toc
---

<div class="hero-section" markdown>

<div class="zhi-logo" markdown>

<pre>
            ·        ✦
           ╱╲
         ╱━━━━╲
        ╱──────╲
      ╱━━━━━━━━━━╲
     ╱────────────╲
   ╱╱╱    ▐▌    ╲╲╲
  ╱╱╱  ━━━━━━━  ╲╲╲
</pre>

</div>

# zhi CLI

**由智谱 GLM 大模型驱动的终端 AI 助手**

zhi 是一个开源命令行工具，将智谱 GLM 大模型带入你的终端。它将智能对话与强大的技能系统相结合，支持文档处理、OCR 识别和自动化工作流 —— 并内置安全防护机制。

[开始使用 :material-arrow-right:](tutorials.md){ .md-button .md-button--primary }
[在 GitHub 上查看 :material-github:](https://github.com/chan-kinghin/zhicli){ .md-button }

</div>

---

## 功能特性

<div class="grid cards" markdown>

- :material-brain: **双模型架构**

    GLM-5 用于智能对话，GLM-4-flash 用于高性价比的技能执行（成本约为前者的 10%）

- :material-tools: **15 个内置技能**

    9 个单一用途技能 + 6 个组合工作流，覆盖文档处理、翻译、OCR 等场景

- :material-file-document: **7 个集成工具**

    文件读写、OCR 识别、Shell 执行、网页抓取、技能创建等

- :material-cog: **YAML 技能系统**

    使用简单的 YAML 配置，几分钟内即可创建自定义自动化技能

- :material-translate: **中英双语支持**

    完整的中英文界面，自动检测语言偏好

- :material-shield-check: **安全优先**

    架构中不存在删除能力 —— 你的文件永远不会被移除或覆盖。所有输出隔离至 zhi-output/ 目录，配合路径遍历防护与 Shell 命令确认机制

</div>

---

## 快速开始

```bash
# 安装
pip install zhicli

# 配置（30 秒完成）
zhi --setup

# 开始对话
zhi
```
