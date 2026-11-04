from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]

csv_path = (
    PROJECT_ROOT / "data" / "raw" / "telemetry_readings.csv"
)

df = pd.read_csv(csv_path)

print("\nFIRST FIVE ROWS")
print(df.head())

print("\nDATASET SHAPE")
print(df.shape)

print("\nCOLUMN TYPES")
print(df.dtypes)

print("\nREADINGS PER SENSOR")
print(df["sensor_name"].value_counts())

print("\nMISSING VALUES")
print(df.isna().sum())

print("\nSUMMARY STATISTICS")
print(df.groupby("sensor_name")["measurement_value"].describe())

print("\nINVALID TIMESTAMPS")
parsed_timestamps = pd.to_datetime(
    df["recorded_at"],
    errors="coerce",
    utc=True,
    format="ISO8601",
)
print(parsed_timestamps.isna().sum())

print("\nDUPLICATE TELEMETRY RECORDS")
duplicate_columns = [
    "mission_name",
    "sensor_name",
    "recorded_at",
    "measurement_value",
]

print(
    df.duplicated(
        subset=duplicate_columns,
        keep="first",
    ).sum()
)