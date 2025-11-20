# VTB Finance Tracker

VTB Finance Tracker is a Django web application for managing personal finances with support for accounts, cards, transactions, budgets, analytics, and dashboard widgets.

## Requirements
- Python 3.10 or newer (tested with 3.11)
- SQLite (bundled with Python) for local development
- Node is **not** required; the UI is rendered with Django templates

## Project Setup
1. Clone the repository and move into the project directory:
   ```bash
   git clone <repo-url>
   cd vtb-finance-tracker1
   ```
2. Create and activate a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\\Scripts\\activate
   ```
3. Install dependencies from the pinned requirements file:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure environment variables by copying the example file and adjusting values as needed:
   ```bash
   cp .env.example .env
   ```
   - `SECRET_KEY` – Django secret key for the instance
   - `DEBUG` – set to `True` for local development
   - `ALLOWED_HOSTS` – comma-separated hostnames that can serve the app
   - `CORS_ALLOWED_ORIGINS` – comma-separated origins allowed for cross-origin requests

## Database and Migrations
Apply migrations to create the local SQLite database:
```bash
python manage.py migrate
```

If you need to reset the database for a clean start, you can remove `db.sqlite3` and re-run migrations. A helper script `reset_db.py` is also available if you want to automate cleanup.

## Running the Application
Start the development server:
```bash
python manage.py runserver
```

Access the site at http://127.0.0.1:8000/.

## Creating a Superuser
To access the Django admin or log in with credentials, create a superuser:
```bash
python manage.py createsuperuser
```
Follow the prompts to set a username and password. You can then log in at `/admin/`.

If you prefer to start with ready-made demo data, use the provided fixture (see below) and log in with:

- **Username:** `admin`
- **Password:** `admin123`

## Tests and Checks
Run Django system checks:
```bash
python manage.py check
```
Run the test suite:
```bash
python manage.py test
```

## Project Structure
- `accounts/` – custom user model and authentication views
- `analytics/` – budgeting and analytics logic
- `cards/` – card management
- `dashboard/` – dashboard widgets and views
- `transactions/` – transaction CRUD, categories, and related templates
- `templates/` – Django templates used across the project
- `static/` – static assets for development (collected into `staticfiles/` when needed)
- `vtb_tracker/` – core Django project settings and URL configuration

## Dependencies
All Python dependencies are pinned in `requirements.txt` for reproducible installs.

## Environment Template
A starter configuration is provided in `.env.example` (no secrets included). Copy it to `.env` and adjust values for your environment.

## Fixtures and Sample Data
Demo data is available for quick onboarding:

1. Apply migrations (if you haven’t already):
   ```bash
   python manage.py migrate
   ```
2. Load the sample dataset:
   ```bash
   python manage.py loaddata fixtures/sample_data.json
   ```

The fixture creates an admin user (`admin` / `admin123`), a couple of categories, example transactions, a budget entry, and a sample card linked to the admin account.

## Licensing
A license file is not included. Add one if you plan to distribute the project publicly.