
import type {
    Mission,
    Sensor,
    MissionStats,
    TelemetryReading,
    TelemetryResponse,
    AnomalyReading,
    AnomalyResponse,
} from "./types";

const API_BASE_URL = (
    import.meta.env.VITE_API_BASE_URL ||
    "http://localhost:8000"
).replace(/\/$/, "");

async function request<T>(
    path: string,
    signal?: AbortSignal
): Promise<T> {
    const response = await fetch(
        `${API_BASE_URL}${path}`,
        { signal }
    );

    if (!response.ok) {
        throw new Error(
            `API request failed: ${response.status} ${response.statusText}`
        );
    }

    return (await response.json()) as T;
}

// Retrieve all missions.
export function getMissions(
    signal?: AbortSignal
): Promise<Mission[]> {
    return request<Mission[]>("/missions", signal);
}

// Retrieve available sensors for one mission.
export function getMissionSensors(
    missionId: number,
    signal?: AbortSignal
): Promise<Sensor[]> {
    return request<Sensor[]>(
        `/missions/${missionId}/sensors`,
        signal
    );
}

// Retrieve mission and sensor statistics.
export function getMissionStats(
    missionId: number,
    signal?: AbortSignal
): Promise<MissionStats> {
    return request<MissionStats>(
        `/missions/${missionId}/stats`,
        signal
    );
}

// Retrieve ALL pages of telemetry for one sensor.
export async function getAllTelemetry(
    missionId: number,
    sensorId: number,
    signal?: AbortSignal
): Promise<TelemetryReading[]> {
    const pageSize = 1000;
    let offset = 0;
    let total = Infinity;

    const readings: TelemetryReading[] = [];

    while (offset < total) {
        const params = new URLSearchParams({
            sensor_id: String(sensorId),
            limit: String(pageSize),
            offset: String(offset),
        });

        const page = await request<TelemetryResponse>(
            `/missions/${missionId}/telemetry?${params}`,
            signal
        );

        readings.push(...page.readings);

        total = page.total;
        offset += page.readings.length;

        // Prevent an infinite loop on an empty page.
        if (page.readings.length === 0) {
            break;
        }
    }

    return readings;
}


// Retrieve all anomaly pages for a mission and sensor.
export async function getAllAnomalies(
    missionId: number,
    sensorId: number,
    signal?: AbortSignal
): Promise<AnomalyReading[]> {
    const pageSize = 1000;
    let offset = 0;
    let total = Infinity;

    const anomalies: AnomalyReading[] = [];

    while (offset < total) {
        const params = new URLSearchParams({
            sensor_id: String(sensorId),
            limit: String(pageSize),
            offset: String(offset),
        });

        const page = await request<AnomalyResponse>(
            `/missions/${missionId}/anomalies?${params}`,
            signal
        );

        anomalies.push(...page.anomalies);

        total = page.total;
        offset += page.anomalies.length;

        if (page.anomalies.length === 0) {
            break;
        }
    }

    return anomalies;
}

