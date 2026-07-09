from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import services
import os

app = FastAPI(title="Local AI Manager Console")

# Serve UI static folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
def read_root():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            return f.read()
    return """
    <html>
        <head><title>Local AI Manager Console</title></head>
        <body style="font-family: sans-serif; background: #121214; color: #fff; text-align: center; padding-top: 100px;">
            <h1>Local AI Dashboard Backend</h1>
            <p>UI is still initializing. Please create index.html in the static folder.</p>
        </body>
    </html>
    """

@app.get("/api/status")
def get_all_status():
    status_data = {}
    for key in services.SERVICES.keys():
        status_data[key] = services.get_service_status(key)
        
    metrics = services.get_system_metrics()
    
    return {
        "services": status_data,
        "metrics": metrics,
        "mlx_models": services.get_installed_mlx_models(),
        "gguf_models": services.get_installed_gguf_models(),
        "litert_models": services.get_installed_litert_models()
    }

@app.post("/api/start")
def start_service_endpoint(service: str, model: str = Query(None)):
    if service not in services.SERVICES:
        raise HTTPException(status_code=400, detail="Invalid service key")
        
    # Check RAM safeguard limit
    metrics = services.get_system_metrics()
    current_vram = metrics["vram"]["allocated_gb"]
    
    # Calculate additional VRAM needed
    added_vram = 0.0
    
    # Check if starting MLX and which model
    if service == "mlx":
        if not model:
            installed = services.get_installed_mlx_models()
            model_key = installed[0]["key"] if installed else "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
        else:
            model_key = model
        added_vram = services.estimate_vram_gb(model_key)
    elif service == "llama_cpp":
        if not model:
            installed = services.get_installed_gguf_models()
            model_key = installed[0]["key"] if (installed and installed[0]["key"]) else ""
        else:
            model_key = model
        
        # Resolve blob path to model tag for VRAM estimation
        model_tag = "llama3.2:3b"
        if model_key:
            gguf_models = services.get_installed_gguf_models()
            for m in gguf_models:
                if m["key"] == model_key:
                    model_tag = m["model_tag"]
                    break
        added_vram = services.estimate_vram_gb(model_tag)
    elif service == "litert":
        added_vram = services.estimate_vram_gb("litert-gemma4")
    elif service == "ollama":
        added_vram = 2.5
        
    if current_vram + added_vram > 11.0: # Safeguard boundary (11GB out of 16GB)
        # Let's see if we are starting a service that is already running, which wouldn't add VRAM
        service_status = services.get_service_status(service)
        if service_status["status"] != "running":
            raise HTTPException(
                status_code=400,
                detail=f"【内存红线预警】当前已分配 {current_vram}GB 显存，启动新服务需追加 {added_vram}GB。这超出了 Mac 16GB 的安全分配上限 (11GB)，可能引发死机崩溃。请先手动关闭其他大模型服务以释放显存。"
            )
            
    success = services.start_service(service, model)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to start service {service}")
    return {"status": "ok", "message": f"{service} started successfully"}

@app.post("/api/stop")
def stop_service_endpoint(service: str):
    if service not in services.SERVICES:
        raise HTTPException(status_code=400, detail="Invalid service key")
    success = services.stop_service(service)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to stop service {service}")
    return {"status": "ok", "message": f"{service} stopped successfully"}

@app.post("/api/cooldown")
def cooldown_endpoint():
    services.cool_down_mac()
    return {"status": "ok", "message": "All AI processes stopped. Mac cooled down successfully!"}

@app.get("/api/logs/{service}")
def get_service_logs_endpoint(service: str, lines: int = 50):
    if service not in services.SERVICES:
        raise HTTPException(status_code=400, detail="Invalid service key")
    logs = services.get_service_logs(service, lines)
    return {"service": service, "logs": logs}

