# 🛡️ LLM Security Gateway Pro

[![Author](https://img.shields.io/badge/Author-Dhruv%20Patil-blue?style=for-the-badge&logo=github)](https://github.com/dhruuv-patil)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Tests](https://img.shields.io/badge/Tests-15%20Passing-success?style=for-the-badge&logo=pytest&logoColor=white)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

An enterprise-grade, high-performance security middleware and observability platform designed to sit between client applications and Large Language Models (LLMs). This gateway enforces zero-trust safety principles, intercepts requests and completions in real-time, redacts Personally Identifiable Information (PII), neutralizes prompt injection and jailbreaks, serves ultra-low latency cached completions, and offers complete human-in-the-loop governance with AES-encrypted audit trails.

---

## 🚀 Key Features

* **🛡️ Multi-Vector Prompt Injection Defense:**
  * Heuristic pattern matching against adversarial jailbreaks (e.g. DAN, system override, format delimiters).
  * Automatic Base64 payload decoding and recursive inspection to block obfuscated attacks.
* **🔒 Automatic PII Anonymization & Redaction:**
  * Automatically detects and sanitizes sensitive data (Emails, SSNs, Credit Cards, Phone Numbers, API Keys, and JWTs) replacing them with `[ENTITY_REDACTED]` tokens prior to forwarding to upstream LLMs.
* **⚡ Ultra-Fast Response Caching Engine:**
  * Exact and normalized prompt matching via SHA-256 hash caching.
  * Yields sub-millisecond response latency and **0 token expenditure** on identical safe interactions.
* **⚖️ Complete Human-in-the-Loop (HITL) Governance:**
  * Automatically routes high-risk interactions (Risk Score > 50) to the administrator approval queue.
  * Administrators can review, **Approve & Execute**, or **Deny** requests from the Streamlit dashboard.
  * Asynchronous client polling endpoint (`GET /v1/requests/{request_id}`) allowing downstream consumers to retrieve resolved completions.
* **🛑 Output Guardrails & System Leakage Prevention:**
  * Validates model completions with boundary-enforced regex to prevent system prompt leakage, internal instruction disclosures, and policy violations without false positives on harmless terms.
* **🔐 AES-Fernet Encrypted Audit Trail:**
  * Encrypts interaction logs and model completions at rest using AES-Fernet cryptography.
* **🌐 Unified Multi-Provider Routing:**
  * Seamlessly dispatches requests to **Groq** (Llama 3.3 70B, Llama 3.1 8B, Mixtral 8x7B) or local **Ollama** models (`ollama/llama3`, `ollama/mistral`).
* **📊 Dual-Interface Experience:**
  * **Interactive Web Chat & Live Telemetry:** Web UI with real-time WebSocket security feed.
  * **Streamlit Admin & Analytics Dashboard:** High-level metrics, token tracking, cache controls, and review queue.

---

## 🛠️ Tech Stack

* **Core Runtime:** Python 3.10+
* **Backend Framework:** FastAPI & Uvicorn (Asynchronous, High-Performance)
* **Real-Time Telemetry:** WebSockets
* **Governance & Analytics:** Streamlit, Pandas, Plotly Express
* **Validation & Schemas:** Pydantic V2
* **Cryptography:** Cryptography (Fernet symmetric encryption)
* **Database & Concurrency:** SQLite in WAL (Write-Ahead Logging) mode with busy timeout handling
* **Testing:** Pytest (15 automated unit and integration tests)
* **Containerization:** Docker & Docker Compose

---

## 📦 Quick Start Guide

### 1. Clone the Repository

```bash
git clone https://github.com/dhruuv-patil/llm-security-gateway.git
cd llm-security-gateway
```

### 2. Set Up a Virtual Environment & Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create your `.env` file:

```bash
cp .env.example .env
```

Generate a secure Fernet encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Sample `.env`:
```env
# Database Configuration
DATABASE=llm_gateway.db

# Security & Encryption
ENCRYPTION_KEY=your_generated_fernet_key_here
SECRET_KEY=your_app_secret_token_here

# LLM Providers
# Optional: Add your live Groq API key (starts with gsk_) or run in verified demo mode
GROQ_API_KEY=
OLLAMA_URL=http://localhost:11434

# Server Configuration
API_HOST=127.0.0.1
API_PORT=8000
```

### 4. Run the Services

#### Option A: Run Gateway API & Web Chat Interface
```bash
python run_api.py
```
* **Interactive Chat & Live Telemetry:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Interactive API Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

#### Option B: Run Admin & Governance Dashboard
```bash
python run_dashboard.py
```
* **Streamlit Admin Dashboard:** [http://127.0.0.1:8501](http://127.0.0.1:8501)

#### Option C: Run Terminal CLI Client
```bash
python client.py
```

---

## 🧪 Running Automated Tests

Run the complete test suite covering input guards, output guards, encryption, caching, and API endpoints:

```bash
pytest tests/ -v
```

---

## 🛡️ Gateway Security Flow

```mermaid
graph TD
    A[Client Request] --> B[Input Guardrails: Injection & Jailbreak Scan]
    B -->|Injection Detected| C[HTTP 403 Forbidden]
    B -->|Passed| D[PII Detection & Automatic Masking]
    D --> E{Risk Score > 50?}
    E -->|Yes| F[Approval Queue: Admin Review]
    F -->|Approved| G[Provider Dispatcher: Groq / Ollama]
    F -->|Denied| H[Request Marked Denied]
    E -->|No| I{In Gateway Cache?}
    I -->|Hit| J[Instant Response: 0 Tokens, Sub-ms Latency]
    I -->|Miss| G
    G --> K[Output Guardrails: Leakage & Safety Scan]
    K -->|Violation| L[HTTP 403 Output Blocked]
    K -->|Passed| M[Write to Cache & Encrypted SQLite Audit]
    M --> N[Client Response]
```

---

## 🖥️ API Reference

### 1. Chat Completion (`POST /v1/chat/completions`)

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
     -H "Content-Type: application/json" \
     -d '{
           "model": "groq/llama-3.3-70b-versatile",
           "messages": [
             {"role": "user", "content": "How do I secure enterprise AI pipelines?"}
           ]
         }'
```

### 2. Poll Pending Approval (`GET /v1/requests/{request_id}`)

```bash
curl "http://localhost:8000/v1/requests/0ac20ab8-3833-49fa-96e5-7decf0a9e568"
```

### 3. Health & Telemetry (`GET /api/health`)

```bash
curl "http://localhost:8000/api/health"
```

---

## 📂 Project Structure

```text
llm-security-gateway/
├── app/                        # Web Application & Routing Layer
│   ├── api/                    # API route controllers & Pydantic schemas
│   │   ├── routes.py           # Core endpoints, WebSocket telemetry & approvals
│   │   └── schemas.py          # Strict Pydantic models with validation
│   ├── dashboard/              # Streamlit Governance & Analytics
│   │   ├── dashboard_main.py   # Admin UI, charts, and approval actions
│   │   └── ui_components.py    # Dark-mode styling and UI components
│   ├── static/                 # Web UI assets
│   │   ├── index.html          # Gateway chat & live WebSocket logs
│   │   ├── script.js           # Client-side WebSocket & approval polling
│   │   └── style.css           # Responsive interface styles
│   └── server.py               # FastAPI application factory
├── core/                       # Core Security & Business Logic
│   ├── cache.py                # Response caching engine (SHA-256)
│   ├── config.py               # Central configuration loader
│   ├── crypto.py               # AES-Fernet symmetric encryption
│   ├── llm/                    # Upstream model integrations
│   │   ├── groq_client.py      # Groq cloud client with demo fallback
│   │   ├── ollama_client.py    # Local Ollama client
│   │   └── provider_dispatcher.py # Unified provider router
│   └── security/               # Guardrail evaluation engines
│       ├── input_guards.py     # Prompt injection, base64 & PII masking
│       └── output_guards.py    # Context-aware output guardrails
├── data/                       # Data Persistence Layer
│   ├── database.py             # SQLite WAL-mode connection manager
│   └── repository.py           # Audit logging and approval queue queries
├── tests/                      # Automated Test Suite
│   ├── test_api.py             # API route and lifecycle tests
│   ├── test_cache.py           # Response cache unit tests
│   ├── test_crypto.py          # Encryption / decryption tests
│   ├── test_input_guards.py    # Injection & PII masking tests
│   └── test_output_guards.py   # Output guardrail tests
├── .github/workflows/ci.yml    # Continuous Integration pipeline
├── Dockerfile                  # Production container definition
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Packaging metadata
├── run_api.py                  # API service entry point
├── run_dashboard.py            # Streamlit service entry point
├── client.py                   # Terminal CLI client
├── LICENSE                     # MIT License
└── README.md                   # Project documentation
```

---

## 📄 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.

---

## 👨‍💻 Author

**Dhruv Patil**
* GitHub: [@dhruuv-patil](https://github.com/dhruuv-patil)
* Project: [llm-security-gateway](https://github.com/dhruuv-patil/llm-security-gateway)
