
export interface Mission {
    mission_id: number;
    mission_name: string;
    vehicle_id: number;
    vehicle_name: string;
    launch_time: string | null;
    landing_time: string | null;
    status: string;
}

export interface Sensor {
    sensor_id: number;
    sensor_name: string;
    sensor_type: string;
    measurement_unit: string;
}

export interface TelemetryReading {
    reading_id: number;
    mission_id: number;
    sensor_id: number;
    sensor_name: string;
    measurement_unit: string;
    recorded_at: string;
    measurement_value: number;
}

export interface TelemetryResponse {
    mission_id: number;
    total: number;
    limit: number;
    offset: number;
    readings: TelemetryReading[];
}

export interface SensorStats {
    sensor_id: number;
    sensor_name: string;
    measurement_unit: string;
    reading_count: number;
    minimum: number;
    maximum: number;
    average: number;
}

export interface MissionStats {
    mission_id: number;
    mission_name: string;
    total_readings: number;
    first_reading: string | null;
    last_reading: string | null;
    sensors: SensorStats[];
}


export interface AnomalyReading {
    anomaly_id: number;
    reading_id: number;
    mission_id: number;
    sensor_id: number;
    sensor_name: string;
    measurement_unit: string;
    recorded_at: string;
    measurement_value: number;
    anomaly_score: number;
    model_version: string;
}

export interface AnomalyResponse {
    mission_id: number;
    total: number;
    limit: number;
    offset: number;
    anomalies: AnomalyReading[];
}

