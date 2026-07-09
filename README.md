<div align="center">

# 🖥️ Local LLMs Dashboard

**Language / 语言 / 言語:**
[🇺🇸 English](#english) | [🇨🇳 简体中文](#简体中文) | [🇯🇵 日本語](#日本語)

</div>

---

<a name="english"></a>
## 🇺🇸 English

### Overview

A local LLM (Large Language Model) control center and inference engine manager, deeply optimized for **macOS Apple Silicon (M-Series)**. It unifies multiple local inference backends under one sleek glassmorphism UI, offering real-time system monitoring, VRAM safety guardrails, one-click model management, and live model discovery powered by the Hugging Face API.

---

### 🏗️ Architecture & Supported Engines

| Engine | Port | Description |
|--------|------|-------------|
| 🦙 Ollama | 11434 | Pull and run lightweight GGUF models (e.g. BGE-M3 for embeddings) |
| 🚀 MLX | 8080 | Apple-official Metal/GPU-optimized inference (e.g. Qwen2.5-Coder-7B) |
| ⚙️ llama.cpp | 8090 | Native C/C++ runtime, no Python required, shares Ollama model files |
| ⚡ LiteRT | 4010 | Google's on-device multimodal engine (formerly TensorFlow Lite) |
| 🐳 Open WebUI | 3000 | Sandboxed containerized chat UI with persistent knowledge base |

---

### ✨ Key Features

#### 1. 🛡️ VRAM Safety Guardrail
- Designed for 16GB unified memory Macs, continuously tracks total VRAM usage.
- Blocks new model launches if total VRAM approaches the 11.5GB system limit.
- One-click **Cooldown** button to instantly release all GPU memory.

#### 2. 🔍 Hugging Face Live Model Discovery
- Dynamically fetches trending models from Hugging Face API, filtered by engine type.
- Each model card displays a full hardware-suitability profile:
  - 🟢 Smooth / 🟡 Heavy / 🔴 Exceeds hardware limit
  - 💿 Format · 🔩 Quantization · 📊 Parameter size · ⚖️ License
  - 🔓 Open pull / 🔒 Gated (requires HF token)
  - 📖 Context window · 🚀 Estimated speed · 📦 Download size · 📈 KV Cache overhead

#### 3. 📥 Background Silent Download & Auto Import
- Ollama and MLX support background download sessions.
- **LiteRT Auto-resolver**: Paste a Hugging Face repo ID — the backend automatically fetches the file list, selects the best GPU/INT4 binary (e.g. `gemma-2b-it-gpu-int4.bin`), and runs `litert-lm import`.

---

### 💻 Platform Compatibility

| Platform | Ollama | MLX | LiteRT | llama.cpp |
|----------|--------|-----|--------|-----------|
| macOS (Apple Silicon) | ✅ Full | ✅ Full | ✅ Full | ✅ Full |
| macOS (Intel) | ✅ | ❌ | ⚠️ Partial | ✅ |
| Windows (WSL) | ✅ | ❌ | ⚠️ Partial | ✅ |
| Linux | ✅ | ❌ | ⚠️ Partial | ✅ |

> **Note for Windows users**: The backend uses macOS `screen` for background session management. On Windows, either use WSL or replace `screen -dmS` commands in `services.py` with `start /B`.

---

### 🚀 Quick Start

**Requirements**: Python 3.10+

```bash
# 1. Clone the repository
git clone https://github.com/mrwu1/Local-LLMs-Dashboard.git
cd Local-LLMs-Dashboard

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the dashboard
python3 src/main.py

# 4. Open in browser
# http://127.0.0.1:8123
```

---

### 🔒 License
MIT License. Models served may be subject to their own licenses (Google Gemma License, Meta Llama License, etc.). Please review and comply with each model's terms of use.

---

<a name="简体中文"></a>
## 🇨🇳 简体中文

### 项目简介

这是一个专为 **macOS Apple Silicon（M 系列芯片）** 深度优化的本地大模型（LLM）控制中心与推理引擎管理面板。它能将本地部署的多套推理引擎统一集成在一个美观、流畅的毛玻璃微透 UI 中，并提供实时系统监控、大模型安全显存卫士、一键模型管理，以及由 Hugging Face API 驱动的动态模型发现功能。

---

### 🏗️ 架构组成与引擎支持

| 引擎 | 端口 | 描述 |
|------|------|------|
| 🦙 Ollama | 11434 | 拉取并运行轻量级 GGUF 格式大模型与向量嵌入模型（如 BGE-M3） |
| 🚀 MLX | 8080 | 苹果官方 Metal/GPU 优化推理引擎（如 Qwen2.5-Coder-7B） |
| ⚙️ llama.cpp | 8090 | 原生 C/C++ 推理运行时，免 Python 依赖，与 Ollama 共享模型文件 |
| ⚡ LiteRT | 4010 | 谷歌高性能端侧多模态轻量引擎（前身 TensorFlow Lite） |
| 🐳 Open WebUI | 3000 | 本地容器化聊天 Web UI，支持知识库持久存储 |

---

### ✨ 核心亮点功能

#### 1. 🛡️ 物理显存红线卫士
- 针对 16GB 统一内存机型设计，实时追踪活跃模型显存总占用。
- 若总显存逼近系统红线（11.5GB），自动拦截新模型的启动请求。
- 提供一键 **「退烧药 (Cooldown)」** 按钮，秒级释放全部 GPU 显存。

#### 2. 🔍 Hugging Face 动态模型发现
- 实时从 Hugging Face API 拉取热门模型列表，按引擎类型自动筛选。
- 每个模型卡片展示完整的硬件适配画像：
  - 🟢 完美流畅 / 🟡 较吃力 / 🔴 硬件超限
  - 💿 文件格式 · 🔩 量化规格 · 📊 参数量 · ⚖️ 开源协议
  - 🔓 开源直拉 / 🔒 需协议授权（Gated，需配置 HF Token）
  - 📖 上下文窗口 · 🚀 估计生成速度 · 📦 预计下载大小 · 📈 满载显存增幅

#### 3. 📥 后台多引擎静默下载与自动导入
- Ollama 与 MLX 均支持后台静默下载会话。
- **LiteRT 自动解析器**：只需粘贴 Hugging Face 仓储 ID，后端自动通过 API 获取文件列表，智能挑选最合适的 GPU/INT4 模型包（如 `gemma-2b-it-gpu-int4.bin`），并执行 `litert-lm import` 一键导入。

---

### 💻 平台兼容性

| 平台 | Ollama | MLX | LiteRT | llama.cpp |
|------|--------|-----|--------|-----------|
| macOS（Apple Silicon） | ✅ 完全支持 | ✅ 完全支持 | ✅ 完全支持 | ✅ 完全支持 |
| macOS（Intel） | ✅ | ❌ | ⚠️ 部分支持 | ✅ |
| Windows（WSL） | ✅ | ❌ | ⚠️ 部分支持 | ✅ |
| Linux | ✅ | ❌ | ⚠️ 部分支持 | ✅ |

> **Windows 用户注意**：后台进程管理使用了 macOS 的 `screen` 命令。在 Windows 上请使用 WSL 运行，或将 `services.py` 中的 `screen -dmS` 替换为 `start /B` 命令。

---

### 🚀 快速启动

**环境要求**：Python 3.10+

```bash
# 1. 克隆项目
git clone https://github.com/mrwu1/Local-LLMs-Dashboard.git
cd Local-LLMs-Dashboard

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动面板
python3 src/main.py

# 4. 浏览器访问
# http://127.0.0.1:8123
```

---

### 🔒 开源协议与声明
本项目以 **MIT 协议**开源。部分推理引擎及模型（如 LiteRT、MLX）依赖外部框架，使用各模型时请严格遵守对应厂商的开源许可协议（如 Google Gemma License、Meta Llama License）。

---

<a name="日本語"></a>
## 🇯🇵 日本語

### 概要

**macOS Apple Silicon（Mシリーズチップ）** に深く最適化されたローカル大規模言語モデル（LLM）制御センター・推論エンジン管理パネルです。複数のローカル推論バックエンドを美しいグラスモーフィズム UI に統合し、リアルタイムのシステム監視、VRAMセーフガード、ワンクリックモデル管理、Hugging Face APIによるライブモデル発見機能を提供します。

---

### 🏗️ アーキテクチャと対応エンジン

| エンジン | ポート | 説明 |
|----------|--------|------|
| 🦙 Ollama | 11434 | 軽量GGUFモデル・埋め込みモデルの実行（例：BGE-M3） |
| 🚀 MLX | 8080 | Apple公式のMetal/GPU最適化推論エンジン（例：Qwen2.5-Coder-7B） |
| ⚙️ llama.cpp | 8090 | Python不要のネイティブC/C++ランタイム、Ollamaとモデル共有可能 |
| ⚡ LiteRT | 4010 | Googleの高性能エッジ向けマルチモーダルエンジン（旧TensorFlow Lite） |
| 🐳 Open WebUI | 3000 | コンテナ化されたローカルチャットUI、永続的なナレッジベース対応 |

---

### ✨ 主要機能

#### 1. 🛡️ VRAMセーフガード
- 16GB統合メモリのMac向けに設計。アクティブなモデルのVRAM使用量をリアルタイム追跡。
- 合計VRAMがシステム限界（11.5GB）に近づくと、新しいモデルの起動を自動ブロック。
- ワンクリック**クールダウン**ボタンでGPUメモリを即時解放。

#### 2. 🔍 Hugging Faceライブモデル発見
- Hugging Face APIからトレンドモデルをリアルタイム取得し、エンジン別にフィルタリング。
- 各モデルカードにハードウェア適合プロファイルを表示：
  - 🟢 快適動作 / 🟡 やや重い / 🔴 ハードウェア超過
  - 💿 フォーマット · 🔩 量化 · 📊 パラメータ数 · ⚖️ ライセンス
  - 🔓 直接ダウンロード / 🔒 要認証（HF Token設定が必要）
  - 📖 コンテキスト長 · 🚀 推定生成速度 · 📦 ダウンロードサイズ · 📈 KVキャッシュ増加量

#### 3. 📥 バックグラウンドダウンロード・自動インポート
- OllamaとMLXはバックグラウンドサイレントダウンロードに対応。
- **LiteRT自動リゾルバー**：Hugging Faceのリポジトリ IDを貼り付けるだけで、バックエンドが自動的にファイルリストを取得し、最適なGPU/INT4バイナリを選択して `litert-lm import` を実行。

---

### 💻 プラットフォーム互換性

| プラットフォーム | Ollama | MLX | LiteRT | llama.cpp |
|------------------|--------|-----|--------|-----------|
| macOS（Apple Silicon） | ✅ 完全対応 | ✅ 完全対応 | ✅ 完全対応 | ✅ 完全対応 |
| macOS（Intel） | ✅ | ❌ | ⚠️ 部分対応 | ✅ |
| Windows（WSL） | ✅ | ❌ | ⚠️ 部分対応 | ✅ |
| Linux | ✅ | ❌ | ⚠️ 部分対応 | ✅ |

> **Windowsユーザーへの注意**：バックグラウンド管理にmacOSの`screen`コマンドを使用しています。WindowsではWSLを使用するか、`services.py`内の`screen -dmS`を`start /B`コマンドに置き換えてください。

---

### 🚀 クイックスタート

**必要環境**：Python 3.10以上

```bash
# 1. リポジトリのクローン
git clone https://github.com/mrwu1/Local-LLMs-Dashboard.git
cd Local-LLMs-Dashboard

# 2. 依存パッケージのインストール
pip install -r requirements.txt

# 3. ダッシュボードの起動
python3 src/main.py

# 4. ブラウザでアクセス
# http://127.0.0.1:8123
```

---

### 🔒 ライセンス
MITライセンスで公開しています。使用するモデルはそれぞれ独自のライセンス（Google Gemma License、Meta Llama Licenseなど）に従う場合があります。各モデルの利用規約をご確認ください。