@app.get("/api/diagnose")
def diagnose_network():
    metrics = services.get_system_metrics()
    bridge100_ok = metrics["bridge100_ok"]
    
    # Check if local proxy TUN mode is listening
    tun_warning = False
    clash_ports = [7890, 7897, 9090, 7893]
    active_clash_port = None
    for port in clash_ports:
        if services.is_port_listening(port):
            active_clash_port = port
            tun_warning = True # If Clash is running, flag potential TUN issue
            break
            
    return {
        "bridge100_ok": bridge100_ok,
        "clash_running": tun_warning,
        "clash_port": active_clash_port,
        "diagnostics": {
            "status": "warning" if (not bridge100_ok or tun_warning) else "healthy",
            "message": (
                "检测到 Clash 代理正在运行。请确保 Docker 容器环境变量中已正确配置 OLLAMA_BASE_URL 使用直连 IP 192.168.64.1，并声明 NO_PROXY 白名单，以防止 TUN 模式劫持本地流量。"
                if tun_warning else "系统网络连接健康。本地桥接网卡与代理环境握手正常。"
            )
        }
    }

OLLAMA_MODEL_METADATA = {
    "llama3.2:3b": {
        "title": "Llama 3.2 3B Instruct",
        "purpose": "日常中英文翻译、文本润色、轻量闲聊",
        "vram": "约 2.2 GB",
        "speed": "100+ tokens/s"
    },
    "llama3.2": {
        "title": "Llama 3.2 3B Instruct",
        "purpose": "日常中英文翻译、文本润色、轻量闲聊",
        "vram": "约 2.2 GB",
        "speed": "100+ tokens/s"
    },
    "phi4-mini": {
        "title": "Phi-4 Mini (3.8B)",
        "purpose": "微软出品，逻辑、数学和函数调用（Tool Calling）表现优异的超轻量模型",
        "vram": "约 2.5 GB",
        "speed": "100+ tokens/s"
    },
    "qwen3.5:4b": {
        "title": "Qwen 3.5 4B Instruct",
        "purpose": "通义千问最新一代超轻量模型，中文日常问答与快答首选",
        "vram": "约 2.6 GB",
        "speed": "100+ tokens/s"
    },
    "deepseek-r1:7b": {
        "title": "DeepSeek-R1 Distill Qwen 7B",
        "purpose": "具备本地“慢思考”推理链的数学/逻辑/代码推理模型",
        "vram": "约 4.5 GB",
        "speed": "60 - 80 tokens/s"
    },
    "gemma-4-12b": {
        "title": "Gemma 4 12B Instruct (Q4_K_XL)",
        "purpose": "谷歌官方 12B 旗舰模型，极高智商，适合处理复杂综合任务",
        "vram": "约 6.9 GB",
        "speed": "30 - 45 tokens/s"
    },
    "bge-m3": {
        "title": "BGE-M3 Embedding",
        "purpose": "专用中文/多语言向量模型，后台 RAG 检索器（已在菜单隐藏）",
        "vram": "约 1.2 GB",
        "speed": "向量计算专用"
    }
}

@app.get("/api/ollama/models")
def get_ollama_models():
    import urllib.request
    import json
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=1.0) as response:
            data = json.loads(response.read().decode())
            models_list = data.get("models", [])
            
            result = []
            for m in models_list:
                name = m.get("name", "")
                meta = None
                for k, v in OLLAMA_MODEL_METADATA.items():
                    if k in name.lower():
                        meta = v
                        break
                
                size_gb = m.get("size", 0) / (1024 ** 3)
                
                if meta:
                    result.append({
                        "name": name,
                        "title": meta["title"],
                        "purpose": meta["purpose"],
                        "vram": meta["vram"],
                        "speed": meta["speed"],
                        "size_gb": round(size_gb, 1)
                    })
                else:
                    result.append({
                        "name": name,
                        "title": name.title(),
                        "purpose": "本地下载的自定义模型",
                        "vram": f"约 {round(size_gb * 1.2, 1)} GB",
                        "speed": "视模型参数大小而定",
                        "size_gb": round(size_gb, 1)
                    })
            return result
    except Exception as e:
        raise HTTPException(status_code=503, detail="Ollama 引擎未运行或无法连接")

from pydantic import BaseModel

class TestRequest(BaseModel):
    prompt: str
    model: str = ""

