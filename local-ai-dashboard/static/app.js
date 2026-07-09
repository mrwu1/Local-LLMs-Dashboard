let activeLogService = null;
let logPollInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    // Initialize Lucide Icons
    lucide.createIcons();
    
    // Fetch initial status and start periodic polling
    fetchStatus();
    setInterval(fetchStatus, 3000);
    
    // Bind cooldown trigger
    document.getElementById('cooldown-trigger').addEventListener('click', triggerCooldown);
    
    // Initialize download presets
    initDownloadPresets();
});

// Update the VRAM gauge ring offset
function setVramGauge(allocatedGb, limitGb) {
    const ring = document.getElementById('vram-ring');
    const label = document.getElementById('vram-val');
    
    label.innerText = `${allocatedGb.toFixed(1)} GB`;
    
    const percentage = Math.min(100, (allocatedGb / limitGb) * 100);
    const circumference = 440; // 2 * PI * r (r=70)
    const offset = circumference - (percentage / 100) * circumference;
    
    ring.style.strokeDashoffset = offset;
    
    // Change color dynamic based on allocation
    if (percentage > 90) {
        ring.style.stroke = 'var(--accent-red)';
    } else if (percentage > 70) {
        ring.style.stroke = 'var(--accent-yellow)';
    } else {
        ring.style.stroke = 'var(--primary)';
    }
}

// Fetch general system status and active models
async function fetchStatus() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        
        // Update service cards state
        updateServiceState('ollama', data.services.ollama);
        updateServiceState('mlx', data.services.mlx);
        updateServiceState('llama_cpp', data.services.llama_cpp);
        updateServiceState('litert', data.services.litert);
        updateServiceState('webui', data.services.webui);
        
        // Populate MLX models dropdown dynamically
        const select = document.getElementById('mlx-model-select');
        if (data.mlx_models) {
            const currentSelection = select.value;
            const currentKeys = Array.from(select.options).map(o => o.value).join(',');
            const newKeys = data.mlx_models.map(m => m.key).join(',');
            
            if (currentKeys !== newKeys) {
                select.innerHTML = '';
                data.mlx_models.forEach(model => {
                    const opt = document.createElement('option');
                    opt.value = model.key;
                    opt.innerText = model.name;
                    select.appendChild(opt);
                });
                if (currentSelection && data.mlx_models.some(m => m.key === currentSelection)) {
                    select.value = currentSelection;
                }
            }
        }

        // Populate GGUF models dropdown dynamically
        const ggufSelect = document.getElementById('llama_cpp-model-select');
        if (data.gguf_models && ggufSelect) {
            const currentGgufSelection = ggufSelect.value;
            const currentGgufKeys = Array.from(ggufSelect.options).map(o => o.value).join(',');
            const newGgufKeys = data.gguf_models.map(m => m.key).join(',');
            
            if (currentGgufKeys !== newGgufKeys) {
                ggufSelect.innerHTML = '';
                data.gguf_models.forEach(model => {
                    const opt = document.createElement('option');
                    opt.value = model.key;
                    opt.innerText = model.name;
                    ggufSelect.appendChild(opt);
                });
                if (currentGgufSelection && data.gguf_models.some(m => m.key === currentGgufSelection)) {
                    ggufSelect.value = currentGgufSelection;
                }
            }
        }

        // Populate LiteRT models dropdown dynamically
        const litertSelect = document.getElementById('litert-model-select');
        if (data.litert_models && litertSelect) {
            const currentLitertSelection = litertSelect.value;
            const currentLitertKeys = Array.from(litertSelect.options).map(o => o.value).join(',');
            const newLitertKeys = data.litert_models.map(m => m.key).join(',');
            
            if (currentLitertKeys !== newLitertKeys) {
                litertSelect.innerHTML = '';
                data.litert_models.forEach(model => {
                    const opt = document.createElement('option');
                    opt.value = model.key;
                    opt.innerText = model.name;
                    litertSelect.appendChild(opt);
                });
                if (currentLitertSelection && data.litert_models.some(m => m.key === currentLitertSelection)) {
                    litertSelect.value = currentLitertSelection;
                }
            }
        }
        
        // Update circular gauge & metrics
        const metrics = data.metrics;
        setVramGauge(metrics.vram.allocated_gb, metrics.vram.limit_gb);
        
        // Progress Bars
        document.getElementById('ram-text').innerText = `${metrics.memory.used_gb.toFixed(1)}GB / ${metrics.memory.total_gb.toFixed(1)}GB`;
        document.getElementById('ram-bar').style.width = `${metrics.memory.percent}%`;
        
        document.getElementById('cpu-text').innerText = `${metrics.cpu_percent.toFixed(0)}%`;
        document.getElementById('cpu-bar').style.width = `${metrics.cpu_percent}%`;
        
        // Update Safeguard status badge
        const safeguard = document.getElementById('safeguard-badge');
        if (metrics.vram.allocated_gb >= metrics.vram.limit_gb) {
            safeguard.className = 'safeguard-status warning';
            safeguard.innerHTML = '<i data-lucide="shield-alert" class="shield-red"></i> <span>内存红线守卫: ⚠️ 临界</span>';
        } else {
            safeguard.className = 'safeguard-status';
            safeguard.innerHTML = '<i data-lucide="shield-check" class="shield-green"></i> <span>内存红线守卫: 🟢 安全</span>';
        }
        
        // Active Models list
        const modelList = document.getElementById('active-models-list');
        modelList.innerHTML = '';
        if (metrics.active_models && metrics.active_models.length > 0) {
            metrics.active_models.forEach(model => {
                const li = document.createElement('li');
                li.innerText = model;
                modelList.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.className = 'empty-list';
            li.innerText = '暂无活跃模型在显存';
            modelList.appendChild(li);
        }
        
        // Network Diagnostics
        const bridgeBadge = document.getElementById('bridge-badge');
        if (metrics.bridge100_ok) {
            bridgeBadge.className = 'badge-green';
            bridgeBadge.innerText = '192.168.64.1';
        } else {
            bridgeBadge.className = 'badge-red';
            bridgeBadge.innerText = '无 IP 分配';
        }
        
        // Async Diagnostics call
        fetchDiagnostics();
        
        // Poll download status for active downloads
        pollDownloadStatuses();
        
        lucide.createIcons();
    } catch (e) {
        console.error("Status check failed", e);
    }
}

