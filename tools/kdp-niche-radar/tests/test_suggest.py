from kdp_niche_radar import suggest


def test_expand_seeds_ranks_by_breadth_excludes_seed_caps_limit():
    # a stub suggest_fn: each query returns some keywords; breadth = how many
    # distinct queries a keyword shows up in.
    # keys must be queries expand_seeds actually generates: the seed itself and
    # "<seed> <modifier>" (workbook is a modifier). "sobriety workbook" appears
    # in two generated queries -> breadth 2.
    corpus = {
        "sobriety journal": ["sobriety journal", "sobriety workbook", "sobriety journal for women"],
        "sobriety journal workbook": ["sobriety workbook", "sobriety planner"],
    }

    def stub(q):
        return corpus.get(q, [])

    out = suggest.expand_seeds("sobriety journal", suggest_fn=stub, limit=10)
    assert isinstance(out, list) and all(isinstance(t, tuple) and len(t) == 2 for t in out)
    kws = [k for k, _ in out]
    assert "sobriety journal" not in kws  # seed itself excluded
    # "sobriety workbook" appears in two queries -> breadth 2, should outrank breadth-1 items
    assert out[0][0] == "sobriety workbook" and out[0][1] == 2
    # sorted descending by breadth
    breadths = [b for _, b in out]
    assert breadths == sorted(breadths, reverse=True)


def test_expand_seeds_respects_limit():
    def stub(q):
        return [f"kw{i}" for i in range(50)]

    out = suggest.expand_seeds("seed", suggest_fn=stub, limit=5)
    assert len(out) == 5
