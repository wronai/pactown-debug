-- Faulty SQL with common issues

CREATE TABLE users (
    id INT PRIMARY KEY,
    username VARCHAR(50),
    password VARCHAR(100)
);

SELECT * FROM users;

UPDATE users SET status = 'active';

DELETE FROM orders;

DROP IF EXISTS TABLE old_logs;

INSERT INTO users VALUES (1, 'admin', 'password123');

SELECT * FROM users WHERE username = '' + @input + '';

GRANT ALL PRIVILEGES ON *.* TO 'app_user'@'%';

CREATE USER 'backup'@'localhost' IDENTIFIED BY 'backup_pass_123';

SELECT id, name FROM products ORDER BY created_at;
