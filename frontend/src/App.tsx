
import {
  useEffect,
  useState,
} from "react";

import {
  getAllTelemetry,
  getAllAnomalies,
  getMissionSensors,
  getMissionStats,
  getMissions,
} from "./api";

import TelemetryChart from "./components/TelemetryChart";

import type {
  Mission,
  MissionStats,
  Sensor,
  TelemetryReading,
  AnomalyReading,
} from "./types";

function formatNumber(
  value: number | null | undefined
): string {
  if (value === null || value === undefined) {
    return "—";
  }

  return value.toLocaleString(undefined, {
    maximumFractionDigits: 2,
  });
}

function formatDate(
  value: string | null | undefined
): string {
  if (!value) {
    return "—";
  }

  return new Date(value).toLocaleString();
}

export default function App() {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [missionId, setMissionId] = useState<number | null>(
    null
  );

  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [sensorId, setSensorId] = useState<number | null>(
    null
  );

  const [stats, setStats] = useState<MissionStats | null>(
    null
  );

  const [readings, setReadings] = useState<
    TelemetryReading[]
  >([]);

  const [anomalies, setAnomalies] = useState<
    AnomalyReading[]
  >([]);

  const [loadingAnomalies, setLoadingAnomalies] =
    useState(false);

  const [anomalyError, setAnomalyError] =
    useState<string | null>(null);

  const [showAnomalies, setShowAnomalies] =
    useState(true);

  const [loadingMissions, setLoadingMissions] =
    useState(true);

  const [loadingDetails, setLoadingDetails] =
    useState(false);

  const [loadingTelemetry, setLoadingTelemetry] =
    useState(false);

  const [missionsError, setMissionsError] =
    useState<string | null>(null);

  const [detailsError, setDetailsError] =
    useState<string | null>(null);

  const [telemetryError, setTelemetryError] =
    useState<string | null>(null);

  // 1. Load the mission list when the app opens.
  useEffect(() => {
    const controller = new AbortController();

    setLoadingMissions(true);

    getMissions(controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return;

        setMissions(data);
        setMissionId(data[0]?.mission_id ?? null);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;

        setMissionsError(String(error));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoadingMissions(false);
        }
      });

    return () => controller.abort();
  }, []);

  // 2. Load sensors and statistics for the mission.
  useEffect(() => {
    setSensors([]);
    setSensorId(null);
    setStats(null);
    setReadings([]);
    setDetailsError(null);

    if (missionId === null) {
      setLoadingDetails(false);
      return;
    }

    const controller = new AbortController();

    setLoadingDetails(true);

    Promise.all([
      getMissionSensors(missionId, controller.signal),
      getMissionStats(missionId, controller.signal),
    ])
      .then(([sensorData, missionStats]) => {
        if (controller.signal.aborted) return;

        setSensors(sensorData);
        setStats(missionStats);

        // Automatically choose the first sensor.
        setSensorId(
          sensorData[0]?.sensor_id ?? null
        );
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;

        setDetailsError(String(error));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoadingDetails(false);
        }
      });

    return () => controller.abort();
  }, [missionId]);

  // 3. Load readings whenever the sensor changes.
  useEffect(() => {
    setReadings([]);
    setTelemetryError(null);

    if (missionId === null || sensorId === null) {
      setLoadingTelemetry(false);
      return;
    }

    const controller = new AbortController();

    setLoadingTelemetry(true);

    getAllTelemetry(
      missionId,
      sensorId,
      controller.signal
    )
      .then((data) => {
        if (controller.signal.aborted) return;

        setReadings(data);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;

        setTelemetryError(String(error));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoadingTelemetry(false);
        }
      });

    return () => controller.abort();
  }, [missionId, sensorId]);


  useEffect(() => {
    setAnomalies([]);
    setAnomalyError(null);

    if (missionId === null || sensorId === null) {
      setLoadingAnomalies(false);
      return;
    }

    const controller = new AbortController();

    setLoadingAnomalies(true);

    getAllAnomalies(
      missionId,
      sensorId,
      controller.signal
    )
      .then((data) => {
        if (controller.signal.aborted) return;

        setAnomalies(data);
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;

        setAnomalyError(String(error));
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoadingAnomalies(false);
        }
      });

    return () => controller.abort();
  }, [missionId, sensorId]);


  const selectedMission = missions.find(
    (mission) => mission.mission_id === missionId
  );

  const selectedSensor = sensors.find(
    (sensor) => sensor.sensor_id === sensorId
  );

  const selectedSensorStats = stats?.sensors.find(
    (sensor) => sensor.sensor_id === sensorId
  );

  const anomalyPercentage =
    readings.length > 0
      ? (anomalies.length / readings.length) * 100
      : 0;

  const mostUnusualAnomaly =
    anomalies.length > 0
      ? anomalies.reduce((lowest, current) =>
        current.anomaly_score < lowest.anomaly_score
          ? current
          : lowest
      )
      : null;

  const recentReadings = readings
    .slice(-8)
    .reverse();

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-icon">◈</span>

          <div>
            <h1>Aerospace Telemetry</h1>
            <p>Mission Analytics Platform</p>
          </div>
        </div>

        <span className="environment-pill">
          LOCAL DEVELOPMENT
        </span>
      </header>

      <main className="dashboard">
        <div className="page-heading">
          <div>
            <p className="eyebrow">
              MISSION CONTROL / OVERVIEW
            </p>

            <h2>Flight Telemetry Dashboard</h2>

            <p className="muted">
              Explore mission data, sensor readings,
              and flight statistics.
            </p>
          </div>
        </div>

        {missionsError && (
          <div className="alert" role="alert">
            Could not load missions: {missionsError}
          </div>
        )}

        <section className="panel filters">
          <div className="field">
            <label htmlFor="mission-select">
              Mission
            </label>

            <select
              id="mission-select"
              value={missionId ?? ""}
              disabled={
                loadingMissions ||
                missions.length === 0
              }
              onChange={(event) => {
                setMissionId(
                  Number(event.target.value)
                );
              }}
            >
              {missions.length === 0 && (
                <option value="">
                  {loadingMissions
                    ? "Loading missions..."
                    : "No missions available"}
                </option>
              )}

              {missions.map((mission) => (
                <option
                  key={mission.mission_id}
                  value={mission.mission_id}
                >
                  {mission.mission_name}
                </option>
              ))}
            </select>
          </div>

          <div className="field">
            <label htmlFor="sensor-select">
              Sensor
            </label>

            <select
              id="sensor-select"
              value={sensorId ?? ""}
              disabled={
                loadingDetails ||
                sensors.length === 0
              }
              onChange={(event) => {
                setSensorId(
                  Number(event.target.value)
                );
              }}
            >
              {sensors.length === 0 && (
                <option value="">
                  {loadingDetails
                    ? "Loading sensors..."
                    : "No sensors available"}
                </option>
              )}

              {sensors.map((sensor) => (
                <option
                  key={sensor.sensor_id}
                  value={sensor.sensor_id}
                >
                  {sensor.sensor_name} —{" "}
                  {sensor.sensor_type}
                </option>
              ))}
            </select>
          </div>
        </section>

        {detailsError && (
          <div className="alert" role="alert">
            Could not load mission details:{" "}
            {detailsError}
          </div>
        )}

        <section className="metrics-grid">
          <div className="metric-card">
            <span className="metric-label">
              Selected Mission
            </span>

            <strong className="metric-value">
              {selectedMission?.mission_name ?? "—"}
            </strong>

            <span className="metric-detail">
              {selectedMission?.vehicle_name ??
                "No vehicle selected"}
            </span>
          </div>

          <div className="metric-card">
            <span className="metric-label">
              Total Readings
            </span>

            <strong className="metric-value">
              {formatNumber(stats?.total_readings)}
            </strong>

            <span className="metric-detail">
              Mission-wide telemetry
            </span>
          </div>

          <div className="metric-card">
            <span className="metric-label">
              Sensors
            </span>

            <strong className="metric-value">
              {stats?.sensors.length ?? "—"}
            </strong>

            <span className="metric-detail">
              Sensors with recorded data
            </span>
          </div>

          <div className="metric-card">
            <span className="metric-label">
              Mission Status
            </span>

            <strong className="metric-value">
              {selectedMission?.status ?? "—"}
            </strong>

            <span className="metric-detail">
              Recorded mission state
            </span>
          </div>
        </section>

        <section className="panel mission-details">
          <div className="section-heading">
            <div>
              <p className="eyebrow">
                FLIGHT INFORMATION
              </p>
              <h2>Mission Summary</h2>
            </div>
          </div>

          <div className="detail-grid">
            <div>
              <span className="detail-label">
                First Telemetry Reading
              </span>
              <strong>
                {formatDate(stats?.first_reading)}
              </strong>
            </div>

            <div>
              <span className="detail-label">
                Last Telemetry Reading
              </span>
              <strong>
                {formatDate(stats?.last_reading)}
              </strong>
            </div>

            <div>
              <span className="detail-label">
                Selected Sensor
              </span>
              <strong>
                {selectedSensor?.sensor_name ?? "—"}
              </strong>
            </div>

            <div>
              <span className="detail-label">
                Measurement Unit
              </span>
              <strong>
                {selectedSensor?.measurement_unit ??
                  "—"}
              </strong>
            </div>
          </div>
        </section>

        <section className="sensor-stats-grid">
          {[
            {
              label: "Sensor Readings",
              value: formatNumber(
                selectedSensorStats?.reading_count
              ),
            },
            {
              label: "Minimum",
              value: formatNumber(
                selectedSensorStats?.minimum
              ),
            },
            {
              label: "Maximum",
              value: formatNumber(
                selectedSensorStats?.maximum
              ),
            },
            {
              label: "Average",
              value: formatNumber(
                selectedSensorStats?.average
              ),
            },
          ].map((item) => (
            <div
              key={item.label}
              className="small-metric-card"
            >
              <span className="metric-label">
                {item.label}
              </span>

              <strong>
                {item.value}
              </strong>
            </div>
          ))}
        </section>


        <section className="anomaly-summary">
          <div className="anomaly-metric">
            <span className="metric-label">
              Detected Anomalies
            </span>

            <strong className="anomaly-count">
              {loadingAnomalies
                ? "Loading..."
                : anomalyError
                  ? "—"
                  : anomalies.length.toLocaleString()}
            </strong>

            <span className="metric-detail">
              Isolation Forest predictions
            </span>
          </div>

          <div className="anomaly-metric">
            <span className="metric-label">
              Anomaly Percentage
            </span>

            <strong className="anomaly-count">
              {loadingAnomalies || anomalyError
                ? "—"
                : `${anomalyPercentage.toFixed(2)}%`}
            </strong>

            <span className="metric-detail">
              Selected sensor readings
            </span>
          </div>

          <div className="anomaly-metric">
            <span className="metric-label">
              Lowest Decision Score
            </span>

            <strong className="anomaly-count">
              {loadingAnomalies || anomalyError
                ? "—"
                : mostUnusualAnomaly
                  ? mostUnusualAnomaly.anomaly_score.toFixed(4)
                  : "—"}
            </strong>

            <span className="metric-detail">
              More negative indicates more anomalous
            </span>
          </div>
        </section>

        {anomalyError && (
          <div className="alert" role="alert">
            Could not load anomalies: {anomalyError}
          </div>
        )}

        <div className="anomaly-toggle">
          <label>
            <input
              type="checkbox"
              checked={showAnomalies}
              onChange={(event) =>
                setShowAnomalies(event.target.checked)
              }
            />
            Show anomaly markers on chart
          </label>
        </div>


        {telemetryError && (
          <div className="alert" role="alert">
            Could not load telemetry:{" "}
            {telemetryError}
          </div>
        )}

        {loadingDetails || loadingTelemetry ? (
          <section className="panel loading-panel">
            Loading telemetry data...
          </section>
        ) : selectedSensor ? (
          <TelemetryChart
            sensor={selectedSensor}
            readings={readings}
            anomalies={anomalies}
            showAnomalies={showAnomalies}
          />
        ) : (
          <section className="panel loading-panel">
            Select a mission and sensor to view data.
          </section>
        )}


        <section className="panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">
                MACHINE LEARNING / ANOMALIES
              </p>

              <h2>Detected Anomalies</h2>

              <p className="muted">
                Isolation Forest results for the
                selected sensor.
              </p>
            </div>

            <span className="count-pill">
              {anomalies.length} flagged
            </span>
          </div>

          {loadingAnomalies ? (
            <p className="empty-state">
              Loading anomaly predictions...
            </p>
          ) : anomalyError ? (
            <p className="empty-state">
              Anomaly predictions are unavailable.
            </p>
          ) : anomalies.length === 0 ? (
            <p className="empty-state">
              No anomalies found for this sensor.
            </p>
          ) : (
            <div className="table-scroll">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Reading ID</th>
                    <th>Timestamp</th>
                    <th>Sensor</th>
                    <th>Measurement</th>
                    <th>Anomaly Score</th>
                  </tr>
                </thead>

                <tbody>
                  {[...anomalies]
                    .sort(
                      (a, b) =>
                        a.anomaly_score - b.anomaly_score
                    )
                    .slice(0, 20)
                    .map((anomaly) => (
                      <tr key={anomaly.anomaly_id}>
                        <td>{anomaly.reading_id}</td>

                        <td>
                          {formatDate(anomaly.recorded_at)}
                        </td>

                        <td>
                          {anomaly.sensor_name}
                        </td>

                        <td>
                          {formatNumber(
                            anomaly.measurement_value
                          )}{" "}
                          {anomaly.measurement_unit}
                        </td>

                        <td className="score-negative">
                          {anomaly.anomaly_score.toFixed(4)}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          )}

          <p className="chart-note">
            Showing the 20 lowest-scoring readings.
            Lower decision scores indicate more
            statistically unusual observations.
          </p>
        </section>


        <section className="panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">
                RAW SENSOR DATA
              </p>
              <h2>Recent Readings</h2>
            </div>
          </div>

          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Reading ID</th>
                  <th>Timestamp</th>
                  <th>Sensor</th>
                  <th>Value</th>
                </tr>
              </thead>

              <tbody>
                {recentReadings.map((reading) => (
                  <tr key={reading.reading_id}>
                    <td>{reading.reading_id}</td>

                    <td>
                      {formatDate(
                        reading.recorded_at
                      )}
                    </td>

                    <td>
                      {reading.sensor_name}
                    </td>

                    <td>
                      {formatNumber(
                        reading.measurement_value
                      )}{" "}
                      {reading.measurement_unit}
                    </td>
                  </tr>
                ))}

                {recentReadings.length === 0 && (
                  <tr>
                    <td colSpan={4}>
                      No readings to display.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </main>

      <footer className="footer">
        Aerospace Telemetry Platform · React +
        FastAPI + PostgreSQL
      </footer>
    </div>
  );
}
