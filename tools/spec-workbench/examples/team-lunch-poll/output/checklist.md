# Test checklist: Lunch poll idea

From revision 5.

Ticks come from evidence run 1 (JUnit results junit.xml, recorded against revision 5): 5 of 10 criteria verified. A tick means a test pinned to the current wording passed; read the test to confirm it checks the criterion.

## Acceptance criteria

### R1 (must): Any team member can start a poll with 2 to 8 restaurant options.
- [x] AC1: Given a signed-in team member on the new poll page, when they enter 1 option, then 9 options, then 3 options and press Start, then 1 and 9 options are rejected with the message "Add 2 to 8 places" and 3 options create an open poll (verified by test_acceptance::test_ac1_any_team_member_can_start_a in evidence run 1)

### R2 (must): A voter must be able to cast a vote in at most 2 taps from the poll link, in a phone or laptop browser.
- [ ] AC2: Given an open poll and its link on a phone browser, when a voter opens the link and taps one place, then the vote is saved after the second tap and the page shows "Vote saved" (unwritten in evidence run 1)

### R3 (must): A voter must not see how any other person voted.
- [x] AC3: Given an open poll with votes from 3 people, when a voter who is not the organizer views the poll, then the page shows vote counts per place and no voter names (verified by test_acceptance::test_ac3_a_voter_must_not_see_how in evidence run 1)

### R4 (must): The organizer must see who voted for what so they can place the order.
- [x] AC4: Given a closed poll with votes from 3 people, when the organizer opens the results, then each place lists the names of the people who voted for it (verified by test_acceptance::test_ac4_the_organizer_must_see_who_voted in evidence run 1)

### R5 (must): The poll must close automatically 15 minutes after it opens, unless the organizer closes it sooner.
- [ ] AC5: Given a poll opened at 12:00:00, when no one closes it, then its status is closed at 12:15:00 and new votes are rejected (stale in evidence run 1)

### R7 (must): A voter can change their vote until the poll closes.
- [x] AC6: Given a voter who voted for place A in an open poll, when they vote for place B, then the poll counts 1 vote for B and 0 votes for A from that voter (verified by test_acceptance::test_ac6_a_voter_can_change_their_vote in evidence run 1)

### R9 (must): Results must appear within 2 seconds of the poll closing.
- [ ] AC7: Given a poll with 15 votes, when the poll closes, then the winning place and its vote count are shown to every voter within 2 seconds of the close time (unwritten in evidence run 1)

### R12 (must): The tool must email every team member a reminder 2 minutes before the poll closes.
- [x] AC8: Given a poll that closes at 12:10:00 for a team of 5, when the clock reaches 12:08:00, then 5 reminder emails are sent, one to each team member (verified by test_acceptance::test_ac8_the_tool_must_email_every_team in evidence run 1)

### R13 (must): Every team member must get an email with the poll link when a poll opens.
- [ ] AC9: Given a team of 5, when a member starts a poll, then 5 emails containing the poll link are sent (unpinned in evidence run 1)

### R14 (must): When two or more places tie, the organizer must pick the winner from the tied places.
- [ ] AC10: Given a closed poll where places A and B each have 3 votes, when the organizer opens the results, then the organizer is asked to pick A or B, and the other places are not offered (failing in evidence run 1)

## Requirements with no criterion (not testable yet)

- [ ] R11 (could): It would be nice to remember everyone's favorite places.

## Assumptions to validate

- [ ] A1: I assume everyone already has a work email address. (Ask the pilot team's admin before the build starts.)
- [ ] A2: Probably most people will vote from a laptop anyway. (Count phone versus laptop votes in the first week of pilot polls.)
