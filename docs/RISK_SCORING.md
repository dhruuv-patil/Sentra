# Risk Scoring Specification

**Component:** `InputGuards.calculate_risk_score`  
**Reference File:** [`core/security/input_guards.py`](file:///Users/dhruvpatil/Projects/llm-security-gateway-main/core/security/input_guards.py)

---

## 1. Overview

The Adversarial Risk Score is a deterministic, bounded heuristic metric $[0, 100]$ computed by the gateway to quantify the exposure and security risk of an incoming interaction before it is dispatched to upstream LLMs.

Prompts scoring above the policy threshold ($\text{Score} > 50$) trigger the **Human-in-the-Loop (HITL)** governance gate, placing the transaction in a pending quarantine state until an authorized security administrator reviews and explicitly approves or denies it.

---

## 2. Mathematical Formulation

The risk score $S(P)$ for a prompt $P$ is calculated as the sum of weighted risk signals, bounded at 100:

$$S(P) = \min\left(100, S_{\text{keywords}}(P) + S_{\text{injection}}(P) + S_{\text{pii}}(P)\right)$$

### 2.1 Keyword Risk Signals ($S_{\text{keywords}}$)

Keyword signals identify high-value security concepts and credential identifiers using word-boundary regular expressions on lowercased input:

| Keyword Pattern | Weight | Description |
|:---|:---:|:---|
| `\b(private\s+key\|confidential\|credentials?)\b` | **+25** | High-sensitivity secrets, private keys, or confidentiality indicators |
| `\bpassword\b` | **+20** | Authentication secrets and password inquiries |
| `\bsecret\b` | **+15** | Generic secret or undisclosed key references |
| `\badmin(?:istrator)?\b` | **+10** | Elevated administrative role references |

*Note:* Keywords are cumulative. A prompt containing both `admin` and `password` receives $10 + 20 = +30$.

### 2.2 Adversarial Injection Signals ($S_{\text{injection}}$)

| Signal | Weight | Description |
|:---|:---:|:---|
| `detect_prompt_injection(P) == True` | **+50** | Matches prompt injection heuristics, jailbreaks, or decoded Base64 payloads |

### 2.3 Personally Identifiable Information ($S_{\text{pii}}$)

For every distinct category of detected PII (Email, SSN, Credit Card, Phone Number, API Key, JWT Token):

$$S_{\text{pii}} = 15 \times N_{\text{distinct\_pii\_types}}$$

* Examples:
  * 1 email address: $+15$
  * 1 email address and 1 SSN: $15 \times 2 = +30$
  * 3 email addresses: $+15$ (scored per *category*, not occurrence, preventing artificial score inflation)

---

## 3. Thresholds and Action Matrix

| Score Range | Classification | Gateway Action |
|:---:|:---:|:---|
| **$0 - 25$** | **Low Risk** | Forwarded immediately to Response Cache or Upstream Dispatcher. |
| **$26 - 50$** | **Medium Risk** | Sanitized (PII masked), logged to audit trail, forwarded to Upstream Dispatcher. |
| **$51 - 100$** | **High Risk** | **Quarantined.** Placed in `approval_queue` with status `Pending`. Returns HTTP 200 with `status: "Pending Approval"` and polling URL `/v1/requests/{request_id}`. |

*Exception:* If a prompt triggers hard prompt injection detection, it is immediately rejected with HTTP 403 Forbidden before reaching the queue.

---

## 4. Multi-Turn / Multi-Message Aggregation

For multi-message conversations (e.g., standard OpenAI `messages` array), the gateway computes the score across all conversation turns:

$$S_{\text{conversation}} = \max_{m \in \text{messages}} S(m.\text{content})$$

This guarantees that an attacker cannot bury sensitive keywords or credentials in an earlier turn (`messages[0]`) to evade the policy threshold.

---

## 5. Known Limitations & False-Positive Profiles

1. **Benign Technical Discussions:** Legitimate queries regarding security operations (e.g. *"How does an administrator reset a user password securely?"*) match `admin` (+10) and `password` (+20) = 30. Mentioning a sample email address adds +15 = 45. Mentioning "confidential" pushes the score to 70, triggering human review.
2. **Context Blindness:** Regex-based keyword matching cannot distinguish between an attacker demanding credentials versus a defensive engineer analyzing log sanitization.
3. **Mitigation:** In Phase 3, an ML-based classifier (TF-IDF + Logistic Regression) complements the heuristic score with continuous semantic probability estimation.
