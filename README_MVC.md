# Job Interview Platform — MVC Structure

This version reorganizes the Flask application into the Model–View–Controller pattern.

## MVC mapping

- **Model — `app/models/`**  
  Contains domain entities and repository classes responsible for database access.
- **View — `app/views/templates/` and `app/static/`**  
  Contains Jinja HTML templates, CSS, JavaScript, images, and other visible UI assets.
- **Controller — `app/controllers/`**  
  Contains Flask Blueprints, URL routes, request validation, session checks, redirects,
  and coordination between the model/services and the views.
- **Services — `app/services/`**  
  Contains reusable business and technical logic such as scoring, email, OTP,
  resume scanning, status synchronization, and PDF generation.

## Main structure

```text
Simulation_MVC/
├── app/
│   ├── __init__.py              # Application factory
│   ├── config.py
│   ├── extensions.py
│   ├── session_utils.py
│   ├── models/
│   │   ├── entities.py
│   │   └── repositories.py
│   ├── controllers/
│   │   ├── auth.py
│   │   ├── applicants.py
│   │   ├── hr.py
│   │   ├── admin.py
│   │   ├── interview.py
│   │   ├── schedule.py
│   │   └── summary.py
│   ├── views/templates/
│   ├── static/
│   └── services/
├── run.py
├── requirements.txt
└── schema.sql
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Import `schema.sql` into MySQL.
4. Configure environment variables when necessary:
   - `SECRET_KEY`
   - `MYSQL_HOST`
   - `MYSQL_USER`
   - `MYSQL_PASSWORD`
   - `MYSQL_DB`
   - `MAIL_USERNAME`
   - `MAIL_PASSWORD`
5. Start the application:
   ```bash
   python run.py
   ```

## Controller flow

```text
Browser request
      ↓
Controller / Blueprint
      ↓
Model repository + Service
      ↓
Database / business processing
      ↓
Controller
      ↓
View template or JSON response
```

New database queries should be placed in repository classes under `app/models/`.
Controllers should primarily validate requests, call models/services, and select the
view or response.

## Render deployment

Use these Render settings:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn run:app --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 180`
- Health check path: `/health`
- Recommended Python version: `3.12.7`

Required environment variables normally include `SECRET_KEY`, MySQL connection values, and mail credentials. `MAX_RESUME_SIZE` must be a plain integer in bytes, such as `10485760` for 10 MB.

The SentenceTransformer and KeyBERT models are lazy-loaded. Render can therefore open its web port before the large NLP model is downloaded and initialized.

## Connect to a local MySQL Server through MySQL Workbench

MySQL Workbench is the interface used to manage the MySQL Server. The Flask application connects to the same MySQL Server using the credentials in `.env`.

1. In MySQL Workbench, connect to your local server, normally `127.0.0.1:3306`.
2. Create the schema `auth_db` if it does not exist.
3. Open **Server > Data Import**, select `database/auth_db.sql`, choose `auth_db`, and start the import.
4. Copy `.env.example` to a new file named `.env`.
5. Enter the same username and password used by your MySQL Workbench connection.
6. Install dependencies and test the connection:

```powershell
pip install -r requirements.txt
python test_database.py
python run.py
```

Default local settings:

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DB=auth_db
```

If the MySQL `root` account has a password, place it after `MYSQL_PASSWORD=`. Do not commit `.env` to GitHub.

A local Workbench/MySQL connection works only while running the Flask app on the same computer. A Render deployment still requires a publicly reachable hosted MySQL server; Render cannot connect to your laptop's `127.0.0.1` database.

## Railway MySQL from Render

The application now accepts Railway's public connection in any of these forms, in priority order:

1. `MYSQL_PUBLIC_URL=mysql://user:password@public-host:public-port/database`
2. `DATABASE_URL=mysql://user:password@public-host:public-port/database`
3. Railway public proxy variables: `RAILWAY_TCP_PROXY_DOMAIN`, `RAILWAY_TCP_PROXY_PORT`, `MYSQLUSER`, `MYSQLPASSWORD`, and `MYSQLDATABASE`
4. Standard variables: `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DB`

For Render, the simplest setup is to create one environment variable named `MYSQL_PUBLIC_URL` and paste Railway's fully resolved public URL. Do not paste a value that still contains `${...}` placeholders, and do not use `mysql.railway.internal` from Render.

After deployment, open `/health/db`. A successful response reports `status: ok` and the connected database name. The response never exposes the database password.
