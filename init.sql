CREATE DATABASE IF NOT EXISTS flask_messenger;

USE flask_messenger;

CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(50) DEFAULT 'anonymous'
);

-- Create the user and grant privileges
CREATE USER IF NOT EXISTS 'flask_user'@'%' IDENTIFIED BY 'password';
GRANT ALL PRIVILEGES ON flask_messenger.* TO 'flask_user'@'%';
FLUSH PRIVILEGES; 