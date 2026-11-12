import { useMemo } from "react";

import {
    CartesianGrid,
    Line,
    LineChart,
    ReferenceDot,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";

import type {
    AnomalyReading,
    Sensor,
    TelemetryReading,
} from "../types";

interface TelemetryChartProps {
    sensor: Sensor;
    readings: TelemetryReading[];
    anomalies: AnomalyReading[];
    showAnomalies: boolean;
}

export default function TelemetryChart({
    sensor,
    readings,
    anomalies,
    showAnomalies,
}: TelemetryChartProps) {
    const anomalyIds = useMemo(
        () => new Set(
            anomalies.map((a) => a.reading_id)
        ),
        [anomalies]
    );

    const chartData = useMemo(() => {
        return readings
            .map((reading) => ({
                ...reading,
                timestamp: new Date(
                    reading.recorded_at
                ).getTime(),
            }))
            .filter(
                (reading) =>
                    Number.isFinite(reading.timestamp) &&
                    Number.isFinite(reading.measurement_value)
            )
            .sort(
                (a, b) =>
                    a.timestamp - b.timestamp ||
                    a.reading_id - b.reading_id
            );
    }, [readings]);

    // Find chart points matching ML anomaly reading IDs.
    const flaggedPoints = useMemo(() => {
        return chartData.filter(
            (reading) => anomalyIds.has(reading.reading_id)
        );
    }, [chartData, anomalyIds]);

    return (
        <section className="panel chart-panel">
            <div className="section-heading">
                <div>
                    <p className="eyebrow">
                        TELEMETRY TIMESERIES
                    </p>

                    <h2>{sensor.sensor_name}</h2>

                    <p className="muted">
                        {sensor.sensor_type} ·{" "}
                        {sensor.measurement_unit}
                    </p>
                </div>

                <span className="count-pill">
                    {chartData.length.toLocaleString()} points
                </span>
            </div>

            <div className="chart-legend">
                <span>
                    <span className="legend-line" />
                    Telemetry
                </span>

                <span>
                    <span className="legend-dot" />
                    Detected anomaly
                </span>
            </div>

            {chartData.length === 0 ? (
                <p className="empty-state">
                    No telemetry readings available.
                </p>
            ) : (
                <div className="chart-wrapper">
                    <ResponsiveContainer
                        width="100%"
                        height="100%"
                    >
                        <LineChart
                            data={chartData}
                            margin={{
                                top: 12,
                                right: 24,
                                bottom: 12,
                                left: 0,
                            }}
                        >
                            <CartesianGrid
                                stroke="#25334a"
                                strokeDasharray="3 4"
                                vertical={false}
                            />

                            <XAxis
                                dataKey="timestamp"
                                type="number"
                                scale="time"
                                domain={["dataMin", "dataMax"]}
                                tickFormatter={(value) =>
                                    new Date(value).toLocaleTimeString(
                                        [],
                                        {
                                            hour: "2-digit",
                                            minute: "2-digit",
                                            second: "2-digit",
                                        }
                                    )
                                }
                                tick={{
                                    fill: "#94a3b8",
                                    fontSize: 11,
                                }}
                                stroke="#465670"
                            />

                            <YAxis
                                width={78}
                                domain={["auto", "auto"]}
                                tickFormatter={(value) =>
                                    Number(value).toLocaleString()
                                }
                                tick={{
                                    fill: "#94a3b8",
                                    fontSize: 11,
                                }}
                                stroke="#465670"
                            />

                            <Tooltip
                                labelFormatter={(value) =>
                                    new Date(
                                        Number(value)
                                    ).toLocaleString()
                                }
                                formatter={(value) => [
                                    Number(value).toLocaleString(
                                        undefined,
                                        { maximumFractionDigits: 2 }
                                    ),
                                    `${sensor.sensor_name} (${sensor.measurement_unit})`,
                                ]}
                                contentStyle={{
                                    backgroundColor: "#142238",
                                    border: "1px solid #334155",
                                    borderRadius: "8px",
                                    color: "#f8fafc",
                                }}
                            />

                            <Line
                                type="linear"
                                dataKey="measurement_value"
                                stroke="#38bdf8"
                                strokeWidth={2}
                                dot={false}
                                activeDot={{ r: 5 }}
                                isAnimationActive={false}
                            />

                            {showAnomalies &&
                                flaggedPoints.map((reading) => (
                                    <ReferenceDot
                                        key={reading.reading_id}
                                        x={reading.timestamp}
                                        y={reading.measurement_value}
                                        r={5}
                                        fill="#fb7185"
                                        stroke="#ffffff"
                                        strokeWidth={1}
                                        ifOverflow="discard"
                                    />
                                ))}
                        </LineChart>
                    </ResponsiveContainer>
                </div>
            )}

            <p className="chart-note">
                Red markers indicate measurements flagged
                by Isolation Forest. Predictions are
                statistical outliers, not confirmed faults.
            </p>
        </section>
    );
}
