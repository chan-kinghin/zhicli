---
hide:
  - toc
---

# 安装

<div class="install-hero" markdown>

选择你的平台，开始使用 zhi CLI。

</div>

---

## :material-apple: macOS / :material-linux: Linux

需要 **Python 3.10+**，通过 pip 安装：

```bash
pip install zhicli
```

??? tip "没有 Python？"

    === "macOS"

        ```bash
        brew install python@3.11
        ```

        或从 [python.org](https://www.python.org/downloads/) 下载。

    === "Ubuntu / Debian"

        ```bash
        sudo apt update && sudo apt install python3 python3-pip
        ```

    === "Fedora / RHEL"

        ```bash
        sudo dnf install python3 python3-pip
        ```

然后配置：

```bash
zhi --setup     # 输入你的智谱 API Key
zhi             # 开始对话
```

---

## :material-microsoft-windows: Windows

### 方式 A：独立 exe（无需安装 Python）

<a id="windows-download-btn" class="md-button md-button--primary" href="#" onclick="return false;">
:material-download: 下载 Windows 版本
</a>
<span id="windows-download-version" class="install-version"></span>

<noscript>

[从 Releases 下载 :material-open-in-new:](https://github.com/chan-kinghin/zhicli/releases/latest){ .md-button .md-button--primary }

</noscript>

`.exe` 文件已内置 Python —— 下载后放入 PATH 目录，即可运行：

```powershell
zhi --setup
zhi
```

### 方式 B：pip 安装（需要 Python 3.10+）

```powershell
pip install zhicli
zhi --setup
zhi
```

??? tip "Windows 安装 Python"

    从 [python.org](https://www.python.org/downloads/) 下载，安装时**勾选 "Add Python to PATH"**。

---

## :material-package-variant: 验证安装

```bash
zhi --version
```

应看到类似 `zhi 0.1.19` 的输出。

---

## :material-key: 获取 API Key

zhi 需要智谱 AI 的 API Key。前往 [open.bigmodel.cn](https://open.bigmodel.cn/) 免费获取。

```bash
zhi --setup    # 引导式配置 —— 密钥保存在 ~/.config/zhi/config.yaml
```

---

## :material-arrow-up: 升级

```bash
pip install --upgrade zhicli
```

Windows exe 用户请从本页面下载最新版本。

<script>
(function() {
  var btn = document.getElementById('windows-download-btn');
  var ver = document.getElementById('windows-download-version');
  if (!btn) return;
  fetch('https://api.github.com/repos/chan-kinghin/zhicli/releases/latest')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      var exe = (data.assets || []).find(function(a) {
        return a.name.endsWith('.exe');
      });
      if (exe) {
        btn.href = exe.browser_download_url;
        btn.onclick = null;
        ver.textContent = data.tag_name + ' (' + (exe.size / 1048576).toFixed(1) + ' MB)';
      } else {
        btn.href = data.html_url;
        btn.onclick = null;
      }
    })
    .catch(function() {
      btn.href = 'https://github.com/chan-kinghin/zhicli/releases/latest';
      btn.onclick = null;
    });
})();
</script>
