"""Detect ambiguous language in a spec — the words that make an implementer
guess. Deterministic and offline: a curated lexicon of weasel words and hedges,
grouped by why each one hurts a spec. No LLM required.

This is the heart of a "zero-edit" spec: every flagged term is a place an agent
would have to stop and ask a question.
"""
import re

# term (lowercased) -> (category, why it is ambiguous)
LEXICON = {
    # unmeasurable qualities — say the number instead
    "fast": ("unmeasurable", "State the latency or throughput, not 'fast'."),
    "slow": ("unmeasurable", "Give the threshold you mean."),
    "quick": ("unmeasurable", "State the actual time budget."),
    "efficient": ("unmeasurable", "Efficient by what measure? Give the target."),
    "scalable": ("unmeasurable", "To what load? State the number."),
    "robust": ("unmeasurable", "Name the failures it must survive."),
    "secure": ("unmeasurable", "Against which threats? Be specific."),
    "user-friendly": ("unmeasurable", "Describe the behavior, not the adjective."),
    "intuitive": ("unmeasurable", "Unmeasurable. Describe the interaction."),
    "seamless": ("unmeasurable", "Describe what the user does and sees."),
    "high performance": ("unmeasurable", "Give the performance number."),
    "high-performance": ("unmeasurable", "Give the performance number."),
    # vague qualifiers — an implementer cannot verify these
    "appropriate": ("vague-qualifier", "Appropriate by whose judgment? Define it."),
    "as appropriate": ("vague-qualifier", "Define the actual rule."),
    "as needed": ("vague-qualifier", "Needed when? State the condition."),
    "where applicable": ("vague-qualifier", "State exactly where it applies."),
    "reasonable": ("vague-qualifier", "Give the concrete bound."),
    "sufficient": ("vague-qualifier", "Sufficient for what? Quantify."),
    "adequate": ("vague-qualifier", "Quantify what 'adequate' means."),
    "optimal": ("vague-qualifier", "Optimal against which objective?"),
    "properly": ("vague-qualifier", "Define 'properly' as a checkable rule."),
    "gracefully": ("vague-qualifier", "Say exactly what happens on failure."),
    # hedges — commitment missing
    "should probably": ("hedge", "Decide: must it or not?"),
    "ideally": ("hedge", "Is it required or not? Remove the hedge."),
    "if possible": ("hedge", "State whether it is required."),
    "might": ("hedge", "Specify the actual condition."),
    "maybe": ("hedge", "Decide and state it."),
    "some": ("hedge", "How many? Be specific."),
    "several": ("hedge", "Give the count."),
    "various": ("hedge", "Enumerate them."),
    "many": ("hedge", "How many? Quantify."),
    "few": ("hedge", "How few? Quantify."),
    # open-ended — the spec trails off
    "etc": ("open-ended", "Enumerate the full list; 'etc' hides requirements."),
    "and so on": ("open-ended", "List the rest explicitly."),
    "and/or": ("open-ended", "Pick one, or state both cases separately."),
    "tbd": ("incomplete", "A spec with TBD is not buildable yet."),
    "todo": ("incomplete", "Resolve before this spec is done."),
}

_PATTERNS = [(term, re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.I)) for term in LEXICON]


def find_ambiguities(text: str) -> list:
    """Return a list of {line, term, category, why} for every ambiguous term."""
    flags = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for term, pat in _PATTERNS:
            if pat.search(line):
                category, why = LEXICON[term]
                flags.append({"line": lineno, "term": term, "category": category, "why": why})
    return flags
