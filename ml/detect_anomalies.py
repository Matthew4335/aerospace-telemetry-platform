
import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.ensemble import IsolationForest
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

MODEL_VERSION = "isolation_forest_v1"
MIN_SAMPLES = 30


def score_sensor(
    readings: pd.DataFrame,
    contamination: float = 0.01,
) -> pd.DataFrame:
    """
    Fit Isolation Forest to one mission/sensor group.

    Returns reading IDs, decision scores, and anomaly flags.
    Negative decision scores indicate predicted anomalies.
    """
    if not (0 < contamination <= 0.5):
        raise ValueError(
            "contamination must be greater than 0 and at most 0.5"
        )

    ordered = readings.copy()

    ordered["recorded_at"] = pd.to_datetime(
        ordered["recorded_at"],
        utc=True,
    )

    ordered = ordered.sort_values(
        ["recorded_at", "reading_id"]
    ).reset_index(drop=True)

    # Avoid training on extremely small groups.
    if len(ordered) < MIN_SAMPLES:
        return pd.DataFrame(
            columns=[
                "reading_id",
                "anomaly_score",
                "is_anomaly",
            ]
        )

    values = pd.to_numeric(
        ordered["measurement_value"],
        errors="raise",
    ).astype(float)

    if not np.isfinite(values.to_numpy()).all():
        raise ValueError(
            "Sensor data contains a non-finite measurement"
        )

    # Nearby measurements provide a local baseline.
    rolling_median = values.rolling(
        window=11,
        center=True,
        min_periods=1,
    ).median()

    # Three features for detecting unusual behavior.
    features = pd.DataFrame(
        {
            "value": values,
            "local_deviation": (
                values - rolling_median
            ).abs(),
            "step_change": (
                values.diff().abs().fillna(0.0)
            ),
        }
    )

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
    )

    model.fit(features)

    scores = model.decision_function(features)

    return pd.DataFrame(
        {
            "reading_id": ordered["reading_id"]
                .astype(int)
                .to_numpy(),
            "anomaly_score": scores,
            "is_anomaly": scores < 0,
        }
    )


def run_detection(
    database_url: str,
    mission_id: int | None = None,
    contamination: float = 0.01,
) -> None:
    if not (0 < contamination <= 0.5):
        raise ValueError(
            "contamination must be greater than 0 and at most 0.5"
        )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )

    query = """
        SELECT
            r.reading_id,
            r.mission_id,
            r.sensor_id,
            s.sensor_name,
            r.recorded_at,
            r.measurement_value
        FROM telemetry_readings AS r
        JOIN sensors AS s
            ON r.sensor_id = s.sensor_id
    """

    params = {}

    if mission_id is not None:
        query += " WHERE r.mission_id = :mission_id"
        params["mission_id"] = mission_id

    query += """
        ORDER BY
            r.mission_id,
            r.sensor_id,
            r.recorded_at,
            r.reading_id
    """

    # Remove previous results for each processed sensor.
    delete_sql = text("""
        DELETE FROM telemetry_anomalies AS a
        USING telemetry_readings AS r
        WHERE a.reading_id = r.reading_id
          AND r.mission_id = :mission_id
          AND r.sensor_id = :sensor_id
    """)

    # Store only readings classified as anomalous.
    insert_sql = text("""
        INSERT INTO telemetry_anomalies (
            reading_id,
            anomaly_score,
            model_version
        )
        VALUES (
            :reading_id,
            :anomaly_score,
            :model_version
        )
    """)

    total_flagged = 0

    try:
        # One transaction: if an error occurs,
        # all anomaly updates are rolled back.
        with engine.begin() as conn:
            readings = pd.read_sql(
                text(query),
                conn,
                params=params,
            )

            if readings.empty:
                print("No telemetry readings found.")
                return

            groups = readings.groupby(
                ["mission_id", "sensor_id"],
                sort=True,
            )

            print(
                f"Loaded {len(readings):,} telemetry readings."
            )

            for (mid, sid), group in groups:
                sensor_name = group["sensor_name"].iloc[0]

                results = score_sensor(
                    group,
                    contamination=contamination,
                )

                flagged = results[
                    results["is_anomaly"]
                ]

                # Clear this group's previous predictions.
                conn.execute(
                    delete_sql,
                    {
                        "mission_id": int(mid),
                        "sensor_id": int(sid),
                    },
                )

                records = [
                    {
                        "reading_id": int(row.reading_id),
                        "anomaly_score": float(
                            row.anomaly_score
                        ),
                        "model_version": MODEL_VERSION,
                    }
                    for row in flagged.itertuples()
                ]

                if records:
                    conn.execute(insert_sql, records)

                total_flagged += len(records)

                if len(group) < MIN_SAMPLES:
                    print(
                        f"Mission {mid} | {sensor_name}: "
                        "skipped (fewer than 30 readings)"
                    )
                else:
                    print(
                        f"Mission {mid} | {sensor_name}: "
                        f"{len(records)} flagged "
                        f"out of {len(group):,}"
                    )

        print()
        print(
            f"Complete: {total_flagged} anomaly "
            "records stored."
        )

    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Detect anomalies in stored telemetry"
    )

    parser.add_argument(
        "--mission-id",
        type=int,
        default=None,
        help="Only analyze the specified mission",
    )

    parser.add_argument(
        "--contamination",
        type=float,
        default=0.01,
        help="Estimated outlier fraction (default: 0.01)",
    )

    args = parser.parse_args()

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is not configured"
        )

    run_detection(
        database_url=database_url,
        mission_id=args.mission_id,
        contamination=args.contamination,
    )


if __name__ == "__main__":
    main()
