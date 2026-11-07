# 3. How I would run this in production

The design target is to run the model of Section 2 for 25 buildings (about 600 AHUs) in the first year, and to send the technicians work orders they can trust. I chose **Azure with Databricks**: the buildings already run Windows and SQL Server, and it is the stack I used in production for a similar ML system (Delta tables, scheduled jobs, MLflow with a champion model). The lighter option, containers with Parquet files and a managed MLflow, would also work and cost less; I would pick it if the operator has no Azure. More detail (technology choices, alert rules, monitoring thresholds, onboarding plan) in `code/docs/05 - Architecture.md`.

![From the BMS to a work order, and back as labels.](../figures/architecture.png){width=95%}

## Data ingestion and storage

- **At the edge:** a small Python agent runs as a Windows service on each edge PC. Every 15 minutes it reads the new rows from SQL Server (by last timestamp) and sends them over **outbound HTTPS** to an ingestion endpoint, with a token per site. If the connection fails, it keeps up to 7 days on disk and sends them later. Nothing listens on site, so no inbound connection is needed. The model does **not** run at the edge: one place to update it, and the edge PC is the least reliable part.
- **Storage:** three layers in Delta tables, partitioned by building and day. **Bronze** keeps the rows exactly as received, so I can always rebuild. **Silver** is the cleaned data (`clean_sensors()`). **Gold** has the features and the predictions.
- **Data quality:** the problems I found in Section 1 become automatic checks in the step to silver: clock shift (outside temperature compared with a neighbour building), duplicate rows, outages, wrong units, sensor limits and frozen sensors. A failed check fixes what it can and logs the rest. A frozen sensor raises a **"sensor issue"** ticket, kept apart from fault alarms, because it needs a different fix. Each building's batch gets a result: **pass, warn or block**. If it blocks (for example the clock is shifted or half the rows are missing), the alerts of that building pause until the data is fixed, so bad data never becomes a false alarm.

## ML lifecycle

- **Training** runs once a month, or earlier when new confirmed work orders arrive. It reuses the code of Section 2: time-block validation and the event-level scorer.
- **Versioning:** every run is logged in MLflow (data period, code commit, parameters, scores) and registers a new model version with its model card, like the `artifacts/` folder of this repository.
- **Champion and challenger:** a new version (challenger) replaces the current one (champion) only if it passes **two gates**: a minimum level (for example, at least 90% of faults found and at most 0.1 false alarms per AHU per month) **and** a better score than the champion on the same validation data. Then it runs **two weeks in shadow mode**, predicting without sending alerts, and its alarms are compared with what the technicians find. Rolling back means moving the `champion` alias back to the old version.
- **Environments:** code goes through the same branch flow as this repository (`develop`, `qa`, `main`), deployed with Databricks Asset Bundles to a dev, a QA and a production workspace. Each environment trains its own model on its own data; models are never copied between environments.
- **Labels from the field:** every day the system reads the closed work orders from the CMMS API. "Fault confirmed" becomes a label for that fault and period; "no fault found" becomes a normal label and a measured false alarm. This is the most valuable data: today there are only 29 events.

## Inference strategy

**Every hour, per building.** Faults last days, an alarm needs at least 2 hours of evidence, and a supply air sensor bias can only be checked at night with the fan off. Every 5 minutes would cost more and gain minutes that don't matter for a visit the next day. Each run uses the last 48 hours of data, so the rolling features are complete.

## Alerting and integration

The alert service turns predictions into work orders, and its job is to protect the technicians' trust:

- **One alarm per fault:** the pieces of the same fault are joined (the morning start-up doesn't split it) and an open alarm is updated, not repeated. It **closes** by itself after 24 hours of running back to normal, with a note on the work order, so old alarms don't stay open.
- **Severity by type and building:** a stuck valve or low coil capacity wastes energy and comfort now (high); a sensor bias or a stuck damper can usually wait a few days (medium), except a stuck damper in the hospital, where fresh air matters for patients (high).
- **Suppression:** after "no fault found", the same fault on the same AHU is silenced for 14 days, unless the signal gets clearly worse.
- **Work order:** created through the CMMS REST API, with the evidence: a small chart of the signals that triggered it and the plain fault name, so the technician knows what to check first.
- **Feedback:** the outcome of each order flows back as a label (see above).

## Monitoring

- **Data:** freshness per building (an agent that stopped sending), share of missing rows, failed quality checks, frozen sensors.
- **Model:** alarms per AHU per month against the expected rate (0.05 in validation), share of alarms confirmed by technicians, and drift of the main features (for example, filters slowly change the fan signals).
- **Jobs:** failed or late runs.

All of it is in one dashboard (Databricks SQL) that reads from MLflow and the alert tables: champion and challenger versions with their scores, alarms by type and building, confirmed share, drift and data checks.

**First month after go-live:** the model runs in shadow for the first two weeks, then sends alerts with a weekly review with the facilities manager. If a site raises too many alarms, I raise its confidence threshold or minimum alarm length for that site before going further.

## Scale and onboarding

- **Scale:** 2,000 AHUs are about 600,000 rows a day, under 100 MB. Jobs run per building in parallel: growing means more small jobs, not a bigger system.
- **A new building in under a week:**
  - Day 1: install the agent and its token.
  - Day 2: map the BMS point names to the standard names (one template per BMS vendor) and fill the AHU metadata (size, sensors).
  - Day 3: load the history already stored in SQL Server, and run the quality checks.
  - Days 4-5: if there are at least two weeks of history, learn each AHU's normal and start the **physics rules** in shadow mode. Otherwise the rules wait until two weeks of data arrive.
- **Why rules first:** in Section 2, a model trained on other buildings found only 50-60% of the faults in a building it had never seen, while the rules found all of them. The model takes over once the building has its own confirmed work orders.