// Fetch network diagnostics
async function fetchDiagnostics() {
    try {
        const response = await fetch('/api/diagnose');
        const data = await response.json();
        
        const diagnoseBox = document.getElementById('diagnose-box');
        const diagMsg = document.getElementById('diag-message');
        
        diagMsg.innerText = data.diagnostics.message;
        
        if (data.diagnostics.status === 'warning') {
            diagnoseBox.classList.add('warning');
        } else {
            diagnoseBox.classList.remove('warning');
        }
    } catch (e) {
        console.error("Diagnostics check failed", e);
    }
}

// Update card UI based on backend service state
function updateServiceState(key, serviceState) {
    const card = document.getElementById(`card-${key}`);
    const dot = document.getElementById(`status-${key}`);
    
    // Status text & dot styling
    dot.innerText = getStatusLabel(serviceState.status);
    dot.className = `status-dot status-${serviceState.status}`;
    
    const startBtn = card.querySelector('.start-btn');
    const stopBtn = card.querySelector('.stop-btn');
    const linkBtn = card.querySelector('.web-link-btn');
    const selectWrapper = card.querySelector('.model-select-wrapper');
    
    if (serviceState.status === 'running') {
        startBtn.classList.add('hide');
        stopBtn.classList.remove('hide');
        if (linkBtn) linkBtn.classList.remove('hide');
        if (selectWrapper) selectWrapper.classList.add('hide'); // Hide model selection while running
        
        // Show model name in description if available
        const desc = card.querySelector('.service-desc');
        if (serviceState.running_model) {
            // Cache description if not already
            if (!desc.dataset.origDesc) desc.dataset.origDesc = desc.innerText;
            desc.innerHTML = `<strong>加载模型:</strong> <code style="background:rgba(255,255,255,0.08);padding:2px 4px;border-radius:4px;">${serviceState.running_model}</code>`;
        } else {
            if (desc.dataset.origDesc) desc.innerText = desc.dataset.origDesc;
        }
    } else if (serviceState.status === 'initializing') {
        startBtn.classList.add('hide');
        stopBtn.classList.remove('hide');
        if (linkBtn) linkBtn.classList.add('hide');
        if (selectWrapper) selectWrapper.classList.add('hide');
    } else {
        startBtn.classList.remove('hide');
        stopBtn.classList.add('hide');
        if (linkBtn) linkBtn.classList.add('hide');
        if (selectWrapper) selectWrapper.classList.remove('hide');
        
        // Reset description text
        const desc = card.querySelector('.service-desc');
        if (desc.dataset.origDesc) desc.innerText = desc.dataset.origDesc;
    }
}

