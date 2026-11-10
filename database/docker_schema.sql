--
-- PostgreSQL database dump
--

\restrict YRwZvBVBf0I7Kb3wPnOUVPHdLybgoSHMXffd9NTF2iw4xE3wqC3EudrF9ckAqBH

-- Dumped from database version 18.6 (Homebrew)
-- Dumped by pg_dump version 18.6 (Homebrew)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: anomaly_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.anomaly_events (
    anomaly_id bigint NOT NULL,
    reading_id bigint NOT NULL,
    detection_method character varying(50) NOT NULL,
    anomaly_score double precision,
    description text,
    detected_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT valid_anomaly_score CHECK (((anomaly_score IS NULL) OR (anomaly_score <> ALL (ARRAY['Infinity'::double precision, '-Infinity'::double precision, 'NaN'::double precision]))))
);


--
-- Name: anomaly_events_anomaly_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.anomaly_events ALTER COLUMN anomaly_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.anomaly_events_anomaly_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: missions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.missions (
    mission_id integer NOT NULL,
    vehicle_id integer NOT NULL,
    mission_name character varying(100) NOT NULL,
    launch_time timestamp with time zone NOT NULL,
    landing_time timestamp with time zone,
    status character varying(20) DEFAULT 'planned'::character varying NOT NULL,
    CONSTRAINT valid_mission_status CHECK (((status)::text = ANY ((ARRAY['planned'::character varying, 'active'::character varying, 'completed'::character varying, 'aborted'::character varying])::text[]))),
    CONSTRAINT valid_mission_times CHECK (((landing_time IS NULL) OR (landing_time >= launch_time)))
);


--
-- Name: missions_mission_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.missions ALTER COLUMN mission_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.missions_mission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: sensors; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sensors (
    sensor_id integer NOT NULL,
    vehicle_id integer NOT NULL,
    sensor_name character varying(100) NOT NULL,
    sensor_type character varying(50) NOT NULL,
    measurement_unit character varying(20) NOT NULL
);


--
-- Name: sensors_sensor_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.sensors ALTER COLUMN sensor_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.sensors_sensor_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: telemetry_readings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.telemetry_readings (
    reading_id bigint NOT NULL,
    mission_id integer NOT NULL,
    sensor_id integer NOT NULL,
    recorded_at timestamp with time zone NOT NULL,
    measurement_value double precision NOT NULL,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT valid_measurement_value CHECK ((measurement_value <> ALL (ARRAY['Infinity'::double precision, '-Infinity'::double precision, 'NaN'::double precision])))
);


--
-- Name: telemetry_readings_reading_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.telemetry_readings ALTER COLUMN reading_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.telemetry_readings_reading_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: vehicles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.vehicles (
    vehicle_id integer NOT NULL,
    vehicle_name character varying(100) NOT NULL,
    vehicle_type character varying(50) NOT NULL,
    manufacturer character varying(100),
    created_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: vehicles_vehicle_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

ALTER TABLE public.vehicles ALTER COLUMN vehicle_id ADD GENERATED ALWAYS AS IDENTITY (
    SEQUENCE NAME public.vehicles_vehicle_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1
);


--
-- Name: anomaly_events anomaly_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anomaly_events
    ADD CONSTRAINT anomaly_events_pkey PRIMARY KEY (anomaly_id);


--
-- Name: missions missions_mission_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.missions
    ADD CONSTRAINT missions_mission_name_key UNIQUE (mission_name);


--
-- Name: missions missions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.missions
    ADD CONSTRAINT missions_pkey PRIMARY KEY (mission_id);


--
-- Name: sensors sensors_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sensors
    ADD CONSTRAINT sensors_pkey PRIMARY KEY (sensor_id);


--
-- Name: telemetry_readings telemetry_readings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telemetry_readings
    ADD CONSTRAINT telemetry_readings_pkey PRIMARY KEY (reading_id);


--
-- Name: anomaly_events unique_reading_detection; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anomaly_events
    ADD CONSTRAINT unique_reading_detection UNIQUE (reading_id, detection_method);


--
-- Name: telemetry_readings unique_sensor_reading; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telemetry_readings
    ADD CONSTRAINT unique_sensor_reading UNIQUE (mission_id, sensor_id, recorded_at);


--
-- Name: sensors unique_vehicle_sensor; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sensors
    ADD CONSTRAINT unique_vehicle_sensor UNIQUE (vehicle_id, sensor_name);


--
-- Name: vehicles vehicles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_pkey PRIMARY KEY (vehicle_id);


--
-- Name: vehicles vehicles_vehicle_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.vehicles
    ADD CONSTRAINT vehicles_vehicle_name_key UNIQUE (vehicle_name);


--
-- Name: anomaly_events anomaly_events_reading_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.anomaly_events
    ADD CONSTRAINT anomaly_events_reading_id_fkey FOREIGN KEY (reading_id) REFERENCES public.telemetry_readings(reading_id);


--
-- Name: missions missions_vehicle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.missions
    ADD CONSTRAINT missions_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES public.vehicles(vehicle_id);


--
-- Name: sensors sensors_vehicle_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sensors
    ADD CONSTRAINT sensors_vehicle_id_fkey FOREIGN KEY (vehicle_id) REFERENCES public.vehicles(vehicle_id);


--
-- Name: telemetry_readings telemetry_readings_mission_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telemetry_readings
    ADD CONSTRAINT telemetry_readings_mission_id_fkey FOREIGN KEY (mission_id) REFERENCES public.missions(mission_id);


--
-- Name: telemetry_readings telemetry_readings_sensor_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.telemetry_readings
    ADD CONSTRAINT telemetry_readings_sensor_id_fkey FOREIGN KEY (sensor_id) REFERENCES public.sensors(sensor_id);


--
-- PostgreSQL database dump complete
--

\unrestrict YRwZvBVBf0I7Kb3wPnOUVPHdLybgoSHMXffd9NTF2iw4xE3wqC3EudrF9ckAqBH

