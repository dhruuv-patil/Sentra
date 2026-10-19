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
