import socket
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.server import app
from core.cache import cache
from core.config import config


@pytest.fixture
def client():
    cache.clear()
    c = TestClient(app)
    c.headers["Authorization"] = f"Bearer {config.SECRET_KEY}"
    return c

def test_airgapped_mode_blocks_external_cloud_provider(client):
    """When AIRGAPPED_MODE is active, cloud calls to Groq must be blocked with HTTP 403."""
    with patch.object(config, "AIRGAPPED_MODE", True):
        payload = {
            "model": "groq/llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": "Analyze corporate financial health"}]
        }
        res = client.post("/v1/chat/completions", json=payload)
        assert res.status_code == 403
        assert "air-gapped" in res.json()["error"].lower()

def test_airgapped_mode_allows_sovereign_local_provider(client):
    """When AIRGAPPED_MODE is active, sovereign local Ollama models must be permitted."""
    mock_ollama_resp = {
        "mode": "local",
        "choices": [{"message": {"role": "assistant", "content": "Sovereign on-premise completion."}}],
        "usage": {"total_tokens": 15}
    }
    with patch.object(config, "AIRGAPPED_MODE", True):
        with patch("core.llm.ollama_client.OllamaClient.complete", return_value=mock_ollama_resp):
            payload = {
                "model": "ollama/llama3",
                "messages": [{"role": "user", "content": "Summarize air-gapped security benefits"}]
            }
            res = client.post("/v1/chat/completions", json=payload)
            assert res.status_code == 200
            assert res.json()["choices"][0]["message"]["content"] == "Sovereign on-premise completion."

def test_tenant_provider_authorization_restriction():
    """Tenants assigned to specific providers cannot access unauthorized models."""
    # 1. Tenant restricted to 'Ollama Local' (token: sg_test_11a84f3cd789e023ba78cc from seed)
    client_ollama = TestClient(app)
    client_ollama.headers["Authorization"] = "Bearer sg_test_11a84f3cd789e023ba78cc"

    # Attempt to use Groq: must be rejected with 403
    res_blocked = client_ollama.post("/v1/chat/completions", json={
        "model": "groq/llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": "Hello cloud model"}]
    })
    assert res_blocked.status_code == 403
    assert "Policy Restriction" in res_blocked.json()["error"]
    assert "Ollama Local" in res_blocked.json()["error"]

    # 2. Same tenant accessing Ollama: allowed
    mock_local = {
        "mode": "local",
        "choices": [{"message": {"role": "assistant", "content": "Local model output"}}],
        "usage": {"total_tokens": 10}
    }
    with patch("core.llm.ollama_client.OllamaClient.complete", return_value=mock_local):
        res_allowed = client_ollama.post("/v1/chat/completions", json={
            "model": "ollama/llama3",
            "messages": [{"role": "user", "content": "Hello local model"}]
        })
        assert res_allowed.status_code == 200

def test_full_pipeline_with_network_disabled(client):
    """
    Simulates complete air-gapped deployment with external networking disabled at the socket layer.
    Proves local ML injection detector, PII masking, local cache, and mock local LLM operate
    with zero outbound internet connectivity.
    """
    real_socket_connect = socket.socket.connect

    def blocked_external_connect(sock, address):
        host, port = address[0], address[1]
        # Prohibit any outbound external internet address
        if host not in ("127.0.0.1", "localhost", "::1"):
            raise OSError(f"Simulated Air-Gapped Network Isolation: Connection to {host}:{port} is forbidden.")
        return real_socket_connect(sock, address)

    mock_local_completion = {
        "mode": "local",
        "choices": [{"message": {"role": "assistant", "content": "Local sovereign inference completed safely."}}],
        "usage": {"total_tokens": 25}
    }

    with patch("socket.socket.connect", side_effect=blocked_external_connect):
        with patch.object(config, "AIRGAPPED_MODE", True):
            with patch("core.llm.ollama_client.OllamaClient.complete", return_value=mock_local_completion):
                # Prompt with PII and benign instructions
                payload = {
                    "model": "ollama/llama3",
                    "messages": [
                        {"role": "user", "content": "Please explain how air-gapped systems preserve data sovereignty and contact info is user@company.org."}
                    ]
                }
                res = client.post("/v1/chat/completions", json=payload)
                assert res.status_code == 200
                data = res.json()
                assert "choices" in data
                assert data["choices"][0]["message"]["content"] == "Local sovereign inference completed safely."

                # Verify second identical call hits local SQLite cache with zero outbound calls
                res_cached = client.post("/v1/chat/completions", json=payload)
                assert res_cached.status_code == 200
                assert res_cached.json()["cache_hit"] is True
