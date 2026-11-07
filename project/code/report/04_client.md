# 4. Client communication

The reasons behind both texts are in Appendix A.

## 4.1 Reply to the facilities manager

**Subject:** Pilot alerts: review and next steps

Hi,

Thank you for the clear feedback, and for having the alerts checked. I understand the concern: if your team stops trusting the alerts, the system is worth nothing, so fixing this is my first priority.

Why this can happen: the system learns what is normal for each machine, and your building is new to it. In the first weeks it can take unusual but healthy behaviour for a fault, for example a unit that is a bit small for its area and always works at full power. Some faults are also hard to see on a visit: a temperature sensor that reads 2 degrees too high looks fine unless you check it with a second thermometer. So, during the next weeks, I will send a short note with each alert saying what to check on site, for example measuring the air temperature with a hand thermometer.

What we change this week:

- I will go through the 9 alerts one by one with the data, and send you a short answer for each by Wednesday: real problem, healthy machine, or our error.
- From now on, your technicians only get the alerts the system is very sure about. We check the others first.
- For the doubtful cases, I would like to visit the machine together with one of your technicians.

What you could tell the owner: the pilot is being tuned to this building before it grows. We suggest connecting the two new buildings next month as planned, but without alerts: the system learns them quietly. Alerts start there only when your building shows that most alerts are real. Our target is at least 7 out of 10 checked alerts confirmed, two weeks in a row. The owner keeps the timeline, and your team doesn't get the same problem in three buildings.

Two small things would help me a lot: the notes from the 4 visits, and for each new alert, a quick "fault found" or "nothing found" in the work order system.

Could we have a 30-minute call on Monday?

Best regards,\
Sergio

## 4.2 Internal note to the project lead

**Pilot building: the alerts are losing the technicians' trust**

**What I think is happening.** 9 alerts in a week is about ten times what validation suggests for a building of this size, so I suspect our setup more than the idea of the model. In order of likelihood:

1. **We turned alerts on too early.** In my tests, a model trained on other buildings found only about half of the faults in a new one; our own plan says rules first and two weeks in shadow mode.
2. **Healthy machines that look faulty.** In the training data, 3 of 40 units always run at full valve and look like a weak coil. If this building has some, they alarm every week.
3. **A data problem** (clock shift, wrong units, frozen sensor) that the quality gate didn't stop.
4. **Real faults that are hard to confirm on site,** such as a biased sensor, with alerts that don't say what to check.

Also, 5 of the 9 alerts were never checked, so we don't know the real hit rate yet.

**Next two weeks.**

- Days 1-2: review the 9 alerts with the raw data and label each one: real fault, healthy but unusual, data problem or unclear.
- Week 1: shadow mode again for the unclear fault types, a higher threshold for this site, units at their limit marked as normal, a manual "what to check" note with each alert, and one or two joint visits.
- Week 2: only high-confidence alerts, a weekly 30-minute review with the facilities manager, and tracking of the confirmed share.

**Scope question for you.** The manual "what to check" notes are part of this review. Making it a product feature (each alert explains its cause and recommends an action) may be outside the current scope. If it is, I would propose it as a change request: it is the change that would help the technicians most.

**What I need from the client.** The notes of the 4 checked alerts and the outcome of every new one; one technician for one or two joint visits; the BMS history and any setting or maintenance change during the pilot; sensor calibration dates; and which units they already know are undersized.

**Recommendation on the rollout.** Don't turn alerts on in the two new buildings next month. Do connect them next month in shadow mode: the system learns each machine's normal without sending anything. Turn their alerts on only when the pilot reaches a clear target: at least 7 out of 10 checked alerts confirmed, two weeks in a row. If the pilot doesn't get there within four weeks, we stop and review the approach with the client. The owner keeps the start date, and we don't repeat the problem in three buildings.
