
from pathlib import Path

import numpy as np
import pandas as pd


# --------------------------------------------------
# 1. Configuration
# --------------------------------------------------

SEED = 42
SAMPLE_RATE_HZ = 10
DURATION_SECONDS = 300

MISSION_NAME = "Test Flight 001"
VEHICLE_NAME = "GTXR Test Vehicle 01"
LAUNCH_TIME = pd.Timestamp("2026-11-01T12:00:00Z")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
TRUTH_DIR = PROJECT_ROOT / "data" / "ground_truth"

SENSORS = [
    ("ALT-01", "altitude", "meters"),
    ("VEL-01", "velocity", "m/s"),
    ("TEMP-01", "temperature", "celsius"),
    ("PRESS-01", "pressure", "Pa"),
    ("BATT-01", "battery_voltage", "V"),
]


# --------------------------------------------------
# 2. Simulate flight physics
# --------------------------------------------------

def simulate_flight(times):
    """Return ideal altitude and vertical velocity arrays."""

    altitude = np.zeros_like(times)
    velocity = np.zeros_like(times)

    boost = times <= 25
    coast = (times > 25) & (times <= 90)
    descent = times > 90

    # Phase 1: Boost with constant upward acceleration.
    acceleration = 20.8

    altitude[boost] = 0.5 * acceleration * times[boost] ** 2
    velocity[boost] = acceleration * times[boost]

    # Phase 2: Coast and slow until apogee.
    coast_time = times[coast] - 25

    altitude[coast] = (
        6500 + 520 * coast_time - 4 * coast_time**2
    )
    velocity[coast] = 520 - 8 * coast_time

    # Phase 3: Smooth descent toward the ground.
    descent_fraction = (times[descent] - 90) / 210

    altitude[descent] = 23400 * (
        1
        - 3 * descent_fraction**2
        + 2 * descent_fraction**3
    )

    velocity[descent] = (
        23400
        * (-6 * descent_fraction + 6 * descent_fraction**2)
        / 210
    )

    return altitude, velocity


# --------------------------------------------------
# 3. Create mission and sensor metadata
# --------------------------------------------------

def save_metadata():
    vehicles = pd.DataFrame([{
        "vehicle_name": VEHICLE_NAME,
        "vehicle_type": "Experimental Rocket",
        "manufacturer": "Synthetic GTXR-inspired example",
    }])

    missions = pd.DataFrame([{
        "mission_name": MISSION_NAME,
        "vehicle_name": VEHICLE_NAME,
        "launch_time": LAUNCH_TIME.isoformat(),
        "landing_time": (
            LAUNCH_TIME + pd.Timedelta(seconds=DURATION_SECONDS)
        ).isoformat(),
        "status": "completed",
    }])

    sensors = pd.DataFrame([
        {
            "vehicle_name": VEHICLE_NAME,
            "sensor_name": name,
            "sensor_type": sensor_type,
            "measurement_unit": unit,
        }
        for name, sensor_type, unit in SENSORS
    ])

    vehicles.to_csv(RAW_DIR / "vehicles.csv", index=False)
    missions.to_csv(RAW_DIR / "missions.csv", index=False)
    sensors.to_csv(RAW_DIR / "sensors.csv", index=False)


# --------------------------------------------------
# 4. Generate noisy sensor measurements
# --------------------------------------------------

def generate_readings(rng):
    sample_count = SAMPLE_RATE_HZ * DURATION_SECONDS

    times = np.arange(sample_count) / SAMPLE_RATE_HZ

    timestamps = pd.date_range(
        start=LAUNCH_TIME,
        periods=sample_count,
        freq="100ms",
    ).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    altitude, velocity = simulate_flight(times)

    # Simplified physical and equipment relationships.
    pressure = 101325 * np.exp(-altitude / 8400)

    temperature = (
        22
        - 0.004 * np.minimum(altitude, 12000)
        + 12 * np.exp(-times / 20)
    )

    battery = 12.6 - 0.0012 * times

    # Add small, reproducible measurement noise.
    measurements = {
        "ALT-01": np.maximum(
            0, altitude + rng.normal(0, 2.0, sample_count)
        ),
        "VEL-01": velocity + rng.normal(
            0, 1.0, sample_count
        ),
        "TEMP-01": temperature + rng.normal(
            0, 0.5, sample_count
        ),
        "PRESS-01": pressure + rng.normal(
            0, 50.0, sample_count
        ),
        "BATT-01": battery + rng.normal(
            0, 0.025, sample_count
        ),
    }

    frames = []

    for sensor_name, values in measurements.items():
        frames.append(pd.DataFrame({
            "mission_name": MISSION_NAME,
            "sensor_name": sensor_name,
            "recorded_at": timestamps,
            "measurement_value": np.round(values, 4),
            "issue_type": "clean",
        }))

    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------
