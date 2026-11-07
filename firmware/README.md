# Firmware (Phase 3)

The Arduino UNO R3 sketch for sampling the BioAmp EXG Pill will live here as a
separate `.ino` file. Before writing it, verify against the manufacturer
documentation:

- the BioAmp EXG Pill's on-board filter configuration and output range,
- a sampling rate the UNO can sustain reliably (with timer-based sampling),
- a serial format and baud rate that keep up with that rate.

**Safety:** do not connect body electrodes to an unverified power/USB setup.
Human-connected testing requires a manufacturer-approved, electrically safe
power and isolation arrangement (for example a battery-powered laptop that is
not connected to mains power).
