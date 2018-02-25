/* models.sql */
/* mysql -u root -p < schema.sql */

DROP DATABASE IF EXISTS awesome;
CREATE DATABASE awesome;
USE awesome;

/* GRANT SELECT, INSERT, UPDATE, DELET ON awesome.* to 'www-data'@'localhost' identified by 'www.data' */

CREATE TABLE IF NOT EXISTS users(
    id VARCHAR(50) NOT NULL,
    email VARCHAR(50) NOT NULL,
    passwd VARCHAR(50) NOT NULL,
    admin BOOL NOT NULL,
    name VARCHAR(50) NOT NULL,
    image VARCHAR(500) NOT NULL,
    created_at REAL NOT NULL,
    UNIQUE KEY idx_email (email),
    KEY idx_created_at (created_at),
    PRIMARY KEY(id)
)engine=innodb DEFAULT charset=utf8;


CREATE TABLE IF NOT EXISTS blogs(
    id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    user_name VARCHAR(50) NOT NULL,
    user_image VARCHAR(500) NOT NULL,
    name VARCHAR(50) NOT NULL,
    summary VARCHAR(200) NOT NULL,
    content MEDIUMTEXT NOT NULL,
    created_at REAL NOT NULL,
    KEY idx_created_at (created_at),
    PRIMARY KEY (id)
)engine=innodb DEFAULT charset=utf8;


CREATE TABLE IF NOT EXISTS comments(
    id VARCHAR(50) NOT NULL,
    blog_id VARCHAR(50) NOT NULL,
    user_id VARCHAR(50) NOT NULL,
    user_name VARCHAR(50) NOT NULL,
    user_image VARCHAR(500) NOT NULL,
    content MEDIUMTEXT NOT NULL,
    created_at REAL NOT NULL,
    KEY idx_created_at (created_at),
    PRIMARY KEY (id)
)engine=innodb DEFAULT charset=utf8;
