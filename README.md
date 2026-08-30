# Custom Open-Source LLM Cost & Routing Gateway

A high-performance, lightweight, OpenAI-compatible API gateway designed to orchestrate multiple LLM providers. By treating cost, latency, and quality as a joint optimization target, this gateway routes simple requests to cheaper models, escalates complex queries to frontier models, implements strict multi-provider failover, and provides structured cost logging.

---

## 🎯 Core Use Cases

### 1. Automated Cost Optimization (LLM Tiering)
* **Problem:** Running every single prompt through high-end frontier models like GPT-4o burns through engineering budgets on simple requests (e.g., *"Summarize this 3-sentence email"* or *"Say hello"*).
* **Gateway Solution:** The gateway automatically runs a localized heuristic check. Basic structural tasks, casual chat interactions, and short-context prompts are routed to ultra-cheap commodity models (e.g., `gpt-4o-mini`). It reserves expensive frontier models exclusively for long-context workloads or prompts matching specific complex keywords (e.g., *"optimize"*, *"cryptography"*).

### 2. Local/Self-Hosted Migration & Hybrid Cloud Strategies
* **Problem:** Teams want to transition workloads away from paid cloud APIs to private, open-weight models hosted locally on vLLM or Ollama (e.g., Llama 3) to protect data privacy and cut costs, but migrating production applications all at once introduces significant downtime risk.
* **Gateway Solution:** Acts as a hybrid cloud controller. You can set your local self-hosted instance as the primary target for specific low-tier routing rules while keeping mature commercial cloud providers as an instant fallback layer. This allows teams to safely scale and stress-test on-premise infrastructure without breaking client applications.

### 3. High-Availability & Graceful Rate-Limit Mitigation
* **Problem:** High-throughput enterprise workflows frequently run into downstream rate limits (`HTTP 429 Too Many Requests`) or sudden provider-specific regional service degradation (`HTTP 5xx`). 
* **Gateway Solution:** The gateway abstracts client-side retry logic. If a primary provider drops or pushes back a rate limit error, the request instantly cascades down your pre-configured `fallback_chain` in real time. The client application experiences zero downtime or disruption, maintaining high application availability.

### 4. Cost Attribution & Internal Multi-Tenant Billing
* **Problem:** When multiple engineering teams or microservices share a single corporate API key, it becomes virtually impossible to track exactly which service or internal tool is running up the bill.
* **Gateway Solution:** Because the gateway interceptively processes every incoming call and flushes metrics to an append-only `costs.jsonl` sink, it creates a clean audit trail. Data platforms can ingest this structured file into tools like Prometheus, Grafana, or PostgreSQL to build granular dashboards breaking down spend by model, latency, and throughput across internal services.

---

## 🚀 Key Architectural Features

* **OpenAI-Compatible Interface:** Drop-in replacement for existing applications—simply swap your `base_url` to route through the gateway.
* **Intelligent Rule-Based Routing:** Evaluation of prompt complexity using localized heuristic rule checking (keywords and token counts) without execution overhead.
* **Zero-Dependency Token Estimation:** Uses a lightning-fast offline character-to-token approximation (`~4 chars/token`). Avoids network-bound startup delays or heavy downloads caused by vendor-specific packages like `tiktoken`.
* **Multi-Provider Fallback Chain:** Automatically catches downstream provider outages or rate limits (`429`, `5xx`) and instantly cascades through a configurable fallback chain.
* **Extensible Caching Layer:** Ship-ready in-memory caching system with an explicitly abstracted interface designed for sliding out to distributed asynchronous Redis clusters.
* **Non-Blocking Cost Metrics:** Structured, append-only JSON logging capturing exact latency, model-tier costs, and token usage metrics for downstream parsing.

---

## 📂 Project Structure

```text
├── providers/        # Provider abstraction layers (OpenAI, Anthropic, local vLLM)
├── cache.py          # Exact-match in-memory cache and async Redis stubs
├── config.py         # Configuration parsing & typed validation via Pydantic
├── costs.py          # Request cost estimations and high-throughput logging sinks
├── main.py           # FastAPI entry point managing async request/response lifecycles
└── router.py         # Token counting heuristics and routing policy engines
```

---

## 🛠️ Getting Started

### 1. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com
cd -custom-OSS-gateway-solution
pip install fastapi uvicorn pydantic pyyaml anyio
```

### 2. Configuration (`config.yaml`)

Create a `config.yaml` file in the root directory to define your LLM providers, costing parameters, routing logic tiers, and global fallbacks:

```yaml
providers:
  openai-fast:
    kind: "openai"
    model: "gpt-4o-mini"
    api_key_env: "OPENAI_API_KEY"
    cost_per_1k_input_tokens: 0.00015
    cost_per_1k_output_tokens: 0.0006
  openai-frontier:
    kind: "openai"
    model: "gpt-4o"
    api_key_env: "OPENAI_API_KEY"
    cost_per_1k_input_tokens: 0.0025
    cost_per_1k_output_tokens: 0.0010
  local-vllm:
    kind: "local"
    model: "meta-llama/Llama-3-8B-Instruct"
    base_url: "http://localhost:8000/v1"
    cost_per_1k_input_tokens: 0.0
    cost_per_1k_output_tokens: 0.0

routing:
  - name: "long-context-rule"
    max_input_tokens: 2000
    provider: "openai-frontier"
  - name: "complex-intent-keywords"
    keywords: ["analyze", "optimize", "benchmark", "cryptography"]
    provider: "openai-frontier"
  - name: "default-catch-all"
    provider: "openai-fast"

fallback_chain:
  - "openai-fast"
  - "local-vllm"

cache:
  backend: "memory"
  ttl_seconds: 3600
```

### 3. Running the Gateway

Start the async server using `uvicorn`:

```bash
uvicorn gateway.main:app --host 0.0.0.0 --port 8080 --reload
```

---

## 📡 API Usage

### Chat Completions Interface

To utilize the gateway's automatic intelligent routing logic, send a standard payload with `"model": "auto"` (or leave it out).

```bash
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "auto",
    "messages": [
      {"role": "user", "content": "Can you analyze this complex cryptography benchmark for me?"}
    ]
  }'
```

#### Bypassing the Router
If an application needs to enforce a specific model bypass, pass the configured provider name directly in the request body (e.g., `"model": "local-vllm"`).

---

## 📊 Analytics & Metrics Tracking

All request details are logged in a high-performance, append-only structured format (`costs.jsonl`), decoupling blocking I/O tracking loops using background worker thread processing pools (`anyio.to_thread`):

```json
{"ts": 1714839201.23, "provider": "openai-frontier", "model": "gpt-4o", "input_tokens": 120, "output_tokens": 450, "estimated_cost_usd": 0.00075, "latency_ms": 421.5, "cache_hit": false}
{"ts": 1714839245.88, "provider": "cache", "model": "gpt-4o", "input_tokens": 0, "output_tokens": 0, "estimated_cost_usd": 0.0, "latency_ms": 0.0, "cache_hit": true}
```

---

## 🛡️ License

This project is licensed under the MIT License.
