
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
    reject_conflicting_readings,
)
from quality import (
    validate_metadata,
    build_quality_reports,
    save_quality_reports,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")

REJECTED_DIR = PROJECT_ROOT / "data" / "rejected"
QUALITY_DIR = PROJECT_ROOT / "data" / "quality"


def save_rejected_records(rejected_rows):
    """Preserve invalid source records and rejection reasons."""

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

    pd.DataFrame(
        rejected_rows,
        columns=columns,
    ).to_csv(output_file, index=False)

    return output_file


def main():
    """Run the ETL pipeline and produce data-quality reports."""

    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is missing from .env"
        )

    print("Starting aerospace telemetry ETL...")

    # STEP 1: EXTRACT
    vehicles, missions, sensors, readings = (
        read_source_files()
    )

    print(f"Source readings: {len(readings):,}")

    # STEP 2: VALIDATE SOURCE METADATA
    validate_metadata(vehicles, missions, sensors)

    print("Source metadata validation passed.")

    engine = create_engine(DATABASE_URL)

    try:
        # STEP 3: DATABASE TRANSACTION
        with engine.begin() as conn:

            load_metadata(
                conn,
                vehicles,
                missions,
                sensors,
            )

            mission_lookup, sensor_lookup = (
                get_lookup_tables(conn)
            )

            # Ensure existing missions belong to the
            # vehicles specified in our source metadata.
            for source in missions.to_dict("records"):
                stored = mission_lookup.get(
                    source["mission_name"]
                )

                if (
                    stored is None
                    or stored["vehicle_name"]
                    != source["vehicle_name"]
                ):
                    raise ValueError(
                        "Mission/vehicle mismatch: "
                        + source["mission_name"]
                    )

            # STEP 4: TRANSFORM EXISTING TELEMETRY
            valid_rows, rejected_rows = transform_readings(
                readings,
                mission_lookup,
                sensor_lookup,
            )

            # STEP 5: ANALYZE QUALITY
            quality_summary, quality_issues = (
                build_quality_reports(
                    valid_rows,
                    missions,
                    mission_lookup,
                    sensor_lookup,
                )
            )
            # STEP 6: CHECK FOR CONFLICTING DATABASE RECORDS
            reject_conflicting_readings(
                conn,
                valid_rows,
            )

            # STEP 7: LOAD VALID TELEMETRY
            inserted_count = insert_telemetry(
                conn,
                valid_rows,
            )

        # Transaction has now committed successfully.

        # STEP 8: WRITE REJECTION REPORT
        rejected_file = save_rejected_records(
            rejected_rows
        )

        # STEP 9: WRITE DATA-QUALITY REPORTS
        audit = save_quality_reports(
            QUALITY_DIR,
            quality_summary,
            quality_issues,
            source_count=len(readings),
            valid_count=len(valid_rows),
            rejected_rows=rejected_rows,
            inserted_count=inserted_count,
        )

        # STEP 10: PRINT SUMMARY
        print("\nETL completed successfully!")
        print(f"Source rows: {len(readings):,}")
        print(f"Valid rows: {len(valid_rows):,}")
        print(f"Rejected rows: {len(rejected_rows):,}")
        print(f"New database rows: {inserted_count:,}")
        print(
            f"Quality warnings: "
            f"{audit['quality_warnings']:,}"
        )

        print("\nReports:")
        print(f"Rejected: {rejected_file}")
        print(
            f"Quality summary: "
            f"{QUALITY_DIR / 'quality_summary.csv'}"
        )
        print(
            f"Quality issues: "
            f"{QUALITY_DIR / 'quality_issues.csv'}"
        )
        print(
            f"Ingestion summary: "
            f"{QUALITY_DIR / 'ingestion_summary.json'}"
        )

        if rejected_rows:
            reasons = pd.Series([
                row["rejection_reason"]
                for row in rejected_rows
            ])

            print("\nRejection reasons:")
            print(reasons.value_counts().to_string())

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
