import os
import subprocess
import re
import socket
import urllib.request
import urllib.error
import json
import psutil

# Configuration of local services
SERVICES = {
    "ollama": {
        "name": "Ollama Service",
        "port": 11434,
        "api_url": "http://localhost:11434/api/tags",
        "description": "GGUF model runner (handles lightweight models and embedding model BGE-M3)"
    },
    "mlx": {
        "name": "MLX Service",
        "port": 8080,
        "api_url": "http://localhost:8080/v1/models",
        "description": "Native Apple Silicon Metal accelerated engine (for high-performance Qwen Coder models)"
    },
    "litert": {
        "name": "LiteRT Service",
        "port": 4010,
        "api_url": "http://127.0.0.1:4010/v1/models",
        "description": "Lightweight Google LiteRT runtime (running gemma4-e4b with image input)"
    },
    "webui": {
        "name": "Open WebUI Container",
        "port": 3000,
        "api_url": "http://localhost:3000/",
        "description": "Web interfaces and RAG document mounting dashboard"
    },
    "llama_cpp": {
        "name": "llama.cpp 引擎",
        "port": 8090,
        "api_url": "http://localhost:8090/health",
        "description": "原生极简 C/C++ 推理引擎 (基于 Metal GPU 硬件加速直跑 GGUF 模型)"
    }
}

def get_installed_mlx_models():
    cache_dir = os.path.expanduser("~/.cache/huggingface/hub")
    installed = []
    if os.path.exists(cache_dir):
        for item in os.listdir(cache_dir):
            if item.startswith("models--"):
                model_dir = os.path.join(cache_dir, item)
                
                # Verify that model weights (.safetensors) are actually downloaded
                has_weights = False
                for root, dirs, files in os.walk(model_dir):
                    if any(f.endswith(".safetensors") for f in files):
                        has_weights = True
                        break
                
                if not has_weights:
                    continue  # Skip model folder if weights are missing
                    
                parts = item.split("--")
                if len(parts) >= 3:
                    author = parts[1]
                    name = parts[2]
                    model_id = f"{author}/{name}"
                    
                    # Make name user-friendly
                    nice_name = name.replace("-Instruct-4bit", " (Instruct 4bit)").replace("-it-4bit", " (IT 4bit)").replace("-4bit", " (4bit)").replace("-", " ")
                    nice_name = nice_name.title()
                    
                    installed.append({
                        "key": model_id,
                        "name": f"{nice_name}"
                    })
    if not installed:
        installed.append({
            "key": "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit",
            "name": "Qwen2.5 Coder 7B (Default)"
        })
    return installed

def get_installed_gguf_models():
    manifests_dir = os.path.expanduser("~/.ollama/models/manifests/registry.ollama.ai/library")
    blobs_dir = os.path.expanduser("~/.ollama/models/blobs")
    installed = []
    
    if os.path.exists(manifests_dir):
        for model_name in os.listdir(manifests_dir):
            model_dir = os.path.join(manifests_dir, model_name)
            if os.path.isdir(model_dir):
                for tag in os.listdir(model_dir):
                    tag_path = os.path.join(model_dir, tag)
                    if os.path.isfile(tag_path) and not tag.startswith("."):
                        try:
                            with open(tag_path, "r") as f:
                                manifest = json.load(f)
                                layers = manifest.get("layers", [])
                                
                                # Skip custom prompt wrapper models (which contain a system prompt layer)
                                if any(l.get("mediaType") == "application/vnd.ollama.image.system" for l in layers):
                                    continue
                                    
                                for layer in layers:
                                    if layer.get("mediaType") == "application/vnd.ollama.image.model":
                                        digest = layer.get("digest", "")
                                        if digest.startswith("sha256:"):
                                            blob_filename = digest.replace(":", "-")
                                            blob_path = os.path.join(blobs_dir, blob_filename)
                                            if os.path.exists(blob_path):
                                                full_name = f"{model_name}:{tag}"
                                                if "bge-m3" in model_name:
                                                    continue
                                                
                                                nice_name = f"{model_name.replace('-', ' ').title()} ({tag})"
                                                installed.append({
                                                    "key": blob_path,
                                                    "name": nice_name,
                                                    "model_tag": full_name
                                                })
                        except Exception:
                            pass
    if not installed:
        installed.append({
            "key": "",
            "name": "未检测到 Ollama 本地 GGUF 模型",
            "model_tag": "None"
        })
    return installed

