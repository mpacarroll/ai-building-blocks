"""Acceptance tests for: Lunch poll idea, written from the revision 4 skeleton.

Started from `spec-bench export DIR --format pytest`. Each pin comment records
the criterion wording the test was written against. AC2 and AC7 need a browser
and are still the generated skeleton. AC9's pin comment was deleted by hand,
so spec-bench cannot tell whether that test is still current.
"""
import pytest

from lunch_poll import Outbox, Poll, PollError, hms

TEAM5 = ["ana", "ben", "cy", "dee", "eli"]


def poll(places=("A", "B", "C"), team=TEAM5, opened="12:00:00"):
    return Poll("ana", list(places), list(team), hms(opened), Outbox())


# spec-bench: AC1 fp=50eb9bc7c1
def test_ac1_any_team_member_can_start_a():
    for places in (["A"], [f"P{i}" for i in range(9)]):
        with pytest.raises(PollError, match="Add 2 to 8 places"):
            poll(places)
    assert poll(["A", "B", "C"]).status(hms("12:00:01")) == "open"


# spec-bench: AC2 fp=9be8e6ff5b
def test_ac2_a_voter_must_be_able_to():
    raise NotImplementedError("write the check for AC2")


# spec-bench: AC3 fp=07bacebb21
def test_ac3_a_voter_must_not_see_how():
    p = poll()
    for voter, place in (("ana", "A"), ("ben", "A"), ("cy", "B")):
        p.vote(voter, place, hms("12:01:00"))
    seen = p.view("ben", hms("12:02:00"))
    assert seen == {"A": 2, "B": 1, "C": 0}
    assert not any(name in str(seen) for name in TEAM5)


# spec-bench: AC4 fp=88483594ea
def test_ac4_the_organizer_must_see_who_voted():
    p = poll()
    for voter, place in (("ana", "A"), ("ben", "A"), ("cy", "B")):
        p.vote(voter, place, hms("12:01:00"))
    p.close(hms("12:05:00"))
    assert p.view("ana", hms("12:05:00")) == {"A": ["ana", "ben"], "B": ["cy"], "C": []}


# spec-bench: AC5 fp=d051928e82
def test_ac5_the_poll_must_close_automatically_10():
    p = poll(opened="12:00:00")
    assert p.status(hms("12:09:59")) == "open"
    assert p.status(hms("12:10:00")) == "closed"
    with pytest.raises(PollError):
        p.vote("ben", "A", hms("12:10:00"))


# spec-bench: AC6 fp=afbc3ee754
def test_ac6_a_voter_can_change_their_vote():
    p = poll()
    p.vote("ben", "A", hms("12:01:00"))
    p.vote("ben", "B", hms("12:02:00"))
    assert p.counts()["B"] == 1 and p.counts()["A"] == 0


# spec-bench: AC7 fp=3373f3a0b5
def test_ac7_results_must_appear_within_2_seconds():
    raise NotImplementedError("write the check for AC7")


# spec-bench: AC8 fp=6af4a1df30
def test_ac8_the_tool_must_email_every_team():
    p = poll(opened="12:00:00")
    opened_mail = len(p.outbox.sent)
    p.tick(hms("12:07:59"))
    assert len(p.outbox.sent) == opened_mail
    p.tick(hms("12:08:00"))
    p.tick(hms("12:09:00"))
    reminders = p.outbox.sent[opened_mail:]
    assert sorted(m["to"] for m in reminders) == sorted(TEAM5)


def test_ac9_every_team_member_must_get_an():
    p = poll()
    assert len(p.outbox.sent) == 5
    assert all(p.link in m["body"] for m in p.outbox.sent)


# spec-bench: AC10 fp=18f226eebf
def test_ac10_when_two_or_more_places_tie():
    p = poll()
    for voter, place in (("ana", "A"), ("ben", "A"), ("cy", "A"),
                         ("dee", "B"), ("eli", "B")):
        p.vote(voter, place, hms("12:01:00"))
    p.vote("zed", "B", hms("12:01:00"))  # a sixth voter makes it 3 to 3
    p.close(hms("12:05:00"))
    assert p.tie_choices() == ["A", "B"]


def test_clock_helper_reads_hh_mm_ss():
    assert hms("12:10:00") - hms("12:00:00") == 600