function getStatusLabel(status) {
    switch (status) {
        case 'running': return '运行中';
        case 'initializing': return '载入中';
        case 'stopped': return '已关停';
        default: return '未知';
    }
}

// Toggle Service action trigger
async function toggleService(key) {
    const card = document.getElementById(`card-${key}`);
    let url = `/api/start?service=${key}`;
    
    if (key === 'mlx') {
        const select = document.getElementById('mlx-model-select');
        url += `&model=${select.value}`;
    } else if (key === 'llama_cpp') {
        const select = document.getElementById('llama_cpp-model-select');
        url += `&model=${encodeURIComponent(select.value)}`;
    }
    
    // Instantly transition dot to initializing to prevent double click
    const dot = document.getElementById(`status-${key}`);
    dot.innerText = '拉起中...';
    dot.className = 'status-dot status-initializing';
    
    try {
        const response = await fetch(url, { method: 'POST' });
        const result = await response.json();
        if (response.ok) {
            fetchStatus();
        } else {
            alert(result.detail || "启动失败，请检查资源");
            fetchStatus();
        }
    } catch (e) {
        alert("网络请求失败");
        fetchStatus();
    }
}

// Stop Service action trigger
async function stopService(key) {
    try {
        const response = await fetch(`/api/stop?service=${key}`, { method: 'POST' });
        if (response.ok) {
            fetchStatus();
        } else {
            const result = await response.json();
            alert(result.detail || "停机失败");
        }
    } catch (e) {
        alert("网络请求失败");
    }
}

// Trigger Master Cooldown ("退烧药")
async function triggerCooldown() {
    if (!confirm("确定要强行终止所有本地大模型进程与前端容器吗？这会瞬间释放所有显存和物理内存。")) return;
    
    try {
        const response = await fetch('/api/cooldown', { method: 'POST' });
        if (response.ok) {
            alert("降温指令已执行，系统核心已释放。");
            fetchStatus();
        }
    } catch (e) {
        alert("网络请求失败");
    }
}

/* Modal and logs management */
function openLogs(key) {
    activeLogService = key;
    document.getElementById('modal-service-title').innerText = `${SERVICES_TITLES[key] || key} 实时运行日志`;
    
    // Set log path label
    const pathLbl = document.getElementById('log-path-lbl');
    pathLbl.innerText = `日志文件: ${LOG_PATHS[key] || '--'}`;
    
    document.getElementById('log-content').innerText = '正在载入日志文件...';
    document.getElementById('logs-modal').classList.add('active');
    
    refreshLogs();
    
    // Setup interval to refresh log modal every 3 seconds
    if (logPollInterval) clearInterval(logPollInterval);
    logPollInterval = setInterval(refreshLogs, 3000);
}

function closeLogs() {
    document.getElementById('logs-modal').classList.remove('active');
    if (logPollInterval) {
        clearInterval(logPollInterval);
        logPollInterval = null;
    }
    activeLogService = null;
}

async function refreshLogs() {
    if (!activeLogService) return;
    try {
        const response = await fetch(`/api/logs/${activeLogService}?lines=80`);
        const data = await response.json();
        
        const logContent = document.getElementById('log-content');
        logContent.innerText = data.logs;
        // Scroll log terminal to the bottom
        logContent.scrollTop = logContent.scrollHeight;
    } catch (e) {
        document.getElementById('log-content').innerText = '日志载入失败，请确认服务已启动且日志文件可读。';
    }
}

const SERVICES_TITLES = {
    "ollama": "Ollama Service",
    "mlx": "MLX Framework Service",
    "litert": "LiteRT Serve",
    "llama_cpp": "llama.cpp Engine"
};

