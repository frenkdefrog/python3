#!/bin/bash

mysql -u root -p"$MYSQL_ROOT_PASSWORD" <<-EOSQL
	USE email_tracker;

    CREATE USER IF NOT EXISTS '$MYSQL_USER'@'%' IDENTIFIED WITH mysql_native_password BY '$MYSQL_PASSWORD';

	GRANT ALL PRIVILEGES ON $MYSQL_DATABASE.* TO '$MYSQL_USER'@'%';

	FLUSH PRIVILEGES;

    CREATE TABLE user_emails (
        email VARCHAR(255) PRIMARY KEY,
        last_check TIMESTAMP,
        emails_sent_last_minute INT,
        total_emails_sent INT,
        note_to_admin_sent datetime
    );

    CREATE TABLE whitelist(
		email VARCHAR(255) PRIMARY KEY
    ); 
EOSQL
