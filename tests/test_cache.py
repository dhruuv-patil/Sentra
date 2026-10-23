import pytest
from core.cache import cache

def test_cache_lifecycle():
    model = "groq/llama-3.3-70b-versatile"
    prompt = "What is zero-trust security?"
    response = "Zero trust is a security model requiring continuous verification."

    # Clear previous
    cache.clear()
    assert cache.count() == 0
    assert cache.get(model, prompt) is None

    # Set cache entry
    cache.set(model, prompt, response, tokens=20, cost=0.0004)
    assert cache.count() == 1

    # Get cached entry
    cached = cache.get(model, prompt)
    assert cached is not None
    assert cached["response"] == response
    assert cached["tokens"] == 20
    assert cached["cache_hit"] is True

    # Case & whitespace normalization
    cached_whitespace = cache.get(model, "   What is zero-trust security?   ")
    assert cached_whitespace is not None

    # Clear cache
    cache.clear()
    assert cache.count() == 0
    assert cache.get(model, prompt) is None

def test_cache_tenant_isolation():
    """Proves one tenant can NEVER receive another tenant's cached completion."""
    model = "groq/llama-3.3-70b-versatile"
    prompt = "What is our internal Q3 revenue guidance?"
    tenant_a_response = "Tenant A Confidential Revenue: $14.2M."

    cache.clear()

    # Tenant A executes query and response is cached
    cache.set(model, prompt, tenant_a_response, tokens=35, cost=0.0007, tenant_id="tenant_alpha")

    # Tenant A gets their cached completion
    hit_a = cache.get(model, prompt, tenant_id="tenant_alpha")
    assert hit_a is not None
    assert hit_a["response"] == tenant_a_response

    # Tenant B queries with the EXACT same model and prompt: MUST BE A CACHE MISS
    hit_b = cache.get(model, prompt, tenant_id="tenant_beta")
    assert hit_b is None, "Tenant B leaked Tenant A's cached response!"

    # Unauthenticated/default tenant: MUST BE A CACHE MISS
    hit_default = cache.get(model, prompt, tenant_id="default")
    assert hit_default is None

def test_cache_parameter_isolation():
    """Proves deterministic request (temp=0.0) never shares cache with creative (temp=1.0)."""
    model = "groq/llama-3.3-70b-versatile"
    prompt = "Generate test code"
    
    cache.clear()
    cache.set(model, prompt, "Deterministic Output", tenant_id="t1", parameters={"temperature": 0.0})

    # Same tenant, same prompt, but temperature=1.0 -> cache miss
    cached_diff_temp = cache.get(model, prompt, tenant_id="t1", parameters={"temperature": 1.0})
    assert cached_diff_temp is None

    # Matching temperature=0.0 -> cache hit
    cached_same_temp = cache.get(model, prompt, tenant_id="t1", parameters={"temperature": 0.0})
    assert cached_same_temp is not None
    assert cached_same_temp["response"] == "Deterministic Output"

