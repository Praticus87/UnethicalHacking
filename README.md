# ReVive — Interactive EMG Rehabilitation Platform

ReVive turns surface EMG activity from the biceps into movement of an animated
virtual arm, giving patients with limited voluntary arm movement real-time
biofeedback while a physiotherapist monitors the signal.

> **Research / educational prototype — not a medical device.** EMG activation
> shown by ReVive is a biofeedback cue. It does not measure strength, prove
> neurological recovery, or predict whether movement will return. The virtual
> arm's angle is not the patient's real joint angle. Do not store real patient
> health information.

**Status: Phase 1 (interactive prototype).** Everything runs on simulated EMG;
no Arduino or BioAmp hardware is needed.

## Quick start

Requires Python 3.11+.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m revive.main
```

The app opens at <http://127.0.0.1:8080>:

- **Patient view:** <http://127.0.0.1:8080/>
- **Therapist dashboard:** <http://127.0.0.1:8080/therapist>

Both views share one live session, so you can open them side by side (or on
two screens) and watch them stay in sync.

Optional environment variables: `REVIVE_PORT` (default `8080`), `REVIVE_HOST`
(default `127.0.0.1`), `REVIVE_NO_BROWSER=1` (don't open a browser tab).

### Run the tests

```bash
python -m pytest
```

## Demo script

1. Open the patient view and press **Start**.
2. Drag **Simulated muscle effort** above the threshold, or press and hold
   **Press and hold to contract**. The biceps lights up, the forearm flexes,
   and the hold timer runs. Release, and the repetition counts once the hold
   lasted at least the minimum duration.
3. Reach the goal (5 by default) to see the completion banner.
4. Open the therapist dashboard and choose a **Scenario**:
   - *Rest*: background noise only, nothing is counted.
   - *Weak* / *Moderate*: automatic 2-second bursts every 5 seconds.
   - *Noisy*: short motion-artifact spikes that cross the threshold but are
     rejected as too short (see the "Rejected" counter).
5. Adjust the threshold, hysteresis, minimum duration and calibration
   reference, and watch the effect on the envelope chart.

## Project structure

```
revive/
  main.py                    # entry point: pages, background tick, ui.run
  engine.py                  # wires source -> processing -> detection -> session (shared by all tabs)
  core/
    signal_processing.py     # EMGProcessor (high-pass + rolling RMS), ContractionDetector
    calibration.py           # rest/reference normalisation and baseline estimation
    exercises.py             # ExerciseGoal, ExerciseSession (start/pause/reset, reps, timing)
  sources/
    base.py                  # SignalSource interface, SampleBatch
    simulator.py             # repeatable EMG simulator with scenarios and manual effort
    arduino_serial.py        # Phase 3 placeholder for Arduino + BioAmp over serial
  storage/
    database.py              # Phase 4 placeholder for SQLite session storage
  ui/
    layout.py                # theme CSS, header/navigation, helpers
    arm.py                   # animated SVG virtual arm
    simulation_panel.py      # simulator controls (effort slider, hold button, scenarios)
    patient.py               # patient screen
    therapist.py             # therapist dashboard
firmware/                    # future Arduino .ino sketch
tests/                       # pytest suite (logic + NiceGUI page smoke tests)
```

## How it works

1. **Signal source.** A `SignalSource` returns timestamped `SampleBatch`es.
   The simulator generates band-limited (20–150 Hz) noise modulated by an
   effort envelope at 500 Hz, plus a sensor noise floor and, in the noisy
   scenario, motion artifacts and mains hum. It uses a seeded RNG, so output is
   repeatable.
2. **Processing.** `EMGProcessor` applies a configurable high-pass filter
   (20 Hz default; to be re-validated against the BioAmp's actual filtering)
   and a 100 ms rolling RMS envelope. Both are streaming and stateful.
3. **Normalisation.** `Calibration` maps the resting level to 0 and a
   reference level to 1. This is a per-patient display scale, not a strength
   measure.
4. **Detection.** `ContractionDetector` uses an on threshold, a lower off
   threshold (hysteresis), a minimum *continuous* activation duration, and a
   minimum release time, so artifacts and brief dips do not create false
   repetitions.
5. **Session.** `ExerciseSession` counts contractions only while running and
   tracks hold durations and elapsed time.
6. **UI.** A background timer runs the engine every 20 ms. Each page refreshes
   from the shared engine; the virtual arm is animated by updating CSS
   variables that the browser interpolates smoothly.

## Roadmap

- **Phase 2:** guided calibration (rest + reference recording), therapist-
  configured exercises (e.g. minimum hold per rep), richer completion feedback.
- **Phase 3:** Arduino firmware and serial acquisition; verify sampling rate,
  signal quality and filtering; switch between simulation and hardware.
- **Phase 4:** SQLite storage with fictional demo patients, session history and
  progress charts.
- **Phase 5:** polish, performance, error handling, demo hardening.
