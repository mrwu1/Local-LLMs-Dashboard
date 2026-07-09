# Local AI Core & Dashboard Manager (Mac & Multi-Platform)

这是一个专为 macOS (Apple Silicon M-Series) 深度优化的本地大模型（LLM）控制中心与容器网格管理面板。它能将本地部署的多套推理引擎集成在一个美观、流畅的毛玻璃微透 UI 中，并提供实时的系统监控、大模型安全限额卫士、一键调试、以及 Hugging Face 动态发现与自动下载拉取功能。

---

## 🏗️ 架构组成与引擎支持

本系统统一调度并接管了以下本地服务：

1. **🦙 Ollama 引擎 (Port 11434)**
   * 用于拉取并运行本地轻量级通用 GGUF 格式大模型与向量嵌入模型（如 BGE-M3）。
2. **🚀 MLX 引擎 (Port 8080)**
   * 苹果官方专为 Apple Silicon GPU/Metal 优化的本地推理引擎，专治高性能编程与长文本模型（如 Qwen2.5-Coder-7B）。
3. **⚙️ llama.cpp 引擎 (Port 8090)**
   * 原生极简 C/C++ 推理运行时，免 Python 依赖，直接与 Ollama 共享下载的模型文件。
4. **⚡ LiteRT 运行时 (Port 4010)**
   * 谷歌高性能端侧多模态轻量引擎（前身 TensorFlow Lite），专用于离线图片理解。
5. **🐳 Open WebUI 容器 (Port 3000)**
   * 本地沙盒虚拟化运行的 Web UI，挂载系统网格提供一致性的聊天与知识库存储。

---

## ✨ 核心亮点功能

### 1. 🛡️ 物理显存红线卫士 (Safe Safeguard)
* 针对 16GB 内存机型设计，实时计算活跃模型的显存占用总和。
* 若显存使用逼近系统红线（11.0GB - 11.5GB），启动新模型时会自动弹出警告或拦截，防止物理显存耗尽导致系统严重卡顿。
* 提供一键释放全部显存的 **「一键退烧药 (Cooldown)」** 按钮，秒级释放物理内存。

### 2. 🔍 Hugging Face 趋势发现与三维画像
* **智能适性评分**：根据模型参数大小与量化位宽，动态标记其运行体感：
  * 🟢 完美流畅 ($\le 6\text{GB}$ 显存占)
  * 🟡 较吃力 ($6\text{GB} \sim 10\text{GB}$ 显存占)
  * 🔴 硬件超限 ($> 10\text{GB}$ 显存占，前端按钮自动置灰拦截)
* **高维技术透视**：在卡片中清晰呈现：
  * **💿 文件格式**：MLX (Safetensors)、GGUF (Unified)、LiteRT (TFLite)。
  * **🔩 量化规格**：`4-bit (Q4_K_M)`、`8-bit (MXFP8)` 等精确格式。
  * **📖 上下文窗口**：提示最大上下文（如 `128K`, `8K`），预防文本超限。
  * **📈 满载增幅**：精准预估长文本拉满时，KV Cache 额外膨胀的物理显存。
  * **🚀 估计生成速度**：基于 M5 芯片算力估算实际打字机速度（如 `~45 t/s`）。
  * **🔒 审核门槛**：标记 `🔒 需协议授权`，预防受限仓储（Gated）静默下载失败。

### 3. 📥 后台多引擎静默下载与自动导入
* Ollama、MLX 支持在控制面板后台拉起静默下载进程。
* **LiteRT 自动解析器**：对于 LiteRT 模型，只需粘贴 Hugging Face 仓储 ID，后端会自动通过 API 获取列表、智能挑选最合适的 GPU/INT4 模型包（如 `gemma-2b-it-gpu-int4.bin`）并执行 `litert-lm import` 导入。

---

## 💻 平台兼容性指南

### 1. macOS (推荐 Apple Silicon M1 - M5)
* **完全原生支持**。
* MLX 与 LiteRT 支持完整的 GPU/NPU 硬件加速。
* 后台采用 macOS 自带的 `screen` 终端会话管理器静默控制下载。

### 2. Windows 平台
* **部分兼容（降级模式运行）**：
  * **Ollama & llama.cpp**：完全支持。
  * **MLX 引擎**：**不支持**（MLX 为 macOS 独占）。
  * **LiteRT 引擎**：支持编译安装，但可能需修改启动脚本路径。
  * **后台启动挂载**：Windows 下没有 `screen` 命令，需要将代码中 `services.py` 里的 `screen -dmS` 脚本启动方式替换为 Windows 后台 `start /B` 命令，或在 **WSL (Windows Subsystem for Linux)** 容器下运行。
  * **进程检测**：本系统使用 `psutil` 跨平台库进行端口与进程解析，状态检测在 Windows 下依然有效。

---

## 🚀 快速启动说明

### 准备工作
确保本地已安装 Python 3.10+。如果是 Mac 电脑，推荐安装 `uv` 包管理器。

1. **克隆项目**
   ```bash
   git clone <your-repo-url>
   cd Monthly-Sharing-Session/local-ai-dashboard
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   # 或使用 uv:
   uv pip install -r requirements.txt
   ```
   *(如果不存在 requirements.txt，安装: `fastapi uvicorn psutil` 即可)*

3. **启动面板**
   ```bash
   python3 src/main.py
   ```

4. **访问面板**
   打开浏览器访问：`http://127.0.0.1:8123`

---

## 🔒 开源协议与声明
本项目以 MIT 协议开源。部分引擎运行（如 LiteRT）依赖于外部 Google TFLite Runtime 与 Apple MLX Framework，使用模型时请严格遵守各厂商（Google Gemma License, Meta Llama License）的开源使用协议。
