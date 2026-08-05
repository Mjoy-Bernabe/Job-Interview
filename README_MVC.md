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
