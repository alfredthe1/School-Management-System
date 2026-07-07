# Happy Child Nursery and Primary School

A Django school management system for Happy Child Nursery and Primary School (Uganda). It covers student records, academics, examinations, fees, mobile money payments, parent portal, staff payroll, and role-based portal permissions.

## Features

| Area | Capabilities |
|------|--------------|
| **Students** | Enrollment, profiles, class assignment, document uploads |
| **Academics** | Classes, subjects, timetables, teacher assignments |
| **Examinations** | Exam setup, subject-scoped mark entry, teacher marks hub |
| **Fees** | Fee structures (admin-only), payments, balances, bursar tools |
| **Parents** | Pay fees (MTN/Airtel mobile money), payment history, child progress |
| **Staff** | Staff records, payroll runs |
| **Admin** | Per-user portal permissions, payment gateway config, reports |
| **Security** | CSRF hardening, callback verification, activity logging |

## User roles

| Role | Typical access |
|------|----------------|
| **Admin** | Full system access, fee structure CRUD, user permissions |
| **Head Teacher** | Academic oversight, reports, most modules |
| **Teacher** | Assigned subjects, mark entry, communication |
| **Bursar** | Fees (view structures), payments, payroll view |
| **Parent** | Pay fees, view children, progress (results gated by fee balance) |

## Quick start (development)

### Prerequisites

- Python 3.10+
- Windows PowerShell (scripts provided) or any shell

### 1. Clone and set up the virtual environment

```powershell
cd happy_child_school
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
```

### 2. Environment file

```powershell
copy .env.example .env
```

Defaults work for local development (`DJANGO_ENV=development`, SQLite).

### 3. Database and demo data

```powershell
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py populate_demo_data
```

### 4. Run the server

```powershell
.\scripts\run-dev.ps1
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000)

### Demo logins

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Admin |
| `teacher1` | `teacher123` | Teacher |
| `parent1` | `parent123` | Parent |
| `bursar` | `bursar123` | Bursar |

## Mobile testing

Test the parent payment flow on your phone:

| Method | Command | Notes |
|--------|---------|-------|
| **Same Wi-Fi (LAN)** | `.\scripts\start-lan.ps1` | Starts Django on `0.0.0.0:8000`; open `http://<your-pc-ip>:8000` |
| **ngrok tunnel** | Start Django first, then `.\scripts\start-ngrok.ps1` | Requires [ngrok](https://ngrok.com/) authtoken |

## Project structure

```
happy_child_school/
├── accounts/          # Users, roles, portal permissions
├── academics/         # Classes, subjects, timetables
├── announcements/     # School announcements
├── communication/     # Messaging, notifications
├── core/              # Dashboard, school settings, demo data command
├── examinations/      # Exams, marks, teacher marks hub
├── fees/              # Fee structures, payments, mobile money
├── logs/              # User activity logging
├── parents/           # Parent portal, mobile money callbacks
├── reports/           # Report cards, data import/export
├── staff/             # Staff records and payroll
├── students/          # Student records
├── teachers/          # Teacher profiles and assignments
├── school/            # Project config (settings, URLs, middleware, security)
│   └── settings/
│       ├── base.py        # Shared settings
│       ├── development.py # SQLite, DEBUG, ngrok/LAN helpers
│       └── production.py  # PostgreSQL, WhiteNoise, HTTPS
├── templates/         # HTML templates
├── static/            # CSS, JS, images
├── scripts/           # Dev and deploy helper scripts
├── deploy/            # Gunicorn configuration
├── docs/              # Architecture and deployment guides
├── requirements/      # base.txt + production.txt
├── docker-compose.yml # PostgreSQL + Redis for production-like dev
├── manage.py
└── .env.example
```

## Configuration

Settings are split by environment. Set `DJANGO_ENV` in `.env`:

| Value | Use case |
|-------|----------|
| `development` (default) | Local dev — SQLite, DEBUG, ngrok/LAN CSRF helpers |
| `production` | Live server — PostgreSQL, WhiteNoise, strict secrets |

Key environment variables are documented in [`.env.example`](.env.example).

## Production deployment

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for the full checklist. Summary:

```powershell
pip install -r requirements/production.txt
copy .env.example .env   # set DJANGO_ENV=production and strong secrets
docker compose up -d     # optional: local PostgreSQL + Redis
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py collectstatic --noinput
.\scripts\check-production.ps1
gunicorn -c deploy/gunicorn.conf.py school.wsgi:application
```

Place nginx (or similar) in front of Gunicorn for HTTPS and to serve uploaded media files.

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for app responsibilities, data flows, and security model.

## Common management commands

```powershell
.\venv\Scripts\python.exe manage.py migrate
.\venv\Scripts\python.exe manage.py populate_demo_data
.\venv\Scripts\python.exe manage.py createsuperuser
.\venv\Scripts\python.exe manage.py check --deploy   # with DJANGO_ENV=production
```

## License

Private — Happy Child Nursery and Primary School."# School-Management-System" 
