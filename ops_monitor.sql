CREATE DATABASE IF NOT EXISTS ops_monitor DEFAULT CHARACTER SET utf8mb4;
USE ops_monitor;

CREATE TABLE IF NOT EXISTS server (
    server_id   INT          NOT NULL AUTO_INCREMENT,
    hostname    VARCHAR(64)  NOT NULL,
    ip_address  VARCHAR(45)  NOT NULL,
    os_type     ENUM('linux','windows') NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (server_id)
);

CREATE TABLE IF NOT EXISTS metric_record (
    record_id    BIGINT       NOT NULL AUTO_INCREMENT,
    server_id    INT          NOT NULL,
    cpu_percent  DECIMAL(5,2) NOT NULL,
    mem_percent  DECIMAL(5,2) NOT NULL,
    disk_percent DECIMAL(5,2) NOT NULL,
    recorded_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (record_id),
    INDEX idx_server_time (server_id, recorded_at)
);

CREATE TABLE IF NOT EXISTS alert_log (
    alert_id     INT          NOT NULL AUTO_INCREMENT,
    server_id    INT          NOT NULL,
    alert_type   VARCHAR(32)  NOT NULL,
    metric_value DECIMAL(5,2) NOT NULL,
    threshold    DECIMAL(5,2) NOT NULL,
    is_resolved  TINYINT(1)   NOT NULL DEFAULT 0,
    alerted_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (alert_id)
);