const LOG_PATHS = {
    "ollama": "/tmp/ollama.log",
    "mlx": "/tmp/mlx_screen.log",
    "litert": "/Users/anan/local_models/services/litert-gemma4-e4b.log",
    "llama_cpp": "/tmp/llama_cpp.log"
};

async function openOllamaModels() {
    const listContainer = document.getElementById('ollama-models-list');
    listContainer.innerHTML = '<div style="color:var(--text-secondary)">正在连接 Ollama 并读取模型列表...</div>';
    document.getElementById('ollama-models-modal').classList.add('active');
    
    try {
        const response = await fetch('/api/ollama/models');
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "读取失败");
        }
        
        const models = await response.json();
        listContainer.innerHTML = '';
        
        if (models.length === 0) {
            listContainer.innerHTML = '<div style="color:var(--text-muted); font-style:italic;">本地未下载任何 Ollama 模型。请在终端执行 `ollama pull [模型名]` 下载。</div>';
            return;
        }
        
        models.forEach(model => {
            const item = document.createElement('div');
            item.className = 'ollama-model-item';
            
            // Build item markup
            item.innerHTML = `
                <div class="ollama-model-title">
                    <span>${model.title}</span>
                    <span class="ollama-model-tag">${model.name}</span>
                </div>
                <div class="ollama-model-purpose">${model.purpose}</div>
                <div class="ollama-model-meta-row">
                    <span class="ollama-meta-label"><i data-lucide="database" style="width:14px;height:14px;"></i> 存储大小: ${model.size_gb.toFixed(1)} GB</span>
                    <span class="ollama-meta-label"><i data-lucide="cpu" style="width:14px;height:14px;"></i> 显存需求: ${model.vram}</span>
                    <span class="ollama-meta-label"><i data-lucide="zap" style="width:14px;height:14px;"></i> 运行速度: ${model.speed}</span>
                </div>
            `;
            listContainer.appendChild(item);
        });
        
        lucide.createIcons();
    } catch (e) {
        listContainer.innerHTML = `
            <div style="color:var(--accent-red); display:flex; flex-direction:column; gap:0.5rem; align-items:center; text-align:center; padding:1.5rem 0;">
                <i data-lucide="alert-triangle" style="width:32px;height:32px;"></i>
                <strong>连接 Ollama 失败</strong>
                <span style="font-size:0.85rem; color:var(--text-secondary);">${e.message || "请确认已点击【启动】按钮拉起 Ollama 后端进程，且 11434 端口处于监听状态。"}</span>
            </div>
        `;
        lucide.createIcons();
    }
}

function closeOllamaModels() {
    document.getElementById('ollama-models-modal').classList.remove('active');
}

const LLAMA_TEST_CASES = [
    {
        title: "💬 中文快答",
        prompt: "你好！请用一句话介绍你自己，并告诉我你当前运行的底层推理引擎是什么。"
    },
    {
        title: "💻 写 Python 代码",
        prompt: "写一个 Python 递归函数用于计算斐波那契数列的第 N 项，并附带简单的调用示例。"
    },
    {
        title: "🌐 英文翻译",
        prompt: "将以下句子翻译为地道的英文：'私有化部署本地大模型，既能保证核心资产的数据合规，又能规避云端服务的隐私泄露风险。'"
    },
    {
        title: "🔬 语义对齐原理",
        prompt: "在多维语义向量空间（Embedding Space）中，余弦相似度（Cosine Similarity）与欧氏距离（Euclidean Distance）在评估文本关联度时有什么本质区别？"
    }
];

function openLlamaTestModal() {
    document.getElementById('llama-test-modal').classList.add('active');
    
    // Populate test case buttons
    const casesRow = document.getElementById('test-cases-row');
    casesRow.innerHTML = '';
    
    LLAMA_TEST_CASES.forEach((c, index) => {
        const btn = document.createElement('button');
        btn.className = 'action-btn';
        btn.style.background = 'rgba(255, 255, 255, 0.04)';
        btn.style.border = '1px solid rgba(255, 255, 255, 0.08)';
        btn.style.color = 'var(--text-secondary)';
        btn.style.padding = '0.35rem 0.75rem';
        btn.style.fontSize = '0.8rem';
        btn.style.borderRadius = '6px';
        btn.style.cursor = 'pointer';
        btn.innerText = c.title;
        btn.onclick = () => {
            document.getElementById('test-prompt-input').value = c.prompt;
        };
        casesRow.appendChild(btn);
    });
    
    // Clear output
    document.getElementById('test-output-console').innerText = '控制台等待指令...';
    document.getElementById('test-status-lbl').innerText = '等待发送...';
}

