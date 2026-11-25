-- schema.sql

CREATE DATABASE IF NOT EXISTS attendance_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE attendance_db;

-- ─────────────────────────────────────────────
-- Students master table
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS students (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  reg_no      VARCHAR(20)  NOT NULL UNIQUE,
  name        VARCHAR(100) NOT NULL,
  department  VARCHAR(100) NOT NULL,
  photo_path  VARCHAR(255),
  created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────
-- Face encodings (normalized 64x64 face stored as LONGBLOB)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS face_encodings (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  student_id  INT NOT NULL,
  encoding    LONGBLOB NOT NULL,
  FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────────
-- Attendance sessions (one per class per day)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS attendance_sessions (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  subject       VARCHAR(100) NOT NULL,
  class_name    VARCHAR(50)  NOT NULL,
  session_date  DATE         NOT NULL,
  session_time  TIME         NOT NULL,
  image_path    VARCHAR(255),
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_sessions_date (session_date)
);

-- ─────────────────────────────────────────────
-- Attendance records (many per session)
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS attendance_records (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  session_id  INT NOT NULL,
  student_id  INT NOT NULL,
  status      ENUM('present', 'absent') NOT NULL DEFAULT 'present',
  confidence  FLOAT,
  marked_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_session_student (session_id, student_id),
  FOREIGN KEY (session_id) REFERENCES attendance_sessions(id) ON DELETE CASCADE,
  FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
  INDEX idx_records_session (session_id),
  INDEX idx_records_student (student_id)
);
