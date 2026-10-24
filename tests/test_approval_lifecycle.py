"""
Integration test suite for the human-in-the-loop approval lifecycle.
Validates:
1. Pending -> Approved -> Polled decrypted response workflow
2. Pending -> Denied -> Polled refusal reason workflow
3. Role-Based Access Control (RBAC): Admin authorization required for reviews
4. Error resilience: Non-existent requests, model failures, unauthenticated polling
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.server import app
from core.cache import cache
from core.config import config


@pytest.fixture
def client():
    """Authenticated client with standard user token (Ollama authorized)."""
    cache.clear()
    c = TestClient(app)
    c.headers["Authorization"] = "Bearer sg_test_11a84f3cd789e023ba78cc"
    return c


@pytest.fixture
def admin_client():
    """Authenticated client with master administrator token."""
    cache.clear()
    c = TestClient(app)
    c.headers["Authorization"] = f"Bearer {config.SECRET_KEY}"
    return c


def test_approval_lifecycle_full_approved_flow(client, admin_client):
    """
    Validates complete lifecycle from submission through admin approval and client polling:
    1. Client submits high-risk prompt containing sensitive keywords (> 50 risk).
    2. Gateway intercepts and transitions to 'Pending Approval' state.
    3. Client polls request before authorization -> 'Pending'.
    4. Security Lead approves request via admin endpoint.
    5. Client polls request -> 'Approved' with decrypted LLM response and metadata.
    """
    high_risk_payload = {
        "model": "ollama/llama3",
        "messages": [
            {"role": "user", "content": "Admin credentials and password for system audit of user compliance@enterprise.org"}
        ]
    }

    # Step 1: Submit high-risk interaction
    res = client.post("/v1/chat/completions", json=high_risk_payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "Pending Approval"
    req_id = data["request_id"]
    assert req_id is not None
    assert data["risk_score"] > 50
    assert data["poll_url"] == f"/v1/requests/{req_id}"

    # Step 2: Poll immediately -> Status must be Pending with no response yet
    poll_1 = client.get(f"/v1/requests/{req_id}")
    assert poll_1.status_code == 200
    p1_data = poll_1.json()
    assert p1_data["status"] == "Pending"
    assert p1_data["response"] is None
    assert p1_data["reviewed_by"] is None

    # Step 3: Admin inspects pending approvals list
    approvals_res = admin_client.get("/api/approvals")
    assert approvals_res.status_code == 200
    approvals_data = approvals_res.json()
    assert any(item["request_id"] == req_id for item in approvals_data.get("pending", []))

    # Step 4: Admin approves the request (mocking upstream model completion)
    mock_approved_response = {
        "choices": [{"message": {"role": "assistant", "content": "Approved security audit explanation."}}],
        "usage": {"total_tokens": 42}
    }
    with patch("core.llm.ollama_client.OllamaClient.complete", return_value=mock_approved_response):
        approval_res = admin_client.post(
            f"/api/approve/{req_id}",
            json={"reviewer": "sec_lead", "reason": "Authorized penetration testing query"}
        )
        assert approval_res.status_code == 200
        app_json = approval_res.json()
        assert app_json["status"] == "Approved"
        assert app_json["response"] == "Approved security audit explanation."

    # Step 5: Client polls resolved request -> Status is Approved with decrypted completion
    poll_2 = client.get(f"/v1/requests/{req_id}")
    assert poll_2.status_code == 200
    p2_data = poll_2.json()
    assert p2_data["status"] == "Approved"
    assert p2_data["reviewed_by"] == "sec_lead"
    assert p2_data["response"] == "Approved security audit explanation."
    assert p2_data["tokens"] == 42


def test_approval_lifecycle_denied_flow(client, admin_client):
    """
    Validates complete lifecycle when a request is denied:
    1. Client submits high-risk prompt.
    2. Admin denies request with specific compliance reason.
    3. Client polls request -> 'Denied' with human-readable rationale.
    """
    payload = {
        "model": "ollama/llama3",
        "messages": [
            {"role": "user", "content": "Admin credentials and password review for root@internal-security.local"}
        ]
    }

    # Step 1: Submit high-risk interaction
    res = client.post("/v1/chat/completions", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "Pending Approval"
    req_id = data["request_id"]

    # Step 2: Admin denies request
    denial_reason = "Denied: Violates policy on credential inspection."
    deny_res = admin_client.post(
        f"/api/deny/{req_id}",
        json={"reviewer": "compliance_lead", "reason": denial_reason}
    )
    assert deny_res.status_code == 200
    assert deny_res.json()["status"] == "Denied"
    assert deny_res.json()["reason"] == denial_reason

    # Step 3: Client polls resolved request -> Status is Denied
    poll = client.get(f"/v1/requests/{req_id}")
    assert poll.status_code == 200
    p_data = poll.json()
    assert p_data["status"] == "Denied"
    assert p_data["reviewed_by"] == "compliance_lead"
    assert p_data["response"] == denial_reason


def test_approval_lifecycle_rbac_enforcement(client, admin_client):
    """Validates that unprivileged clients cannot approve or deny requests or inspect approval queues."""
    # 1. Non-admin client cannot access /api/approvals
    res_list = client.get("/api/approvals")
    assert res_list.status_code == 403
    assert "Forbidden" in res_list.json()["detail"]

    # 2. Non-admin client cannot approve requests
    res_app = client.post("/api/approve/any-fake-id", json={"reviewer": "rogue_user"})
    assert res_app.status_code == 403
    assert "Forbidden" in res_app.json()["detail"]

    # 3. Non-admin client cannot deny requests
    res_deny = client.post("/api/deny/any-fake-id", json={"reviewer": "rogue_user"})
    assert res_deny.status_code == 403
    assert "Forbidden" in res_deny.json()["detail"]

    # 4. Unauthenticated user cannot poll requests
    unauth_client = TestClient(app)
    res_poll_unauth = unauth_client.get("/v1/requests/any-id")
    assert res_poll_unauth.status_code == 401


def test_approval_lifecycle_edge_cases(client, admin_client):
    """Validates edge cases: missing IDs, model failures during approval execution."""
    # 1. Polling a non-existent request ID returns 404
    missing_poll = client.get("/v1/requests/non_existent_id_12345")
    assert missing_poll.status_code == 404
    assert "not found" in missing_poll.json()["detail"].lower()

    # 2. Approving non-existent request ID returns descriptive error
    missing_approve = admin_client.post("/api/approve/non_existent_id_12345")
    assert missing_approve.status_code == 200
    assert "error" in missing_approve.json()

    # 3. Model failure during approval sets queue status to 'Error'
    # First queue a request
    res = client.post("/v1/chat/completions", json={
        "model": "ollama/llama3",
        "messages": [{"role": "user", "content": "Admin credentials and password for audit of user secops@internal.org"}]
    })
    req_id = res.json()["request_id"]

    mock_error_resp = {"error": {"message": "Local Ollama service daemon unavailable"}}
    with patch("core.llm.ollama_client.OllamaClient.complete", return_value=mock_error_resp):
        app_err = admin_client.post(f"/api/approve/{req_id}", json={"reviewer": "sec_lead"})
        assert app_err.status_code == 200
        assert app_err.json()["status"] == "Error"
        assert "Ollama service daemon unavailable" in app_err.json()["error"]

    # Verify polling status shows Error
    poll_err = client.get(f"/v1/requests/{req_id}")
    assert poll_err.status_code == 200
    assert poll_err.json()["status"] == "Error"
