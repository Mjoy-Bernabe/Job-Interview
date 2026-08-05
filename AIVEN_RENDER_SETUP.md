# Aiven MySQL + MySQL Workbench + Render

## Architecture

- Aiven hosts the MySQL server.
- MySQL Workbench connects to Aiven and manages the `auth_db` schema.
- Render runs the Flask MVC application and connects to the same Aiven server.

## 1. Verify the database in MySQL Workbench

Connect using the values from **Aiven > Overview > Connection information**:

- Connection method: Standard TCP/IP
- Hostname: your Aiven hostname
- Port: your Aiven port (not automatically 3306)
- Username: `avnadmin`
- Password: the current Aiven password
- SSL Mode: Require

Run:

```sql
USE auth_db;
SHOW TABLES;
DESCRIBE users;
SELECT user_id, email, user_type FROM users LIMIT 10;
```

The `users` table must include `user_id`, `email`, `password_hash`, and
`user_type`.

## 2. Render environment variables

Remove old Railway variables such as `MYSQL_PUBLIC_URL`, `DATABASE_URL`, and
`MYSQL_URL`, or leave them unused. This project now gives explicit `MYSQL_*`
variables priority.

Set:

```text
MYSQL_HOST=<Aiven hostname>
MYSQL_PORT=<Aiven port>
MYSQL_USER=avnadmin
MYSQL_PASSWORD=<current Aiven password>
MYSQL_DB=auth_db
MYSQL_SSL_MODE=REQUIRED
MYSQL_CONNECT_TIMEOUT=20
SECRET_KEY=<long random value>
MAX_RESUME_SIZE=10485760
```

Do not add quotation marks around the values. Do not use `localhost`,
`127.0.0.1`, or `mysql.railway.internal` on Render.

## 3. Render commands

Build command:

```text
pip install -r requirements.txt
```

Start command:

```text
gunicorn run:app --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 180
```

Health check path:

```text
/health
```

After deploying, visit:

```text
https://YOUR-SERVICE.onrender.com/health/db
```

A correct setup reports `status: ok`, `database: auth_db`,
`users_table_exists: true`, and no missing login columns.
