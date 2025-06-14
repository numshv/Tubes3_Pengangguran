CREATE DATABASE IF NOT EXISTS ats_pengangguran1;
USE ats_pengangguran2;

CREATE TABLE IF NOT EXISTS ApplicantProfile (
    applicant_id INT PRIMARY KEY NOT NULL,
    first_name VARCHAR(50) DEFAULT NULL,
    last_name VARCHAR(50) DEFAULT NULL,
    date_of_birth DATE DEFAULT NULL,
    address VARCHAR(255) DEFAULT NULL,
    phone_number VARCHAR(20) DEFAULT NULL
);

CREATE TABLE ApplicantDetail(
    applicant_id PRIMARY KEY NOT NULL AUTO_INCREMENT,
    application_role_varchar(100) DEFAULT NULL,
    cv_path TEXT
)