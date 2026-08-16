# Travel Booking API

FastAPI backend using SQLAlchemy 2, Alembic, MySQL, and PyMySQL.

## Setup

Run these commands from this `backend` directory in Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env # only when .env does not already exist
```

Update `DATABASE_URL` and `SECRET_KEY` in `.env`, then start the API:

```powershell
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Useful URLs:

- API documentation: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- Database health: <http://127.0.0.1:8000/api/v1/health>

## Migrations

With the MySQL database running and `.env` configured:

```powershell
.\venv\Scripts\python.exe -m alembic upgrade head
.\venv\Scripts\python.exe -m alembic revision --autogenerate -m "describe change"
```

## Verification

```powershell
.\venv\Scripts\python.exe -m compileall -q app migrations
```

Automated tests have not been added yet; this is tracked in the repository roadmap.
