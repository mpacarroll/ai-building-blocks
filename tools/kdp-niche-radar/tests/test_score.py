from kdp_niche_radar import score


def test_scoring_is_deterministic_and_flags_golden():
    rows = [
        {"keyword": "a", "breadth": 6, "position": 1, "ok": True,
         "top8": [{"rating_count": 50}] * 8},          # high demand, low competition -> golden
        {"keyword": "b", "breadth": 2, "position": 9, "ok": True,
         "top8": [{"rating_count": 9000}] * 8},         # low demand, brutal competition
        {"keyword": "c", "ok": False, "error": "timeout"},  # failed fetch
    ]
    out = score.score_keywords(rows)
    assert [r["keyword"] for r in out] == ["a", "b", "c"]     # sorted; failed last
    assert out[0]["golden"] is True
    assert out[1]["golden"] is False
    assert out[2]["score"] is None                            # failed row carries None
    assert out[0]["competition"] == 50                        # median of top8 ratings


def test_zero_competition_does_not_crash():
    rows = [{"keyword": "z", "breadth": 3, "position": 1, "ok": True,
             "top8": [{"rating_count": 0}] * 8}]
    out = score.score_keywords(rows)
    assert out[0]["score"] is None       # undefined competition -> no score, not a crash
    assert out[0]["golden"] is False
