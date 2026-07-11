-- ==========================================
-- Database Schema for Recruitment Portal (auth_db)
-- Fully Normalized (1NF, 2NF, 3NF Compliant)
-- ==========================================

-- Create the database if it doesn't exist
CREATE DATABASE IF NOT EXISTS auth_db;
USE auth_db;

-- Disable foreign key checks temporarily to safely drop existing tables
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS applicant_skills;
DROP TABLE IF EXISTS skills_master;
DROP TABLE IF EXISTS educations;
DROP TABLE IF EXISTS work_experience;
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS job_desc;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS applicants;
DROP TABLE IF EXISTS users;
SET FOREIGN_KEY_CHECKS = 1;

-- -----------------------------------------------------
-- Table: users
-- -----------------------------------------------------
-- Stores credentials, role types, and system logins.
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    contact_num VARCHAR(20) NULL,
    user_type VARCHAR(20) NOT NULL CHECK (user_type IN ('Admin', 'HR', 'Applicant'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- Table: applicants
-- -----------------------------------------------------
-- Core applicant demographic profiles.
-- Satisfies 1NF by splitting 'location' into distinct columns.
CREATE TABLE applicants (
    applicant_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    full_name VARCHAR(100) NOT NULL,
    date_of_birth DATE NOT NULL,
    current_location VARCHAR(100) NOT NULL,
    preferred_location VARCHAR(100) NULL,
    resume_url VARCHAR(255) NULL,
    CONSTRAINT fk_applicants_users
        FOREIGN KEY (user_id) REFERENCES users (user_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- Table: jobs
-- -----------------------------------------------------
-- Core properties of job listings for initial input.
CREATE TABLE jobs (
    job_id INT AUTO_INCREMENT PRIMARY KEY,
    job_name VARCHAR(100) NOT NULL,
    max_applicants INT NOT NULL,
    application_status VARCHAR(20) NOT NULL DEFAULT 'Open' CHECK (application_status IN ('Open', 'Closed', 'Paused')),
    opening_date DATE NOT NULL,
    application_deadline DATE NOT NULL
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- Table: job_desc
-- -----------------------------------------------------
-- Secondary structural details for jobs. 
-- Kept separate to facilitate delayed/extended HR input, 
-- but constrained as a strict 1:1 relationship via job_id UNIQUE.
CREATE TABLE job_desc (
    job_desc_id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL UNIQUE,
    description TEXT NOT NULL,
    department VARCHAR(100) NOT NULL,
    employment_type VARCHAR(50) NOT NULL,
    schedule_location VARCHAR(50) NOT NULL,
    location VARCHAR(100) NOT NULL,
    salary_range VARCHAR(50) NULL,
    vacancies INT NOT NULL DEFAULT 1,
    education_baseline VARCHAR(100) NOT NULL,
    required_exp_years INT NOT NULL DEFAULT 0,
    minimum_age INT NOT NULL DEFAULT 18,
    education_notes TEXT NULL,
    CONSTRAINT fk_job_desc_jobs
        FOREIGN KEY (job_id) REFERENCES jobs (job_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- Table: applications
-- -----------------------------------------------------
-- Junction tracking applicant progress through jobs.
CREATE TABLE applications (
    application_id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT NOT NULL,
    applicant_id INT NOT NULL,
    screening_status VARCHAR(50) NOT NULL DEFAULT 'Pending',
    applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_applications_jobs
        FOREIGN KEY (job_id) REFERENCES jobs (job_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_applications_applicants
        FOREIGN KEY (applicant_id) REFERENCES applicants (applicant_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- Table: work_experience
-- -----------------------------------------------------
-- Applicant resume work history records.
CREATE TABLE work_experience (
    work_exp_id INT AUTO_INCREMENT PRIMARY KEY,
    applicant_id INT NOT NULL,
    job_title VARCHAR(100) NOT NULL,
    company_name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NULL, -- NULL represents current job
    description TEXT NULL,
    CONSTRAINT fk_work_experience_applicants
        FOREIGN KEY (applicant_id) REFERENCES applicants (applicant_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- Table: educations
-- -----------------------------------------------------
-- Academic achievements for applicants.
CREATE TABLE educations (
    education_id INT AUTO_INCREMENT PRIMARY KEY,
    applicant_id INT NOT NULL,
    degree_level VARCHAR(100) NOT NULL,
    major VARCHAR(100) NOT NULL,
    institution VARCHAR(150) NOT NULL,
    graduation_year INT NOT NULL,
    CONSTRAINT fk_educations_applicants
        FOREIGN KEY (applicant_id) REFERENCES applicants (applicant_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- Table: skills_master
-- -----------------------------------------------------
-- Standard dictionary of unique skills.
CREATE TABLE skills_master (
    skill_id INT AUTO_INCREMENT PRIMARY KEY,
    skill_name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -----------------------------------------------------
-- Table: applicant_skills
-- -----------------------------------------------------
-- Junction mapping applicants to recognized skills.
CREATE TABLE applicant_skills (
    applicant_id INT NOT NULL,
    skill_id INT NOT NULL,
    PRIMARY KEY (applicant_id, skill_id),
    CONSTRAINT fk_app_skills_applicants
        FOREIGN KEY (applicant_id) REFERENCES applicants (applicant_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_app_skills_master
        FOREIGN KEY (skill_id) REFERENCES skills_master (skill_id)
        ON DELETE CASCADE ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;