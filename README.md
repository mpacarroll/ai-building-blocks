# Become an AI Builder

Stop planning things and start building them. If you come from product, design, or engineering, this is how you cross the line into shipping real software yourself, with AI doing the typing. Watch specifications become working tools: the specs, the test-driven plans, and the finished thing, nothing hidden.

I'm Mick. I build software by writing specs precise enough that AI agents implement them without a single clarifying question — then I ship the result. This repo is that method, in public, on small tools you can actually use, so you can do it too. [Who's Mick? →](#whos-mick)

## The tools
- **[KDP Niche Radar](tools/kdp-niche-radar/)** — find low-competition book niches in under a minute. Runs entirely on your machine, no account, no tracking. Built spec-first with a test before every function.
- **[Spec Grader](tools/spec-grader/)** — grade a spec for ambiguity and testable requirements before you build from it. Deterministic, offline, CI-friendly. Point it at a spec and it tells you where an implementer would have to stop and ask a question. (It grades its own spec an A — and caught that the KDP Niche Radar spec needed numbered requirements to score well. Dogfooding works.)

## How to read this repo
1. Start with a **spec** in [`specs/`](specs/) — the complete description an implementer builds from.
2. Read the **plan** in [`plans/`](plans/) — the spec broken into bite-sized, test-first tasks.
3. Open the **tool** — every function had a failing test before it had code.

That order is the whole point. The spec is the source of truth; the code is downstream of it.

## The method
Spec-driven development, with these non-negotiables:
- **A spec so complete an agent can build from it** without guessing.
- **Test-first, always** — no production code without a failing test first (watch it fail, then make it pass).
- **Proof over claims** — every tool here is verified end to end, not just asserted to work.

Inspired by, and built on, the [superpowers](https://github.com/obra/superpowers) methodology by obra.

## Who's Mick
I'm Mick. I build things that ship and write about doing it with AI, in the open — the tools in this repo are the proof. Pro-AI, anti-hype, proof over promises, no résumé required. [More about Mick →](https://mpacarroll.github.io/ai-mick/#about)

Not affiliated with any employer.

## License
MIT — see [LICENSE](LICENSE).