function closeLlamaTestModal() {
    document.getElementById('llama-test-modal').classList.remove('active');
}

async function sendLlamaTest() {
    const prompt = document.getElementById('test-prompt-input').value.trim();
    if (!prompt) {
        alert("请输入测试提示词！");
        return;
    }
    
    const consoleBox = document.getElementById('test-output-console');
    const statusLbl = document.getElementById('test-status-lbl');
    
    consoleBox.innerHTML = '<span style="color:var(--primary); font-style:italic;">⚡ 正在向 llama.cpp (Port 8090) 提交测试用例...</span>';
    statusLbl.innerText = '发送中...';
    
    try {
        const response = await fetch('/api/llama/test', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ prompt: prompt })
        });
        
        const data = await response.json();
        if (response.ok) {
            consoleBox.innerText = data.response;
            statusLbl.innerText = '✅ 接收响应成功';
        } else {
            consoleBox.innerHTML = `<span style="color:var(--accent-red)">❌ 调用失败: ${data.detail || "服务无响应"}</span>`;
            statusLbl.innerText = '❌ 发生错误';
        }
    } catch (e) {
        consoleBox.innerHTML = `<span style="color:var(--accent-red)">❌ 网络请求错误: ${e.message}</span>`;
        statusLbl.innerText = '❌ 发生错误';
    }
}

// Download Presets metadata
const DOWNLOAD_PRESETS = {
    ollama: [
        { name: "llama3.2:3b", label: "Llama3.2 3B", suitability: "smooth", icon: "🟢" },
        { name: "phi4-mini", label: "Phi4 Mini 3.8B", suitability: "smooth", icon: "🟢" },
        { name: "qwen3.5:4b", label: "Qwen3.5 4B", suitability: "smooth", icon: "🟢" },
        { name: "deepseek-r1:7b", label: "DeepSeek R1 7B", suitability: "smooth", icon: "🟢" },
        { name: "hf.co/unsloth/gemma-4-12B-it-qat-GGUF:UD-Q4_K_XL", label: "Gemma4 12B", suitability: "heavy", icon: "🟡" }
    ],
    mlx: [
        { name: "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit", label: "Qwen2.5 Coder 7B", suitability: "smooth", icon: "🟢" },
        { name: "mlx-community/Llama-3.2-3B-Instruct-4bit", label: "Llama3.2 3B", suitability: "smooth", icon: "🟢" },
        { name: "mlx-community/gemma-2-9b-it-4bit", label: "Gemma2 9B", suitability: "smooth", icon: "🟢" },
        { name: "mlx-community/phi-4-4bit", label: "Phi4 14B", suitability: "heavy", icon: "🟡" }
    ],
    litert: [
        { name: "google/gemma-2b-it-tflite/gemma-2b-it-gpu-int4.bin", label: "Gemma 2B GPU", suitability: "smooth", icon: "🟢" },
        { name: "google/gemma-1.1-2b-it-tflite/gemma-1.1-2b-it-gpu-int4.bin", label: "Gemma1.1 2B GPU", suitability: "smooth", icon: "🟢" },
        { name: "sg2023/gemma3-270m-it-sms-verification_code_extraction-int8-tflite", label: "Gemma3 270M INT8", suitability: "smooth", icon: "🟢" }
    ]
};

// Initialize preset buttons under Ollama, MLX & LiteRT cards
function initDownloadPresets() {
    ["ollama", "mlx", "litert"].forEach(service => {
        const container = document.getElementById(`presets-${service}`);
        if (!container) return;
        container.innerHTML = '';
        
        DOWNLOAD_PRESETS[service].forEach(preset => {
            const btn = document.createElement('button');
            btn.className = 'action-btn';
            btn.style.background = 'rgba(255, 255, 255, 0.03)';
            btn.style.border = '1px solid rgba(255, 255, 255, 0.05)';
            btn.style.color = 'var(--text-secondary)';
            btn.style.padding = '0.25rem 0.5rem';
            btn.style.fontSize = '0.72rem';
            btn.style.borderRadius = '4px';
            btn.style.cursor = 'pointer';
            btn.style.display = 'flex';
            btn.style.alignItems = 'center';
            btn.style.gap = '0.2rem';
            btn.innerHTML = `<span>${preset.icon}</span> <span>${preset.label}</span>`;
            
            btn.onclick = () => {
                document.getElementById(`download-input-${service}`).value = preset.name;
            };
            container.appendChild(btn);
        });
    });
}