def get_installed_litert_models():
    models_dir = os.path.expanduser("~/.litert-lm/models")
    installed = []
    if os.path.exists(models_dir):
        for name in os.listdir(models_dir):
            path = os.path.join(models_dir, name)
            if os.path.isdir(path) and not name.startswith("."):
                # Calculate size of all files inside this directory
                size_bytes = 0
                for root, dirs, files in os.walk(path):
                    for file in files:
                        size_bytes += os.path.getsize(os.path.join(root, file))
                size_gb = size_bytes / (1024 ** 3)
                nice_name = f"{name} ({round(size_gb, 1)} GB)"
                installed.append({
                    "key": name,
                    "name": nice_name
                })
    if not installed:
        installed.append({
            "key": "",
            "name": "未检测到已导入的 LiteRT 模型"
        })
    return installed

# VRAM memory footprint estimates for warning safeguard (in GB)
VRAM_ESTIMATES = {
    "llama3.2:3b": 2.2,
    "phi4-mini": 2.5,
    "qwen3.5:4b": 2.6,
    "deepseek-r1:7b": 4.5,
    "gemma-4-12b": 6.9,
    "qwen-7b": 5.0,
    "gemma2-9b": 5.8,
    "litert-gemma4": 3.0
}

def estimate_vram_gb(model_id):
    if not model_id:
        return 4.0
    model_id_lower = model_id.lower()
    for k, v in VRAM_ESTIMATES.items():
        if k in model_id_lower:
            return v
    # Fallback to parsing size
    match = re.search(r'(\d+)[bB]', model_id_lower)
    if match:
        size = int(match.group(1))
        if size <= 3: return 2.5
        elif size <= 4: return 2.6
        elif size <= 8: return 5.0
        elif size <= 9: return 5.8
        elif size <= 12: return 6.9
        elif size <= 14: return 8.8
    return 4.0

