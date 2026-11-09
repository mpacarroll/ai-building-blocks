"""A tiny in-memory lunch poll, built from revision 4 of the lunch poll spec.

This is demo code for the spec-bench evidence walkthrough, not a product. It
has no web layer, so the two browser criteria (AC2 taps, AC7 two seconds on
screen) stay unwritten. It also carries one real bug on purpose: when places
tie, tie_choices() offers every place, not only the tied ones (AC10).

Times are seconds since midnight so tests can pin a clock.
"""

POLL_MINUTES = 10
REMINDER_LEAD = 120  # seconds before close


class PollError(ValueError):
    pass


def hms(text: str) -> int:
    h, m, s = (int(x) for x in text.split(":"))
    return h * 3600 + m * 60 + s


class Outbox:
    """Collects emails instead of sending them."""

    def __init__(self):
        self.sent = []

    def send(self, to, subject, body):
        self.sent.append({"to": to, "subject": subject, "body": body})


class Poll:
    def __init__(self, organizer, places, team, opened_at, outbox, link="https://poll.example/p/1"):
        if not 2 <= len(places) <= 8:
            raise PollError("Add 2 to 8 places")
        self.organizer, self.places, self.team = organizer, list(places), list(team)
        self.opened_at, self.close_at, self.closed_at = opened_at, opened_at + POLL_MINUTES * 60, None
        self.outbox, self.link, self.votes, self._reminded = outbox, link, {}, False
        for member in self.team:
            outbox.send(member, "Lunch poll is open", f"Vote here: {link}")

    def status(self, now):
        if self.closed_at is not None and now >= self.closed_at:
            return "closed"
        return "closed" if now >= self.close_at else "open"

    def close(self, now):
        self.closed_at = now

    def vote(self, voter, place, now):
        if self.status(now) == "closed":
            raise PollError("This poll is closed")
        if place not in self.places:
            raise PollError(f"Unknown place {place!r}")
        self.votes[voter] = place   # a later vote replaces the earlier one

    def counts(self):
        out = {p: 0 for p in self.places}
        for place in self.votes.values():
            out[place] += 1
        return out

    def view(self, viewer, now):
        """What a person sees. Only the organizer of a closed poll sees names."""
        if viewer == self.organizer and self.status(now) == "closed":
            return {p: sorted(v for v, c in self.votes.items() if c == p) for p in self.places}
        return self.counts()

    def tie_choices(self):
        counts = self.counts()
        top = max(counts.values())
        if list(counts.values()).count(top) < 2:
            return []
        return list(self.places)   # BUG (deliberate, see module docstring): should be tied places only

    def tick(self, now):
        """Send the reminder once, REMINDER_LEAD seconds before close."""
        if not self._reminded and now >= self.close_at - REMINDER_LEAD and self.status(now) == "open":
            self._reminded = True
            for member in self.team:
                self.outbox.send(member, "Lunch poll closes in 2 minutes", f"Vote here: {self.link}")