// Global active download states
let activeDownloads = {
    ollama: false,
    mlx: false,
    litert: false
};

// Check if any download is running and update card UI
async function pollDownloadStatuses() {
    for (const service of ["ollama", "mlx", "litert"]) {
        try {
            const response = await fetch(`/api/download/status?service=${service}`);
            const data = await response.json();
            
            const input = document.getElementById(`download-input-${service}`);
            const btn = document.getElementById(`download-btn-${service}`);
            const logBtn = document.getElementById(`download-log-btn-${service}`);
            const statusTxt = document.getElementById(`download-status-${service}`);
            
            if (data.status === 'running') {
                activeDownloads[service] = true;
                input.disabled = true;
                btn.disabled = true;
                btn.style.opacity = '0.5';
                statusTxt.innerText = '⚡ 正在下载...';
                logBtn.classList.remove('hide');
            } else {
                activeDownloads[service] = false;
                input.disabled = false;
                btn.disabled = false;
                btn.style.opacity = '1';
                statusTxt.innerText = '';
                logBtn.classList.add('hide');
            }
        } catch (e) {
            console.error(`Failed to poll download status for ${service}`, e);
        }
    }
}

// Trigger background model download
async function startDownload(service) {
    const input = document.getElementById(`download-input-${service}`);
    const modelId = input.value.trim();
    if (!modelId) {
        alert("请输入模型 ID！");
        return;
    }
    
    // Front-end VRAM Safety Checks (Apple M5 16GB limit)
    let paramSize = null;
    const match = modelId.match(/(\d+(?:\.\d+)?)[bB]/);
    if (match) {
        paramSize = parseFloat(match[1]);
    } else {
        // Fallback checks for common sizes
        if (modelId.includes("3b")) paramSize = 3;
        else if (modelId.includes("7b") || modelId.includes("8b")) paramSize = 7;
        else if (modelId.includes("9b")) paramSize = 9;
        else if (modelId.includes("12b")) paramSize = 12;
        else if (modelId.includes("14b") || modelId.includes("15b")) paramSize = 14;
        else if (modelId.includes("32b")) paramSize = 32;
        else if (modelId.includes("70b") || modelId.includes("72b")) paramSize = 70;
    }
    
    if (paramSize !== null) {
        // Check for 32B or 70B (VRAM > 10GB / Over 11.5GB safe limit)
        if (paramSize > 15) {
            alert(`❌ 拦截：该模型参数量 (${paramSize}B) 过大，在您的 16GB 内存设备上会造成显存枯竭与系统极其严重卡顿。已自动拦截，建议选择 14B 以下的 4-bit 量化版本。`);
            return;
        }
        // Check for 9B ~ 15B (VRAM ~ 6GB to 10GB)
        if (paramSize > 8) {
            const confirmed = confirm(`⚠️ 提示：该模型尺寸较大（估算需要约 ${Math.round(paramSize * 0.6 + 1.0)}GB 显存）。您的 Mac 内存为 16GB，运行此模型时如果同时开启其他中重度应用，系统可能会产生卡顿（Memory Swap）。\n\n是否依然确认启动下载？`);
            if (!confirmed) return;
        }
    }
    
    try {
        const response = await fetch('/api/download', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ service: service, model_id: modelId })
        });
        
        const data = await response.json();
        if (response.ok) {
            alert(`📥 模型下载任务已成功在后台拉起！\n\n可点击输入框右侧的「进度」按钮实时刷新下载控制台终端日志。`);
            pollDownloadStatuses();
        } else {
            alert(`❌ 触发下载失败: ${data.detail || "未知错误"}`);
        }
    } catch (e) {
        alert(`❌ 网络错误: ${e.message}`);
    }
}

