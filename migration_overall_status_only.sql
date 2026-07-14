-- Run this against your existing database. It only adds the new table —
-- it does not touch any existing table or data.

CREATE TABLE IF NOT EXISTS application_overall_status (
    overall_id INT AUTO_INCREMENT PRIMARY KEY,
    application_id INT NOT NULL,
    pre_screen_snapshot VARCHAR(50) NOT NULL,
    chatbot_snapshot VARCHAR(50) NULL,
    overall_status VARCHAR(50) NOT NULL DEFAULT 'Pending',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_overall_status_application
        FOREIGN KEY (application_id) REFERENCES applications(application_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT uq_overall_status_application UNIQUE (application_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
