CREATE TABLE IF NOT EXISTS food (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    user_id             VARCHAR(64) NOT NULL,
    category            VARCHAR(50) NOT NULL,
    food_name           VARCHAR(100) NOT NULL,
    create_date         DATE NOT NULL,
    valid_date          DATE NOT NULL,
    days_left_to_notify INT NOT NULL,
    created_at          DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_food_user_id (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