@app.post("/api/llama/test")
def test_llama_endpoint(req: TestRequest):
    import urllib.request
    import json
    
    url = "http://localhost:8090/v1/chat/completions"
    payload = {
        "messages": [
            {"role": "user", "content": req.prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 512
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        req_data = json.dumps(payload).encode('utf-8')
        request = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=30.0) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            choices = res_data.get("choices", [])
            if choices:
                content = choices[0].get("message", {}).get("content", "")
                return {"status": "ok", "response": content}
            return {"status": "error", "message": "未返回有效响应内容"}
    except urllib.error.URLError as e:
        raise HTTPException(status_code=503, detail="无法连接到 llama.cpp 服务，请确认服务已启动且 8090 端口处于监听状态。")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"调用出错: {str(e)}")

class DownloadRequest(BaseModel):
    service: str
    model_id: str

@app.get("/api/download/status")
def get_download_status_endpoint(service: str):
    if service not in ["ollama", "mlx", "litert"]:
        raise HTTPException(status_code=400, detail="不支持的引擎名称。")
    status = services.get_download_status(service)
    return {"status": status}

@app.post("/api/download")
def start_download_endpoint(req: DownloadRequest):
    try:
        services.start_download(req.service, req.model_id)
        return {"status": "ok", "message": f"开始下载 {req.model_id}"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/huggingface/trending")
def get_hf_trending_models(service: str):
    import urllib.request
    import json
    import re
    
    if service not in ["ollama", "mlx", "litert"]:
        raise HTTPException(status_code=400, detail="不支持的引擎名称。")
        
    url = ""
    if service == "mlx":
        url = "https://huggingface.co/api/models?author=mlx-community&sort=lastModified&direction=-1&limit=40"
    elif service == "ollama":
        url = "https://huggingface.co/api/models?tags=gguf&sort=downloads&direction=-1&limit=45"
    elif service == "litert":
        url = "https://huggingface.co/api/models?search=tflite&pipeline_tag=text-generation&sort=downloads&direction=-1&limit=40"
        
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=10.0) as response:
            models_data = json.loads(response.read().decode('utf-8'))
            
            results = []
            for m in models_data:
                model_id = m.get("id", "")
                tags = m.get("tags", [])
                pipeline = m.get("pipeline_tag") or "text-generation"
                downloads = m.get("downloads", 0)
                likes = m.get("likes", 0)
                last_mod = m.get("lastModified", "")
                
                # Filter task types: keep only text generation or conversational or vision-text
                if pipeline not in ["text-generation", "conversational", "image-text-to-text"]:
                    continue
                    
                model_id_lower = model_id.lower()
                
                # 1. Classify Company / Creator
                company = "Other"
                if "qwen" in model_id_lower or "qwen" in tags:
                    company = "Alibaba"
                elif "llama" in model_id_lower or "llama" in tags:
                    company = "Meta"
                elif "gemma" in model_id_lower or "gemma" in tags:
                    company = "Google"
                elif "phi" in model_id_lower or "phi" in tags:
                    company = "Microsoft"
                elif "deepseek" in model_id_lower or "deepseek" in tags:
                    company = "DeepSeek"
                elif "mistral" in model_id_lower or "mixtral" in model_id_lower:
                    company = "Mistral"
                    
                # 2. Extract Parameter Size (e.g. 3b, 7b, 8b, 14b, 32b)
                param_size = 7.0 # Default fallback
                match = re.search(r'(\d+(?:\.\d+)?)[bB]', model_id)
                if match:
                    try:
                        param_size = float(match.group(1))
                    except ValueError:
                        pass
                else:
                    # check typical tags
                    for t in tags:
                        if t.endswith("b") and t[:-1].replace(".", "").isdigit():
                            try:
                                param_size = float(t[:-1])
                                break
                            except ValueError:
                                pass
                            
                # 3. Check Quantization (Bit width) and multiply factor
                is_quantized = False
                bit_width = 4
                for t in tags:
                    if "bit" in t:
                        is_quantized = True
                        num_match = re.search(r'(\d+)bit', t.replace("-", ""))
                        if num_match:
                            bit_width = int(num_match.group(1))
                            break
                
                # Check for FP16 or BF16 unquantized flags
                is_fp16 = "bf16" in model_id_lower or "fp16" in model_id_lower or "bf16" in tags or "fp16" in tags
                
                # Calculate estimated VRAM
                if is_fp16:
                    vram_est = param_size * 2.0 + 1.0
                elif is_quantized:
                    if bit_width <= 2:
                        vram_est = param_size * 0.4 + 1.0
                    elif bit_width <= 4:
                        vram_est = param_size * 0.6 + 1.0
                    elif bit_width <= 8:
                        vram_est = param_size * 0.9 + 1.0
                    else:
                        vram_est = param_size * 0.6 + 1.0
                else:
                    # Default to 4-bit quant estimate for typical HF downloads
                    vram_est = param_size * 0.6 + 1.0
                    
                # 4. Suitability grading
                if vram_est <= 6.0:
                    suitability = "smooth"
                    suitability_desc = f"🟢 完美流畅 ({round(vram_est, 1)}GB)"
                elif vram_est <= 10.0:
                    suitability = "heavy"
                    suitability_desc = f"🟡 较吃力 ({round(vram_est, 1)}GB)"
                else:
                    suitability = "unsupported"
                    suitability_desc = f"🔴 硬件超限 ({round(vram_est, 1)}GB)"
                    
                # 5. Extract quantization scheme label
                quant_info = "4-bit (量化)"
                if is_fp16:
                    quant_info = "BF16 (未量化 / 高精度)"
                elif "fp16" in model_id_lower or "fp16" in tags:
                    quant_info = "FP16 (未量化 / 高精度)"
                else:
                    # Look for specific GGUF / MLX quant flags
                    match_scheme = re.search(r'(q\d+_[kK]_[sSmMlL]|q\d+_\d|nvfp4|mxfp8|mxfp4|8bit|4bit|2bit|q\d+)', model_id_lower)
                    if match_scheme:
                        scheme = match_scheme.group(1).upper()
                        if "BIT" in scheme:
                            quant_info = f"{scheme.replace('BIT', '')}-bit (量化)"
                        elif scheme.startswith("Q") and "_" in scheme:
                            bit = scheme[1] if len(scheme) > 1 and scheme[1].isdigit() else "4"
                            quant_info = f"{bit}-bit ({scheme})"
                        elif scheme.startswith("Q") and len(scheme) == 2 and scheme[1].isdigit():
                            quant_info = f"{scheme[1]}-bit ({scheme})"
                        else:
                            bit = "4" if "4" in scheme else "8"
                            quant_info = f"{bit}-bit ({scheme})"
                    else:
                        quant_info = f"{bit_width}-bit (量化)"
                        
                # 6. Extract/Infer Context Window and Capabilities
                context_window = "8K"
                if "qwen2.5" in model_id_lower or "qwen-2.5" in model_id_lower:
                    context_window = "128K"
                elif "qwen3" in model_id_lower:
                    context_window = "128K"
                elif "llama-3.1" in model_id_lower or "llama3.1" in model_id_lower:
                    context_window = "128K"
                elif "llama-3.2" in model_id_lower or "llama3.2" in model_id_lower:
                    context_window = "128K"
                elif "llama-3" in model_id_lower or "llama3" in model_id_lower:
                    context_window = "8K"
                elif "gemma-2" in model_id_lower or "gemma2" in model_id_lower:
                    context_window = "8K"
                elif "gemma-4" in model_id_lower or "gemma4" in model_id_lower:
                    context_window = "8K"
                elif "deepseek" in model_id_lower:
                    context_window = "64K"
                elif "phi-4" in model_id_lower:
                    context_window = "16K"
                elif "phi-3" in model_id_lower:
                    if "128k" in model_id_lower:
                        context_window = "128K"
                    else:
                        context_window = "4K"
                        
                capabilities = ["通用对话 (Chat)"]
                if "coder" in model_id_lower or "code" in model_id_lower:
                    capabilities = ["代码 (Code)", "逻辑推理"]
                elif "math" in model_id_lower:
                    capabilities = ["数学 (Math)", "逻辑推理"]
                elif "r1" in model_id_lower or "reasoning" in model_id_lower:
                    capabilities = ["深度推理 (Reasoning)", "复杂问题"]
                elif "instruct" in model_id_lower or "it" in model_id_lower or "chat" in model_id_lower:
                    capabilities = ["通用对话 (Chat)"]
                elif "base" in model_id_lower:
                    capabilities = ["基座模型 (Base)"]
                    
                if pipeline == "image-text-to-text" or "vision" in model_id_lower or "vl" in model_id_lower:
                    capabilities.append("多模态 (Vision)")
                    
                # Format update date
                update_date = ""
                if last_mod:
                    try:
                        update_date = last_mod.split("T")[0]
                    except Exception:
                        pass
                
                # Check gated status
                is_gated = bool(m.get("gated", False))
                
                # Extract license info
                license_info = "Unknown"
                for t in tags:
                    if t.startswith("license:"):
                        license_info = t.split("license:")[1].upper()
                        break
                        
                # Compute KV cache overhead (realistic GB at full context)
                ctx_val = 8
                if context_window == "128K":
                    ctx_val = 128
                elif context_window == "64K":
                    ctx_val = 64
                elif context_window == "16K":
                    ctx_val = 16
                elif context_window == "4K":
                    ctx_val = 4
                kv_overhead = max(0.1, round(param_size * ctx_val * 0.002, 1))
                
                # 7. Speed and Download Size estimation (M5 Mac 16GB)
                if param_size <= 3.0:
                    speed_est = "~45 t/s (极速)"
                elif param_size <= 9.0:
                    speed_est = "~25 t/s (高速)"
                elif param_size <= 15.0:
                    speed_est = "~12 t/s (偏慢)"
                else:
                    speed_est = "无法流畅运行"
                    
                download_size_est = max(0.5, round(vram_est - 1.0, 1))
                
                # 8. Extract Model Series and Author
                parts = model_id.split("/")
                author = parts[0]
                if author == "hf.co" and len(parts) > 1:
                    author = parts[1]
                    
                model_family = "Other Family"
                if "qwen2.5-coder" in model_id_lower or "qwen-2.5-coder" in model_id_lower:
                    model_family = "Qwen 2.5 Coder"
                elif "qwen2.5" in model_id_lower or "qwen-2.5" in model_id_lower:
                    model_family = "Qwen 2.5"
                elif "qwen3" in model_id_lower:
                    model_family = "Qwen 3"
                elif "llama-3.1" in model_id_lower or "llama3.1" in model_id_lower:
                    model_family = "Llama 3.1"
                elif "llama-3.2" in model_id_lower or "llama3.2" in model_id_lower:
                    model_family = "Llama 3.2"
                elif "llama-3" in model_id_lower or "llama3" in model_id_lower:
                    model_family = "Llama 3"
                elif "gemma-2" in model_id_lower or "gemma2" in model_id_lower:
                    model_family = "Gemma 2"
                elif "gemma-4" in model_id_lower or "gemma4" in model_id_lower:
                    model_family = "Gemma 4"
                elif "deepseek" in model_id_lower:
                    model_family = "DeepSeek R1"
                elif "phi-4" in model_id_lower:
                    model_family = "Phi 4"
                elif "phi-3" in model_id_lower:
                    model_family = "Phi 3"
                        
                results.append({
                    "id": model_id,
                    "downloads": downloads,
                    "likes": likes,
                    "pipeline": pipeline,
                    "company": company,
                    "vram_est": round(vram_est, 1),
                    "suitability": suitability,
                    "suitability_desc": suitability_desc,
                    "format": "MLX (Safetensors)" if service == "mlx" else ("LiteRT (TFLite)" if service == "litert" else "GGUF (Unified)"),
                    "quantization": quant_info,
                    "context_window": context_window,
                    "capabilities": capabilities,
                    "update_date": update_date,
                    "gated": is_gated,
                    "license": license_info,
                    "param_size": f"{param_size}B",
                    "kv_overhead": kv_overhead,
                    "speed_est": speed_est,
                    "download_size": f"~{download_size_est} GB",
                    "model_family": model_family,
                    "author": author
                })
            return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取 Hugging Face 最新模型失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    script_dir = os.path.dirname(os.path.abspath(__file__))
    uvicorn.run("main:app", host="127.0.0.1", port=8123, reload=True, app_dir=script_dir)
