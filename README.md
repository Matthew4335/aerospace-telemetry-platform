# Aerospace Telemetry Data Engineering Platform

**An end-to-end data engineering platform for ingesting, processing, validating, and analyzing simulated aerospace flight telemetry.**

**Tech Stack:** Python · Pandas · PostgreSQL · SQL · FastAPI · Docker · AWS

## **Overview**

This project develops a data pipeline for processing simulated rocket flight telemetry. It focuses on building the backend infrastructure needed to ingest raw sensor measurements, transform and validate data, store structured records, and support mission-level analysis.

The platform uses synthetic flight data, including altitude, velocity, temperature, pressure, and battery voltage, to demonstrate practical data engineering concepts in an aerospace context.

## **Key Features**

- **Data Ingestion:** Generate and ingest simulated aerospace telemetry from CSV datasets.
- **ETL Pipeline:** Use Python and Pandas to clean, transform, and load telemetry data.
- **Data Validation:** Identify missing values, duplicate records, invalid timestamps, and inconsistent measurements.
- **Database Engineering:** Design a PostgreSQL database connecting missions, vehicles, sensors, and telemetry readings.
- **SQL Analytics** — Analyze mission performance and sensor measurements using SQL queries and aggregations.

  To run the analytics from the repository root:

  ```bash
  psql -X -P pager=off -v ON_ERROR_STOP=1 \
    -d aerospace_telemetry -f database/analytics.sql
  ```
- **REST API** — Retrieve mission information, telemetry readings, and sensor statistics through a read-only API built with FastAPI, SQLAlchemy, and PostgreSQL.

  | Endpoint | Description |
  | --- | --- |
  | `GET /health` | Check API availability |
  | `GET /missions` | List all missions |
  | `GET /missions/{mission_id}` | Retrieve mission details |
  | `GET /missions/{mission_id}/telemetry` | Retrieve telemetry with sensor, timestamp, and pagination filters |
  | `GET /missions/{mission_id}/stats` | Retrieve mission and per-sensor statistics |
  | `GET /missions/{mission_id}/sensors` | Retrieve sensors with telemetry for a mission |
  | `GET /missions/{mission_id}/anomalies` | Retrieve paginated anomaly predictions |

  **Run locally**

  ```bash
  python -m uvicorn api.main:app --reload
  ```

  Open the interactive documentation at http://127.0.0.1:8000/docs.

  **Run API tests**

  ```bash
  python -m pytest tests/test_api.py -v
  ```

- **Docker Deployment** - Run the platform locally with Docker Compose using separate FastAPI, PostgreSQL, and batch ETL services. The configuration uses PostgreSQL 18 and Python 3.11.

  **Build and Start**

  ```bash
  docker compose build api etl
  docker compose up -d db api
  ```

  **Load Sample Telemetry**

  ```bash
  docker compose run --rm etl
  ```

  Open the interactive API documentation at http://localhost:8000/docs.

  **Verify the Database**

  ```bash
  docker compose exec db sh -c \
    'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT COUNT(*) FROM telemetry_readings;"'
  ```

  **Stop the Application**

  ```bash
  docker compose down
  ```

- **Cloud Integration** — Use AWS S3 and RDS for cloud storage and database hosting.
- **Anomaly Detection** — Explore Isolation Forest to identify unusual telemetry patterns.

    The platform includes an unsupervised anomaly detection
    pipeline built using scikit-learn's Isolation Forest.

    The model analyzes telemetry independently for each
    mission and sensor, using three engineered features:

    - Raw sensor measurement
    - Absolute deviation from a local rolling median
    - Absolute change between consecutive measurements

    Detected anomalies are stored in the PostgreSQL
    `telemetry_anomalies` table and linked to the original
    telemetry readings.


    **Run with Docker**

    ```bash
    docker compose build ml
    docker compose run --rm ml
    ```

## React Telemetry Dashboard

The project includes a React and TypeScript dashboard for
exploring mission telemetry through the FastAPI backend.

Features:
- Dynamic mission and sensor selection
- Interactive time-series telemetry charts
- Mission-wide and sensor-specific statistics
- Automatic pagination for complete telemetry retrieval
- Responsive layout and API error handling

## **Technology Stack**

| Category | Technologies |
|---|---|
| Programming | Python |
| Data Processing | Pandas, NumPy |
| Database | PostgreSQL, SQL, SQLAlchemy |
| Backend | FastAPI |
| Cloud | AWS S3, AWS RDS |
| DevOps | Docker, Git, GitHub Actions |
| Machine Learning | Scikit-learn |

## **Database Design**

The platform uses a relational database organized around five primary entities:

- `missions` – Mission metadata and flight information.
- `vehicles` – Rocket and vehicle information.
- `sensors` – Sensor identifiers and specifications.
- `telemetry_readings` – Timestamped flight measurements.
- `anomaly_events` – Records of detected data quality issues and unusual measurements.

## **Project Structure**

```text
aerospace-telemetry-platform/
├── data/
├── database/
├── etl/
├── api/
├── anomaly_detection/
├── tests/
├── README.md
├── requirements.txt
└── .gitignore
```

## **Development Progress**

- [x] Project structure and development environment
- [x] GitHub repository setup
- [x] PostgreSQL database schema
- [x] Synthetic telemetry generation
- [x] Python ETL pipeline
- [x] Data validation and quality checks
- [x] SQL analytics
- [x] FastAPI endpoints
- [x] Docker containerization
- [x] Anomaly detection
- [ ] Automated testing and documentation

## **Author**

**Matthew Brown**  
B.S. Computer Science, Georgia Institute of Technology

[GitHub Profile](https://github.com/Matthew4335)