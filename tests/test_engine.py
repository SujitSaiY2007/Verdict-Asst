from verdict.engine import _cache_key


def test_cache_key_is_stable_and_context_specific():
    assert _cache_key("ask", "hello") == _cache_key("ask", "hello")
    assert _cache_key("ask", "hello") != _cache_key("debug", "hello")
    assert _cache_key("ask", "hello") != _cache_key("ask", "hello!")
    assert _cache_key("ask", "hello", False) != _cache_key("ask", "hello", True)
