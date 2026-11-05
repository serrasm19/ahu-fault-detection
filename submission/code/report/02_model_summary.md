# 2. Model

Full work in `code/notebooks/05_modelling.ipynb`; `python -m ahu_fdd.predict` rebuilds `predictions.csv` from the raw data and saves the model with its model card.

**Framing.** A combination: a **LightGBM classifier decides if** a machine has a fault, and the **physics rules of Section 1.4 decide which** one inside each alarm. The model gives the fewest false alarms; the rules get the type right more often. Every feature is a residual against **the same machine's normal**, built from the physics of Section 1.4: supply air error, the valve against the valve this machine needs for the same cooling work (fan speed times °C cooled), the outdoor air share from the mixing formula, CO2, and the check with the fan off (9 features, Appendix B). LightGBM because the problem is tabular and threshold-like, it handles missing sensors natively, and I keep it small (only 29 events to learn from). Class weights instead of resampling; no synthetic fault rows.

**Validation.** **Across time:** three blocks of about two months, cut on days with no event in progress; each block is predicted by a model trained on the other two, and each machine's normal comes only from the training blocks. **Across units:** a whole building hidden from training (see below). I score like the brief, by event: found, right type, delay, false alarms per AHU per month (row accuracy is useless: always "normal" is right on 97.6% of rows). Rows become alarms: model at least 80% sure, alarms shorter than 2 hours dropped, pieces of one fault joined, one type per alarm.

| Option (29 events, 240 machine-months) | Found | Right type | Median delay | False alarms per AHU-month |
|--------------------------|--------|--------|--------|-------------|
| Physics rules | 100% | 93% | 11 h | 0.18 |
| Logistic regression | 76% | 59% | 4 h | 1.48 |
| Random forest | 93% | 79% | 11 h | 0.03 |
| LightGBM | 100% | 86% | 10 h | 0.05 |
| **LightGBM + rule types (final)** | **100%** | **93%** | **10 h** | **0.05** |

0.05 false alarms per AHU per month is about one per machine every 20 months. The tests behind the settings (relative features only, 80% confidence, joining alarms) are in Appendix B.

**Where it fails.** Two low coil capacity events on machines that are always at their limit are called a stuck valve: their valve is already at 100%, so a weak coil can't push it further. A valve position sensor or a chilled water flow meter would separate them. The remaining false alarms are short (2 to 5 hours) and all in the mall. The sensor bias is found the first night at the earliest, and can't be seen at all on 24/7 machines.

**A new AHU, and a building with fewer sensors.** I hid a whole building from training and gave it only two weeks of unlabelled data to learn each machine's normal. The model found 100% of the faults in the office but only 50-60% in the hospital and the mall (the mall has no CO2, and most sensor bias examples are there). The rules found all of them. So a new building starts with **two weeks to learn its normal, then the rules only**, and moves to the model once it has its own confirmed work orders. With fewer sensors, the missing features are simply empty and the rules don't use them. Ideas to shorten this cold start, such as injecting simulated faults into a new building's healthy data, are in Appendix E.

**Test period.** 14 alarms in 40 machines over July and August. They include the eight candidate faults I could see by hand in Section 1 (same type and dates), and no alarm on the machine with the frozen supply air sensor.
