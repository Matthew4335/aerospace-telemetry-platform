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
- **SQL Analytics:** Analyze mission performance and sensor measurements using SQL queries and aggregations.
- **REST API:** Build FastAPI endpoints to retrieve mission information and telemetry statistics.
- **Cloud Integration:** Use AWS S3 and RDS for cloud-based storage and database hosting.
- **Anomaly Detection:** Explore Isolation Forest to identify unusual telemetry patterns.

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
- [ ] Python ETL pipeline
- [ ] Data validation and quality checks
- [ ] SQL analytics
- [ ] FastAPI endpoints
- [ ] Docker containerization
- [ ] AWS integration
- [ ] Anomaly detection
- [ ] Automated testing and documentation

## **Author**

**Matthew Brown**  
B.S. Computer Science, Georgia Institute of Technology

[GitHub Profile](https://github.com/Matthew4335)