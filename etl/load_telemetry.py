
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine

from extract import read_source_files
from transform import transform_readings
from load import (
    load_metadata,
    get_lookup_tables,
    insert_telemetry,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

REJECTED_DIR = PROJECT_ROOT / "data" / "rejected"


def save_rejected_records(rejected_rows):
    """Save rejected telemetry to a CSV file."""

    REJECTED_DIR.mkdir(parents=True, exist_ok=True)

    output_file = REJECTED_DIR / "rejected_readings.csv"

    columns = [
        "source_row_id",
        "mission_name",
        "sensor_name",
        "recorded_at",
        "measurement_value",
        "rejection_reason",
    ]

    rejected_df = pd.DataFrame(
        rejected_rows,
        columns=columns,
    )

    rejected_df.to_csv(output_file, index=False)

    return output_file


def main():
    """Run the complete telemetry ETL pipeline."""

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is missing from your .env file"
        )

    print("Starting telemetry ETL pipeline...")

    # STEP 1: EXTRACT
    vehicles, missions, sensors, readings = (
        read_source_files()
    )

    print(f"Source readings: {len(readings):,}")

    # STEP 2: CONNECT
    engine = create_engine(DATABASE_URL)

    try:
        # Use one database transaction.
        with engine.begin() as conn:

            # STEP 3: LOAD METADATA
            load_metadata(
                conn,
                vehicles,
                missions,
                sensors,
            )

            # STEP 4: GET DATABASE IDS
            mission_lookup, sensor_lookup = (
                get_lookup_tables(conn)
            )

            # STEP 5: TRANSFORM
            valid_rows, rejected_rows = transform_readings(
                readings,
                mission_lookup,
                sensor_lookup,
            )

            # STEP 6: LOAD TELEMETRY
            inserted_count = insert_telemetry(
                conn,
                valid_rows,
            )

        # STEP 7: SAVE REJECTED RECORDS
        rejected_file = save_rejected_records(
            rejected_rows
        )

        # STEP 8: REPORT RESULTS
        print("\nETL complete!")
        print(f"Source rows: {len(readings):,}")
        print(f"Valid rows: {len(valid_rows):,}")
        print(f"Rejected rows: {len(rejected_rows):,}")
        print(f"New rows inserted: {inserted_count:,}")
        print(f"Rejection report: {rejected_file}")

        if rejected_rows:
            reasons = pd.Series([
                row["rejection_reason"]
                for row in rejected_rows
            ])

            print("\nRejection summary:")
            print(reasons.value_counts().to_string())

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
