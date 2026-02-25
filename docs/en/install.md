---
hide:
  - toc
---

# Install

<div class="install-hero" markdown>

Choose your platform to get started with zhi CLI.

</div>

---

## :material-apple: macOS / :material-linux: Linux

Requires **Python 3.10+**. Install via pip:

```bash
pip install zhicli
```

??? tip "Don't have Python?"

    === "macOS"

        ```bash
        brew install python@3.11
        ```

        Or download from [python.org](https://www.python.org/downloads/).

    === "Ubuntu / Debian"

        ```bash
        sudo apt update && sudo apt install python3 python3-pip
        ```

    === "Fedora / RHEL"

        ```bash
        sudo dnf install python3 python3-pip
        ```

Then configure:

```bash
zhi --setup     # Enter your Zhipu API key
zhi             # Start chatting
```

---

## :material-microsoft-windows: Windows

### Option A: Standalone exe (no Python needed)

<a id="windows-download-btn" class="md-button md-button--primary" href="#" onclick="return false;">
:material-download: Download for Windows
</a>
<span id="windows-download-version" class="install-version"></span>

<noscript>

[Download from Releases :material-open-in-new:](https://github.com/chan-kinghin/zhicli/releases/latest){ .md-button .md-button--primary }

</noscript>

The `.exe` bundles Python — just download, place it in your PATH, and run:

```powershell
zhi --setup
zhi
```

### Option B: pip install (requires Python 3.10+)

```powershell
pip install zhicli
zhi --setup
zhi
```

??? tip "Installing Python on Windows"

    Download from [python.org](https://www.python.org/downloads/) and **check "Add Python to PATH"** during installation.

---

## :material-package-variant: Verify Installation

```bash
zhi --version
```

You should see output like `zhi 0.1.19`.

---

## :material-key: Get an API Key

zhi requires a Zhipu AI API key. Get one free at [open.bigmodel.cn](https://open.bigmodel.cn/).

```bash
zhi --setup    # Guided setup — stores key in ~/.config/zhi/config.yaml
```

---

## :material-arrow-up: Upgrade

```bash
pip install --upgrade zhicli
```

For the Windows exe, download the latest version from this page.

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
