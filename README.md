# 🛡️ LLM Security Gateway Pro

[![Author](https://img.shields.io/badge/Author-Dhruv%20Patil-blue?style=for-the-badge&logo=github)](https://github.com/dhruuv-patil)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

A robust, enterprise-ready security middleware and analytics gateway designed to sit between client applications and Large Language Models (LLMs). This gateway enforces zero-trust safety principles, intercepts requests and completions in real-time, redacts PII, neutralizes prompt injections, and offers full auditability with live telemetry and admin controls.

---

## 🚀 Key Features

* **🛡️ Real-Time Prompt Injection Defense:** Heuristic pattern scanning and intent analysis to intercept and block adversarial jailbreak attempts (e.g., DAN, system prompt bypasses).
* **🔒 Automatic PII Masking & Redaction:** Automatically detects sensitive Personally Identifiable Information (emails, phone numbers, credit cards, SSNs) and anonymizes data before forwarding to upstream providers.
* **⚡ Dual-Interface Experience:**
  * **Interactive Chat UI & Live Event Stream:** FastAPI-powered web client with real-time WebSocket security event streaming.
  * **Admin Analytics & Governance Dashboard:** Streamlit-powered observability suite for token tracking, risk scores, cost monitoring, and human-in-the-loop approval workflows.
* **🛑 Output Guardrails & Leakage Prevention:** Validates LLM responses before delivery to prevent system prompt leakage, toxic completions, and hallucinations.
* **🔐 Encrypted Audit Trail:** Stores all query and completion logs with AES-Fernet encryption for compliance and security auditing.
* **🌐 Multi-Provider Flexibility:** Out-of-the-box integration with Groq (e.g., Llama 3.3 70B) and self-hosted local models via Ollama.

---

## 🛠️ Tech Stack

* **Core Runtime:** Python 3.10+
* **Backend API:** FastAPI & Uvicorn (Asynchronous, High-Performance)
* **Real-Time Streaming:** WebSockets
* **Analytics & Governance:** Streamlit, Pandas, Plotly Express
* **Validation & Schemas:** Pydantic V2
* **Cryptography:** Cryptography (Fernet symmetric encryption)
* **Database:** SQLite with robust query repository pattern
* **Containerization:** Docker & Docker Compose

---

## 📦 Quick Start Guide

### 1. Clone the Repository

```bash
git clone https://github.com/dhruuv-patil/llm-security-gateway.git
cd llm-security-gateway
```

### 2. Set Up a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Generate a secure Fernet encryption key:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Update your `.env` with your keys:
```env
# Database Configuration
DATABASE=llm_gateway.db

# Security & Encryption
ENCRYPTION_KEY=your_generated_fernet_key_here
SECRET_KEY=your_app_secret_token_here

# LLM Providers
GROQ_API_KEY=your_groq_api_key_here
OLLAMA_URL=http://localhost:11434

# Server Configuration
API_HOST=127.0.0.1
API_PORT=8000
```

### 4. Run the Services

You can run the Gateway API and the Admin Dashboard concurrently:

#### Option A: Run Gateway API & Web Chat Interface
```bash
python run_api.py
```
* **Interactive Chat & Live Telemetry:** Visit [http://127.0.0.1:8000](http://127.0.0.1:8000)
* **Interactive API Documentation:** Visit [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

#### Option B: Run Admin & Analytics Dashboard
```bash
python run_dashboard.py
```
* **Admin Dashboard:** Visit [http://127.0.0.1:8501](http://127.0.0.1:8501)

#### Option C: Run Terminal Client
```bash
python client.py
```

---

## 🐳 Docker Deployment

Run the gateway effortlessly with Docker:

```bash
# Build the Docker image
docker build -t llm-security-gateway .

# Run the container
docker run -p 8000:8000 --env-file .env llm-security-gateway
```

---

## 🖥️ API Usage

Route chat completion requests through the secure gateway endpoint:

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
     -H "Authorization: Bearer your_app_secret_token" \
     -H "Content-Type: application/json" \
     -d '{
           "model": "groq/llama-3.3-70b-versatile",
           "messages": [
             {"role": "user", "content": "How do I secure an enterprise LLM pipeline?"}
           ]
         }'
```

---

## 🛡️ Architecture & Security Pipeline

```mermaid
graph LR
    A[Client Request] --> B[Auth Layer]
    B --> C[Input Guardrails]
    C --> D[PII Masking]
    D --> E[LLM Provider - Groq / Ollama]
    E --> F[Output Guardrails]
    F --> G[Encrypted Logging]
    G --> H[Client Response]
```

1. **Authentication Layer:** Validates authorization tokens before allowing traffic.
2. **Input Guardrails:** Analyzes prompts for injection attempts, jailbreaks, and rule violations.
3. **PII Masking:** Detects and redacts sensitive entities (credit cards, emails, SSNs).
4. **LLM Provider Dispatch:** Dispatches sanitized prompts to Groq or local Ollama instances.
5. **Output Validation:** Validates responses to ensure system prompts and confidential data aren't leaked.
6. **Encrypted Persistence:** Secures request and response audit logs with AES encryption.

---

## 📂 Project Structure

```text
llm-security-gateway/
├── app/                        # Application Presentation Layer
│   ├── api/                    # FastAPI routes and Pydantic schemas
│   │   ├── routes.py           # Chat completions, WebSocket telemetry & approvals
│   │   └── schemas.py          # Request and response models
│   ├── dashboard/              # Streamlit Analytics & Governance dashboard
│   │   ├── dashboard_main.py   # Admin UI, charts, and metrics
│   │   └── ui_components.py    # Custom CSS & styling
│   ├── static/                 # Web UI frontend assets
│   │   ├── index.html          # Gateway chat & live WebSocket logs
│   │   ├── script.js           # Client-side WebSocket & chat logic
│   │   └── style.css           # Modern dark-mode interface styling
│   └── server.py               # FastAPI application factory
├── core/                       # Core Business & Security Logic
│   ├── config.py               # Central configuration & environment loader
│   ├── crypto.py               # AES Fernet encryption for data protection
│   ├── llm/                    # Upstream model connectors (Groq, Ollama)
│   └── security/               # Input & Output guardrail engines
├── data/                       # Data Persistence Layer
│   ├── database.py             # SQLite schema and connection manager
│   └── repository.py           # Log persistence and queue operations
├── Dockerfile                  # Production container definition
├── render.yaml                 # Infrastructure configuration for deployment
├── requirements.txt            # Python dependencies
├── run_api.py                  # API service entry point
├── run_dashboard.py            # Streamlit service entry point
├── client.py                   # CLI client for terminal testing
├── LICENSE                     # MIT License
└── README.md                   # Project documentation
```

---

## 📈 Roadmap

* [x] Real-time prompt injection detection and blocking
* [x] Automated PII scanning and redaction
* [x] WebSocket-powered live activity stream
* [x] Streamlit Admin Dashboard with token and expenditure analytics
* [x] Human-in-the-loop approval queue for flagged requests
* [ ] Semantic response caching for latency & cost optimization
* [ ] Vector database support for contextual guardrails
* [ ] Multi-tenant organization policies and rate limiting

---

## 📄 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.

---

## 👨‍💻 Author

**Dhruv Patil**
* GitHub: [@dhruuv-patil](https://github.com/dhruuv-patil)
* Project: [llm-security-gateway](https://github.com/dhruuv-patil/llm-security-gateway)