def is_port_listening(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0

def check_api_status(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=1.0) as response:
            if response.status in [200, 401, 403]: # 401/403 means listening but needs auth
                return True
    except urllib.error.HTTPError as e:
        if e.code in [401, 403]:
            return True
    except Exception:
        pass
    return False

def get_service_status(key):
    service = SERVICES.get(key)
    if not service:
        return {"status": "unknown"}
    
    port = service["port"]
    api_url = service["api_url"]
    
    port_active = is_port_listening(port)
    api_active = check_api_status(api_url)
    
    if api_active:
        status = "running"
    elif port_active:
        status = "initializing"  # Port open but API not responding yet
    else:
        status = "stopped"
        
    # Get active PID or model details if running
    pid = None
    running_model = None
    
    if port_active:
        # Find process using the port
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                for conn in proc.connections(kind='inet'):
                    if conn.laddr.port == port:
                        pid = proc.pid
                        
                        # Dynamically resolve running model based on the service key
                        if key == "mlx":
                            running_model = "Unknown MLX Model"
                            cmd = proc.info.get('cmdline', [])
                            if cmd:
                                cmd_str = " ".join(cmd)
                                match = re.search(r'--model\s+([^\s]+)', cmd_str)
                                if match:
                                    running_model = match.group(1).split("/")[-1]
                        elif key == "llama_cpp":
                            running_model = "GGUF Model"
                            cmd = proc.info.get('cmdline', [])
                            if cmd:
                                cmd_str = " ".join(cmd)
                                match = re.search(r'-m\s+([^\s]+)', cmd_str)
                                if match:
                                    blob_path = match.group(1)
                                    gguf_models = get_installed_gguf_models()
                                    for m in gguf_models:
                                        if m["key"] == blob_path:
                                            running_model = m["model_tag"]
                                            break
                                    else:
                                        running_model = os.path.basename(blob_path)
                        elif key == "litert":
                            running_model = "gemma4-e4b"
                        elif key == "ollama":
                            running_model = "无活跃模型（已休眠）"
                            try:
                                with urllib.request.urlopen("http://localhost:11434/api/ps", timeout=0.2) as resp:
                                    ps_data = json.loads(resp.read().decode())
                                    models = [m.get("name") for m in ps_data.get("models", [])]
                                    if models:
                                        running_model = ", ".join(models)
                            except Exception:
                                pass
                        elif key == "webui":
                            running_model = None
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
    return {
        "status": status,
        "port": port,
        "pid": pid,
        "running_model": running_model if status == "running" else None,
        "description": service["description"]
    }

def start_service(key, model_key=None):
    if key == "ollama":
        if get_service_status("ollama")["status"] == "running":
            return True
        env = os.environ.copy()
        env["OLLAMA_HOST"] = "0.0.0.0"
        env["HTTP_PROXY"] = "http://127.0.0.1:7897"
        env["HTTPS_PROXY"] = "http://127.0.0.1:7897"
        env["NO_PROXY"] = "localhost,127.0.0.1,192.168.64.1"
        
        # Start Ollama serve
        with open("/tmp/ollama.log", "w") as f:
            subprocess.Popen(["ollama", "serve"], env=env, stdout=f, stderr=f, preexec_fn=os.setsid)
        return True
        
    elif key == "mlx":
        if get_service_status("mlx")["status"] == "running":
            return True
            
        installed = get_installed_mlx_models()
        if not model_key:
            model_key = installed[0]["key"] if installed else "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit"
            
        screen_name = "mlx-service"
        subprocess.run(["screen", "-S", screen_name, "-X", "quit"], capture_output=True)
        
        # Build environment copy with proxy configs for HuggingFace download fallbacks
        env = os.environ.copy()
        env["HTTP_PROXY"] = "http://127.0.0.1:7897"
        env["HTTPS_PROXY"] = "http://127.0.0.1:7897"
        env["NO_PROXY"] = "localhost,127.0.0.1,192.168.64.1"
        
        # Check for Qwen2.5 coder custom script
        home_dir = os.path.expanduser("~")
        python_bin = os.path.join(home_dir, "mlx_env/bin/python")
        if "qwen2.5-coder-7b" in model_key.lower():
            script_path = os.path.join(home_dir, ".config/mlx/start-qwen2.5-coder-7b-mlx.sh")
            if os.path.exists(script_path):
                cmd = ["screen", "-dmS", screen_name, script_path]
            else:
                cmd = [
                    "screen", "-dmS", screen_name,
                    python_bin, "-m", "mlx_lm", "server",
                    "--model", model_key,
                    "--host", "0.0.0.0", "--port", "8080", "--max-tokens", "2048"
                ]
        else:
            cmd = [
                "screen", "-dmS", screen_name,
                python_bin, "-m", "mlx_lm", "server",
                "--model", model_key,
                "--host", "0.0.0.0", "--port", "8080", "--max-tokens", "2048"
            ]
            
        subprocess.run(cmd, env=env)
        return True
        
    elif key == "litert":
        if get_service_status("litert")["status"] == "running":
            return True
            
        screen_name = "litert-gemma4-e4b"
        subprocess.run(["screen", "-S", screen_name, "-X", "quit"], capture_output=True)
        
        home_dir = os.path.expanduser("~")
        script_path = os.path.join(home_dir, "local_models/services/start-litert-gemma4-e4b.sh")
        cmd = [
            "screen", "-dmS", screen_name,
            "sh", "-c", f"LITERT_HOST=0.0.0.0 {script_path}"
        ]
        subprocess.run(cmd)
        return True
        
    elif key == "webui":
        if get_service_status("webui")["status"] == "running":
            return True
            
        # Ensure virtual machine is started
        subprocess.run(["container", "system", "start"], capture_output=True)
        # Start webui container
        subprocess.run(["container", "start", "local-webui"], capture_output=True)
        return True
        
    elif key == "llama_cpp":
        if get_service_status("llama_cpp")["status"] == "running":
            return True
            
        installed = get_installed_gguf_models()
        if not model_key:
            model_key = installed[0]["key"] if (installed and installed[0]["key"]) else None
            
        if not model_key or not os.path.exists(model_key):
            return False
            
        screen_name = "llama-cpp-service"
        subprocess.run(["screen", "-S", screen_name, "-X", "quit"], capture_output=True)
        
        cmd = [
            "screen", "-dmS", screen_name,
            "sh", "-c", f"llama-server -m '{model_key}' -c 2048 --port 8090 --host 0.0.0.0 > /tmp/llama_cpp.log 2>&1"
        ]
        
        # Build environment copy with proxy configs
        env = os.environ.copy()
        env["HTTP_PROXY"] = "http://127.0.0.1:7897"
        env["HTTPS_PROXY"] = "http://127.0.0.1:7897"
        env["NO_PROXY"] = "localhost,127.0.0.1,192.168.64.1"
        
        subprocess.run(cmd, env=env)
        return True
        
    return False

def stop_service(key):
    if key == "ollama":
        # Kill ollama
        subprocess.run(["killall", "Ollama"], capture_output=True)
        subprocess.run(["killall", "ollama"], capture_output=True)
        return True
    elif key == "mlx":
        # Terminate screen session
        subprocess.run(["screen", "-S", "mlx-service", "-X", "quit"], capture_output=True)
        # Also kill any leftover python mlx_lm servers
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmd = " ".join(proc.info.get('cmdline') or [])
                if "mlx_lm" in cmd:
                    os.kill(proc.pid, 9)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return True
    elif key == "litert":
        # Terminate screen session
        subprocess.run(["screen", "-S", "litert-gemma4-e4b", "-X", "quit"], capture_output=True)
        # Also kill litert-lm serve processes
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if "litert-lm" in proc.info.get('name', ''):
                    os.kill(proc.pid, 9)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return True
    elif key == "webui":
        subprocess.run(["container", "stop", "local-webui"], capture_output=True)
        return True
    elif key == "llama_cpp":
        subprocess.run(["screen", "-S", "llama-cpp-service", "-X", "quit"], capture_output=True)
        # Kill running llama-servers
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if "llama-server" in proc.info.get('name', ''):
                    os.kill(proc.pid, 9)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return True
    return False

def cool_down_mac():
    """Unconditionally stops all local services to free memory/CPU"""
    stop_service("webui")
    stop_service("mlx")
    stop_service("llama_cpp")
    stop_service("litert")
    stop_service("ollama")
    return True

def get_system_metrics():
    # CPU
    cpu_percent = psutil.cpu_percent(interval=None)
    
    # Unified Memory (macOS sysctl / psutil representation)
    mem = psutil.virtual_memory()
    total_gb = mem.total / (1024 ** 3)
    available_gb = mem.available / (1024 ** 3)
    used_gb = mem.used / (1024 ** 3)
    
    # Estimate AI VRAM allocation
    allocated_vram = 0.0
    active_models = []
    
    # Check Ollama active models
    ollama_status = get_service_status("ollama")
    if ollama_status["status"] == "running":
        try:
            # Query ollama running models API
            with urllib.request.urlopen("http://localhost:11434/api/ps", timeout=0.5) as response:
                data = json.loads(response.read().decode())
                for model in data.get("models", []):
                    model_name = model.get("name")
                    active_models.append(model_name)
                    # Lookup VRAM
                    for k, v in VRAM_ESTIMATES.items():
                        if k in model_name:
                            allocated_vram += v
                            break
                    else:
                        allocated_vram += 2.5 # default fallback
        except Exception:
            pass
            
    # Check MLX active models
    mlx_status = get_service_status("mlx")
    if mlx_status["status"] == "running":
        running_model = mlx_status["running_model"] or "Qwen2.5-Coder-7B"
        active_models.append(f"MLX: {running_model}")
        allocated_vram += estimate_vram_gb(running_model)
        
    # Check LiteRT active models
    litert_status = get_service_status("litert")
    if litert_status["status"] == "running":
        active_models.append("LiteRT: gemma4-e4b")
        allocated_vram += estimate_vram_gb("litert-gemma4")
        
    # Check llama_cpp active models
    llama_cpp_status = get_service_status("llama_cpp")
    if llama_cpp_status["status"] == "running":
        running_model = llama_cpp_status["running_model"] or "GGUF Model"
        active_models.append(f"llama.cpp: {running_model}")
        allocated_vram += estimate_vram_gb(running_model)
        
    # Check bridge100 network gateway status
    bridge100_ok = False
    try:
        out = subprocess.check_output(["ifconfig", "bridge100"], stderr=subprocess.DEVNULL).decode()
        if "192.168.64.1" in out:
            bridge100_ok = True
    except Exception:
        pass
        
    return {
        "cpu_percent": cpu_percent,
        "memory": {
            "total_gb": round(total_gb, 1),
            "used_gb": round(used_gb, 1),
            "available_gb": round(available_gb, 1),
            "percent": mem.percent
        },
        "vram": {
            "allocated_gb": round(allocated_vram, 1),
            "limit_gb": 11.0, # safe threshold for M5 16GB
            "percent": min(100, round((allocated_vram / 11.0) * 100, 1))
        },
        "active_models": active_models,
        "bridge100_ok": bridge100_ok
    }

def get_service_logs(key, lines=50):
    if key == "download_ollama":
        log_path = "/tmp/download_ollama.log"
    elif key == "download_mlx":
        log_path = "/tmp/download_mlx.log"
    elif key == "download_litert":
        log_path = "/tmp/download_litert.log"
    elif key == "ollama":
        log_path = "/tmp/ollama.log"
    elif key == "litert":
        log_path = os.path.join(os.path.expanduser("~"), "local_models/services/litert-gemma4-e4b.log")
    elif key == "mlx":
        # Check if screen output exists or direct logs
        log_path = "/tmp/mlx_server.log" # fallback or screen log
        # Let's check screen log
        if not os.path.exists(log_path):
            # Try to grab last logs from screen command
            try:
                subprocess.run(["screen", "-S", "mlx-service", "-X", "hardcopy", "/tmp/mlx_screen.log"])
                log_path = "/tmp/mlx_screen.log"
            except Exception:
                pass
    else:
        return "Log inspection not supported for this service."

    if not os.path.exists(log_path):
        return f"Log file not found at {log_path}."
        
    try:
        if key in ["download_ollama", "download_mlx", "download_litert"]:
            with open(log_path, "r", errors='ignore') as f:
                content = f.read()
                return content[-10000:]
        else:
            with open(log_path, "r", errors='ignore') as f:
                content = f.readlines()
                return "".join(content[-lines:])
    except Exception as e:
        return f"Error reading logs: {str(e)}"

def get_download_status(key):
    screen_name = f"download-{key}-service"
    try:
        out = subprocess.check_output(["screen", "-ls"], stderr=subprocess.DEVNULL).decode()
        if screen_name in out:
            return "running"
    except Exception:
        pass
    return "idle"

def start_download(key, model_id):
    if key not in ["ollama", "mlx", "litert"]:
        raise Exception("不支持的下载引擎。")
        
    if get_download_status(key) == "running":
        raise Exception("已有正在进行的下载任务！")
        
    # Check disk space
    import shutil
    total, used, free = shutil.disk_usage(os.path.expanduser("~"))
    if free < 20 * 1024 * 1024 * 1024:
        raise Exception("磁盘剩余空间少于 20GB，安全拦截。")
        
    # Check VRAM limits
    vram_est = estimate_vram_gb(model_id)
    if vram_est > 11.5:
        raise Exception(f"模型估算需要 {vram_est}GB 显存，超出本机 (16G M5 Mac) 11.5GB 显存安全红线，拦截下载。")
        
    screen_name = f"download-{key}-service"
    log_file = f"/tmp/download_{key}.log"
    
    # Initialize log file
    with open(log_file, "w") as f:
        f.write(f"📥 开始下载 {model_id}...\n")
        
    if key == "ollama":
        cmd = ["screen", "-dmS", screen_name, "sh", "-c", f"ollama pull {model_id} > {log_file} 2>&1"]
    elif key == "mlx":
        cmd = ["screen", "-dmS", screen_name, "sh", "-c", f"huggingface-cli download {model_id} > {log_file} 2>&1"]
    elif key == "litert":
        # Resolve repo and file from model_id
        parts = model_id.split("/")
        if len(parts) >= 3:
            # e.g. google/gemma-2b-it-tflite/gemma-2b-it-gpu-int4.bin
            repo = "/".join(parts[:2])
            filename = parts[2]
            local_ref = filename.split(".")[0]
        else:
            # e.g. google/gemma-2b-it-tflite
            repo = model_id
            # Query HF API to find the first suitable binary file
            try:
                import urllib.request
                import json
                hf_url = f"https://huggingface.co/api/models/{repo}"
                req_obj = urllib.request.Request(hf_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req_obj, timeout=5.0) as resp:
                    repo_data = json.loads(resp.read().decode())
                    files = [s.get("rfilename") for s in repo_data.get("siblings", [])]
                    suitable_files = [f for f in files if f.endswith((".bin", ".tflite", ".litertlm"))]
                    if suitable_files:
                        gpu_files = [f for f in suitable_files if "gpu" in f.lower()]
                        filename = gpu_files[0] if gpu_files else suitable_files[0]
                        local_ref = filename.split(".")[0]
                    else:
                        raise Exception("在该仓储中未找到任何 .bin, .tflite 或 .litertlm 文件！")
            except Exception as e:
                raise Exception(f"解析仓储文件失败: {str(e)}。请使用格式: repo/file.bin")

        litert_bin = os.path.join(os.path.expanduser("~"), ".local/share/uv/tools/litert-lm/bin/litert-lm")
        cmd = [
            "screen", "-dmS", screen_name, "sh", "-c",
            f"{litert_bin} import --from-huggingface-repo {repo} {filename} {local_ref} > {log_file} 2>&1"
        ]
        
    subprocess.run(cmd)
    return True

