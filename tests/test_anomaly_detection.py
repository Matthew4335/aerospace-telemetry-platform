
import numpy as np
import pandas as pd
import pytest

from ml.detect_anomalies import score_sensor


def make_sample_readings():
    """Create smooth readings with one large spike."""
    rng = np.random.default_rng(42)
    n = 301

    values = (
        5
        + 0.15 * np.sin(np.arange(n) / 10)
        + rng.normal(0, 0.03, n)
    )

    # Artificially introduce an anomaly.
    values[150] = 50.0

    return pd.DataFrame(
        {
            "reading_id": np.arange(1, n + 1),
            "recorded_at": pd.date_range(
                "2026-01-01",
                periods=n,
                freq="s",
                tz="UTC",
            ),
            "measurement_value": values,
        }
    )


def test_detects_injected_spike():
    readings = make_sample_readings()

    results = score_sensor(readings)

    spike = results[
        results["reading_id"] == 151
    ].iloc[0]

    assert bool(spike["is_anomaly"])
    assert spike["anomaly_score"] < 0


def test_returns_one_score_per_reading():
    readings = make_sample_readings()

    results = score_sensor(readings)

    assert len(results) == len(readings)
    assert results["reading_id"].is_unique


def test_results_are_deterministic():
    readings = make_sample_readings()

    first = score_sensor(readings)
    second = score_sensor(readings)

    np.testing.assert_allclose(
        first["anomaly_score"].to_numpy(),
        second["anomaly_score"].to_numpy(),
    )


def test_skips_small_groups():
    readings = make_sample_readings().head(20)

    results = score_sensor(readings)

    assert results.empty


def test_invalid_contamination():
    readings = make_sample_readings()

    with pytest.raises(ValueError):
        score_sensor(readings, contamination=0)