# 5. Inject intentional data quality problems
# --------------------------------------------------

def inject_issues(readings, rng):
    readings = readings.copy()

    def select_clean_rows(count):
        candidates = readings.index[
            readings["issue_type"] == "clean"
        ].to_numpy()

        return rng.choice(
            candidates,
            size=count,
            replace=False,
        )

    # A. Drop 35 readings entirely.
    missing_indices = select_clean_rows(35)

    missing_readings = readings.loc[
        missing_indices,
        ["mission_name", "sensor_name", "recorded_at"]
    ].copy()

    readings = readings.drop(missing_indices).reset_index(drop=True)

    # B. Create 40 unusually large sensor values.
    spike_indices = select_clean_rows(40)

    spike_offsets = {
        "ALT-01": 2500,
        "VEL-01": 200,
        "TEMP-01": 170,
        "PRESS-01": 50000,
        "BATT-01": 20,
    }

    readings.loc[spike_indices, "measurement_value"] += (
        readings.loc[spike_indices, "sensor_name"]
        .map(spike_offsets)
        .to_numpy()
    )

    readings.loc[spike_indices, "issue_type"] = "spike"

    # C. Create 25 missing measurement values.
    null_indices = select_clean_rows(25)

    readings.loc[null_indices, "measurement_value"] = np.nan
    readings.loc[null_indices, "issue_type"] = "null_value"

    # D. Create 10 invalid timestamps.
    timestamp_indices = select_clean_rows(10)

    readings.loc[timestamp_indices, "recorded_at"] = (
        "not-a-timestamp"
    )
    readings.loc[timestamp_indices, "issue_type"] = (
        "invalid_timestamp"
    )

    # E. Duplicate 30 otherwise clean readings.
    duplicate_indices = select_clean_rows(30)

    duplicates = readings.loc[duplicate_indices].copy()
    duplicates["issue_type"] = "duplicate"

    readings = pd.concat(
        [readings, duplicates],
        ignore_index=True,
    )

    # Shuffle rows to avoid relying on input order.
    readings = readings.sample(
        frac=1,
        random_state=SEED,
    ).reset_index(drop=True)

    # Label the duplicate that appears later in the raw file.
    duplicate_key = [
        "mission_name",
        "sensor_name",
        "recorded_at",
        "measurement_value",
    ]

    readings.loc[
        readings["issue_type"] == "duplicate",
        "issue_type",
    ] = "clean"

    duplicate_mask = readings.duplicated(
        subset=duplicate_key,
        keep="first",
    )

    readings.loc[duplicate_mask, "issue_type"] = "duplicate"

    # Give every raw CSV row its own traceable identifier.
    readings.insert(
        0,
        "source_row_id",
        np.arange(1, len(readings) + 1),
    )

    return readings, missing_readings


# --------------------------------------------------
# 6. Save raw data and separate ground truth
# --------------------------------------------------

def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    TRUTH_DIR.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(SEED)

    save_metadata()

    readings = generate_readings(rng)
    readings, missing_readings = inject_issues(readings, rng)

    raw_columns = [
        "source_row_id",
        "mission_name",
        "sensor_name",
        "recorded_at",
        "measurement_value",
    ]

    readings[raw_columns].to_csv(
        RAW_DIR / "telemetry_readings.csv",
        index=False,
    )

    issue_labels = readings.loc[
        readings["issue_type"] != "clean",
        ["source_row_id", "issue_type"],
    ]

    issue_labels.to_csv(
        TRUTH_DIR / "injected_issues.csv",
        index=False,
    )

    missing_readings.to_csv(
        TRUTH_DIR / "missing_readings.csv",
        index=False,
    )

    print("Telemetry generation complete.")
    print(f"Expected readings: {SAMPLE_RATE_HZ * DURATION_SECONDS * len(SENSORS):,}")
    print(f"Raw rows written: {len(readings):,}")
    print(f"Injected issue labels: {len(issue_labels):,}")
    print(f"Intentionally omitted readings: {len(missing_readings):,}")
    print(f"Random seed: {SEED}")


if __name__ == "__main__":
    main()
