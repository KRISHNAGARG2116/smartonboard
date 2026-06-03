# Deployment Architecture

## Development

Frontend:
React + Vite

Backend:
FastAPI

Database:
PostgreSQL

Storage:
Local Storage / Object Storage

---

## MVP Deployment

Frontend:
Vercel

Backend:
Render

Database:
Neon PostgreSQL

Storage:
Cloudflare R2

Queue:
Celery + Redis

Email:
Resend

SMS:
Twilio

Billing:
Stripe

---

## Production Deployment

Frontend:
CloudFront + S3

Backend:
AWS ECS Fargate

Database:
Aurora PostgreSQL

Storage:
AWS S3

Queue:
Redis + Celery

Monitoring:
Sentry
Prometheus

Security:
AWS WAF