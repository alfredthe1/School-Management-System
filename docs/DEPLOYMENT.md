# Deployment Guide

This document covers deploying Happy Child School to a production Linux server (Ubuntu-style). Adapt paths and service names for your hosting provider.

## Pre-deployment checklist

- [ ] Strong `DJANGO_SECRET_KEY` (50+ random characters)
- [ ] `DJANGO_ENV=production`
- [ ] `DJANGO_ALLOWED_HOSTS` includes your domain(s)
- [ ] `DJANGO_CSRF_TRUSTED_ORIGINS` includes `https://yourdomain.com`
- [ ] PostgreSQL database provisioned
- [ ] `MOBILE_MONEY_CALLBACK_SECRET` set if mobile money is enabled
- [ ] HTTPS certificate (Let's Encrypt via certbot)
- [ ] Media upload directory writable and backed up
- [ ] `.env` file **not** committed to git

## 1. Server setup

```bash
sudo apt update && sudo apt install -y python3-venv python3-pip nginx postgresql-client
```

Clone the project and create a virtual environment:

```bash
cd /var/www/happy_child_school
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/production.txt
```

## 2. Environment configuration

```bash
cp .env.example .env
nano .env
```

Minimum production `.env`:

```env
DJANGO_ENV=production
DJANGO_SECRET_KEY=<generate-a-long-random-key>
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

POSTGRES_DB=happy_child_school
POSTGRES_USER=happy_child
POSTGRES_PASSWORD=<strong-password>
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

MOBILE_MONEY_CALLBACK_SECRET=<shared-secret>
MTN_MOMO_CALLBACK_URL=https://yourdomain.com/parents/mobile-money/mtn/callback/
AIRTEL_MONEY_CALLBACK_URL=https://yourdomain.com/parents/mobile-money/airtel/callback/

SECURE_SSL_REDIRECT=True
USE_X_FORWARDED_HOST=True
```

Generate a secret key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

## 3. Database

### Option A: Docker Compose (on the same server)

```bash
docker compose up -d db
```

### Option B: Managed PostgreSQL

Use your provider's connection details in `.env`.

### Migrate

```bash
source venv/bin/activate
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
```

## 4. Validate settings

```bash
DJANGO_ENV=production python manage.py check --deploy
```

Fix any warnings before going live.

## 5. Gunicorn

Test manually:

```bash
source venv/bin/activate
gunicorn -c deploy/gunicorn.conf.py school.wsgi:application
```

### systemd service

Create `/etc/systemd/system/happychild.service`:

```ini
[Unit]
Description=Happy Child School Gunicorn
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/happy_child_school
EnvironmentFile=/var/www/happy_child_school/.env
ExecStart=/var/www/happy_child_school/venv/bin/gunicorn -c deploy/gunicorn.conf.py school.wsgi:application
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable happychild
sudo systemctl start happychild
```

## 6. nginx

Create `/etc/nginx/sites-available/happychild`:

```nginx
upstream happychild_app {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    client_max_body_size 20M;

    location /static/ {
        alias /var/www/happy_child_school/staticfiles/;
        expires 30d;
    }

    location /media/ {
        alias /var/www/happy_child_school/media/;
        expires 7d;
    }

    location / {
        proxy_pass http://happychild_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/happychild /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

> **Media files:** Django does not serve `/media/` in production (`DEBUG=False`). nginx must serve uploaded photos and documents.

## 7. Redis (optional, multi-worker)

If running multiple Gunicorn workers, enable shared cache:

```bash
docker compose up -d redis
```

Add to `.env`:

```env
REDIS_URL=redis://127.0.0.1:6379/0
```

## 8. Mobile money webhooks

Register these callback URLs with MTN MoMo and Airtel Money:

| Provider | URL |
|----------|-----|
| MTN | `https://yourdomain.com/parents/mobile-money/mtn/callback/` |
| Airtel | `https://yourdomain.com/parents/mobile-money/airtel/callback/` |

Callbacks are verified via `MOBILE_MONEY_CALLBACK_SECRET` header and optional IP allowlist.

## 9. Logs and monitoring

Production logs are written to:

```
runtime/logs/django.log
```

Rotate via logrotate or the built-in `RotatingFileHandler` (5 MB × 5 backups).

Monitor Gunicorn:

```bash
sudo journalctl -u happychild -f
```

## 10. Updates

```bash
cd /var/www/happy_child_school
git pull
source venv/bin/activate
pip install -r requirements/production.txt
python manage.py migrate
python manage.py collectstatic --noinput
sudo systemctl restart happychild
```

## Windows development → production

Use `.\scripts\check-production.ps1` locally to validate production settings before deploying. Never use `DJANGO_DEBUG=True` or the dev secret key on a public server.