// Hugging Face model discovery variables
let activeHFService = null;
let hfModelsData = [];

// Open Hugging Face Discovery Modal
async function openHFDiscovery(service) {
    activeHFService = service;
    document.getElementById('hf-discovery-modal').classList.add('active');
    
    const title = document.getElementById('hf-modal-title');
    title.innerText = service === 'mlx' ? '探索 Hugging Face 最新 MLX 兼容模型' : '探索 Hugging Face 最新 GGUF 模型';
    
    // Clear tabs active state, set All as active
    const tabs = document.querySelectorAll('.hf-tab-btn');
    tabs.forEach((btn, idx) => {
        if (idx === 0) {
            btn.classList.add('active-tab');
            btn.style.background = '';
            btn.style.color = '';
            btn.style.border = '';
        } else {
            btn.classList.remove('active-tab');
            btn.style.background = 'rgba(255,255,255,0.04)';
            btn.style.color = 'var(--text-secondary)';
            btn.style.border = '1px solid rgba(255,255,255,0.08)';
        }
    });
    
    const container = document.getElementById('hf-models-list-container');
    container.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 3rem;">⚡ 正在建立与 Hugging Face 的连接，实时抓取最新模型...</div>';
    
    try {
        const response = await fetch(`/api/huggingface/trending?service=${service}`);
        const data = await response.json();
        if (response.ok) {
            hfModelsData = data;
            renderHFModels(hfModelsData);
        } else {
            container.innerHTML = `<div style="text-align: center; color: var(--accent-red); padding: 3rem;">❌ 获取失败: ${data.detail || "接口响应错误"}</div>`;
        }
    } catch (e) {
        container.innerHTML = `<div style="text-align: center; color: var(--accent-red); padding: 3rem;">❌ 网络连接失败: ${e.message}</div>`;
    }
}

// Close Discovery Modal
function closeHFDiscovery() {
    document.getElementById('hf-discovery-modal').classList.remove('active');
}

// Tab filtering logic
function filterHFModels(company) {
    // Update Tab style
    const tabs = document.querySelectorAll('.hf-tab-btn');
    const tabMap = ['All', 'Alibaba', 'Meta', 'Google', 'Microsoft', 'DeepSeek', 'Mistral', 'Other'];
    const idx = tabMap.indexOf(company);
    
    tabs.forEach((btn, i) => {
        if (i === idx) {
            btn.classList.add('active-tab');
            btn.style.background = '';
            btn.style.color = '';
            btn.style.border = '';
        } else {
            btn.classList.remove('active-tab');
            btn.style.background = 'rgba(255,255,255,0.04)';
            btn.style.color = 'var(--text-secondary)';
            btn.style.border = '1px solid rgba(255,255,255,0.08)';
        }
    });
    
    if (company === 'All') {
        renderHFModels(hfModelsData);
    } else {
        const filtered = hfModelsData.filter(m => m.company === company);
        renderHFModels(filtered);
    }
}

