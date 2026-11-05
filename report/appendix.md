# Appendix

Details that don't fit in the 12 pages.

## A. Why I answered the client this way (Question 4)

**The reply to the facilities manager.** They are not technical, they are frustrated, and they have to tell the owner something. So I followed five rules:

1. **Agree first, defend later.** Their point is correct: alerts that technicians ignore are worthless. Starting with "you are right" keeps the conversation open.
2. **No blame on the technicians.** "Nothing found" is often our fault: the alerts didn't say what to check, and some faults can't be seen without the right test (Q1: the lying thermometer is invisible while the machine runs).
3. **Plain words and one example per idea.** No model, threshold or feature. "A unit that is a bit small for its area" is the healthy machine at its limit of Q1; "a sensor that reads 2 degrees too high" is the lying thermometer.
4. **Concrete actions with a date,** small enough to do this week: review of the 9 alerts by Wednesday, only high-confidence alerts, "what to check" in each alert, a joint visit.
5. **Give them a message for the owner** that keeps the owner's timeline but protects the technicians: connect the new buildings next month without alerts, and turn alerts on when a clear target is met. A yes/no answer would put the facilities manager in a bad position.

**The internal note.** Here I can be direct and use numbers. Every hypothesis comes from what I saw in the data:

| Hypothesis in the note | Where it comes from |
|---|---|
| Alerts turned on too early in a new building | Q2: a model trained on other buildings found about half of the faults of a building it never saw; the rules found all of them |
| Healthy machines that look faulty | Q1: 3 of 40 units always run at full valve and look like a weak coil, labelled normal by the client |
| A data problem | Q1: each building had its own problem (clock shift, repeated day, outage, wrong units, frozen sensors) |
| Real faults hard to confirm on site | Q1: the lying thermometer only shows with the fan off |
| 9 alerts is about ten times the expected rate | Q2: 0.05 false alarms per AHU per month in validation, so less than one a month for 12-16 units |

**The rollout recommendation.** I didn't say "go" or "stop". Connecting the new buildings in shadow mode costs nothing in trust and gains time, because each machine needs about two weeks of data to learn its normal anyway (Q3, onboarding). The target (7 of 10 checked alerts confirmed, two weeks in a row) is simple enough for the owner to follow, and the four-week limit makes sure we don't hide the problem if it doesn't improve.
