import json

from kdp_niche_radar import license as lic

DAY = 86400
PRODUCT = "kdp-niche-radar"


def test_valid_key_caches_and_returns_true(tmp_path):
    cache = tmp_path / "lic.json"
    ok = lic.verify("GOODKEY", PRODUCT, cache, now=1000.0, verifier=lambda k, p: True)
    assert ok is True
    saved = json.loads(cache.read_text())
    assert saved["key"] == "GOODKEY" and saved["verified_at"] == 1000.0


def test_invalid_key_returns_false(tmp_path):
    cache = tmp_path / "lic.json"
    assert lic.verify("BADKEY", PRODUCT, cache, now=1000.0, verifier=lambda k, p: False) is False
    assert not cache.exists()  # nothing cached for an invalid key


def test_network_down_with_fresh_cache_returns_true(tmp_path):
    cache = tmp_path / "lic.json"
    cache.write_text(json.dumps({"key": "GOODKEY", "verified_at": 1000.0}))

    def boom(k, p):
        raise RuntimeError("network down")

    # 10 days later, still within the 30-day grace window
    assert lic.verify("GOODKEY", PRODUCT, cache, now=1000.0 + 10 * DAY, verifier=boom) is True


def test_network_down_with_stale_cache_returns_false(tmp_path):
    cache = tmp_path / "lic.json"
    cache.write_text(json.dumps({"key": "GOODKEY", "verified_at": 1000.0}))

    def boom(k, p):
        raise RuntimeError("network down")

    assert lic.verify("GOODKEY", PRODUCT, cache, now=1000.0 + 31 * DAY, verifier=boom) is False


def test_network_down_no_cache_returns_false(tmp_path):
    cache = tmp_path / "lic.json"

    def boom(k, p):
        raise RuntimeError("network down")

    assert lic.verify("GOODKEY", PRODUCT, cache, now=1000.0, verifier=boom) is False