// Render model items inside modal
function renderHFModels(models) {
    const container = document.getElementById('hf-models-list-container');
    container.innerHTML = '';
    
    if (!models || models.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: var(--text-muted); padding: 3rem;">暂无该分类的最新适配模型。</div>';
        return;
    }
    
    models.forEach(model => {
        const item = document.createElement('div');
        item.style.background = 'rgba(255, 255, 255, 0.02)';
        item.style.border = '1px solid rgba(255, 255, 255, 0.05)';
        item.style.padding = '0.8rem 1rem';
        item.style.borderRadius = '8px';
        item.style.display = 'flex';
        item.style.justifyContent = 'space-between';
        item.style.alignItems = 'center';
        item.style.gap = '1rem';
        
        let color = '#2ecc71';
        let isUnsupported = false;
        if (model.suitability === 'heavy') {
            color = '#f1c40f';
        } else if (model.suitability === 'unsupported') {
            color = '#e74c3c';
            isUnsupported = true;
        }
        
        const capTags = model.capabilities.map(cap => 
            `<span style="background: rgba(52, 152, 219, 0.08); color: #3498db; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(52, 152, 219, 0.15); font-weight: 500;">💡 ${cap}</span>`
        ).join(' ');

        const gatedBadge = model.gated 
            ? `<span style="background: rgba(231, 76, 60, 0.08); color: #e74c3c; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(231, 76, 60, 0.15); font-weight: 600;">🔒 需协议授权</span>`
            : `<span style="background: rgba(46, 204, 113, 0.08); color: #2ecc71; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(46, 204, 113, 0.15); font-weight: 500;">🔓 开源直拉</span>`;

        item.innerHTML = `
            <div style="flex: 1; min-width: 0;">
                <h4 style="font-size: 0.9rem; color: #fff; margin: 0 0 0.35rem 0; word-break: break-all;">${model.id}</h4>
                <div style="display: flex; flex-wrap: wrap; gap: 0.6rem; font-size: 0.72rem; color: var(--text-secondary); margin-bottom: 0.35rem;">
                    <span>📥 ${model.downloads.toLocaleString()} 下载</span>
                    <span>❤️ ${model.likes.toLocaleString()} 点赞</span>
                    <span>📅 更新: ${model.update_date || '未知'}</span>
                    <span>🏷️ 系列: <strong>${model.model_family}</strong></span>
                    <span>👤 上传: <strong>${model.author}</strong></span>
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 0.4rem; font-size: 0.7rem; color: var(--text-secondary); margin-bottom: 0.35rem;">
                    <span style="background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.05);">💿 格式: <strong>${model.format}</strong></span>
                    <span style="background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.05);">🔩 量化: <strong>${model.quantization}</strong></span>
                    <span style="background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.05);">📊 规模: <strong>${model.param_size}</strong></span>
                    <span style="background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(255,255,255,0.05);">⚖️ 协议: <strong>${model.license}</strong></span>
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 0.4rem; font-size: 0.7rem; color: var(--text-secondary); line-height: 1.6;">
                    ${gatedBadge}
                    <span style="background: rgba(46, 204, 113, 0.08); color: #2ecc71; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(46, 204, 113, 0.15); font-weight: 500;">📖 上下文: <strong>${model.context_window}</strong></span>
                    <span style="background: rgba(52, 152, 219, 0.08); color: #3498db; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(52, 152, 219, 0.15); font-weight: 500;">🚀 速度: <strong>${model.speed_est}</strong></span>
                    <span style="background: rgba(155, 89, 182, 0.08); color: #9b59b6; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(155, 89, 182, 0.15); font-weight: 500;">📦 下载: <strong>${model.download_size}</strong></span>
                    <span style="background: rgba(241, 196, 15, 0.08); color: #f1c40f; padding: 2px 6px; border-radius: 4px; border: 1px solid rgba(241, 196, 15, 0.15); font-weight: 500;">📈 满载增幅: <strong>+${model.kv_overhead}GB</strong></span>
                    ${capTags}
                </div>
            </div>
            <div style="display: flex; align-items: center; gap: 1rem; flex-shrink: 0;">
                <span style="font-size: 0.8rem; font-weight: 500; color: ${color}; whitespace: nowrap;">
                    ${model.suitability_desc}
                </span>
                <button class="action-btn" ${isUnsupported ? 'disabled style="opacity:0.35; cursor:not-allowed;" title="硬件不支持"' : ''} onclick="fillDownloadModel('${model.id}')" style="padding: 0.35rem 0.75rem; font-size: 0.8rem; height: auto;">
                    一键拉取
                </button>
            </div>
        `;
        
        container.appendChild(item);
    });
}

// Copy clicked HF Model ID to target input and close modal
function fillDownloadModel(modelId) {
    if (!activeHFService) return;
    
    // Check if the target GGUF model contains unsloth or standard tags
    // For GGUF on Ollama, it must be pulled via tag or hf.co domain
    // Ollama supports pulling from Hugging Face via: ollama run hf.co/username/reponame:quantization
    // Since HF repo tags contain specific GGUF quant versions (e.g. Q4_K_M), we fill it directly.
    let targetId = modelId;
    if (activeHFService === 'ollama' && !modelId.startsWith("hf.co/")) {
        // Automatically wrap with hf.co/ prefix to make it pullable via Ollama!
        targetId = `hf.co/${modelId}`;
    }
    
    document.getElementById(`download-input-${activeHFService}`).value = targetId;
    closeHFDiscovery();
}



