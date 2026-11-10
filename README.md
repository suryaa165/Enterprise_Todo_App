# Todo Application

React + FastAPI + MySQL starter with admin/customer roles, personal routines, daily completion and 30-day progress history.

## 1. Run locally without Docker

### MySQL
Create a MySQL database and user, then configure `backend/.env` using `.env.example`.

### Backend (Python 3.11/3.12 recommended)
```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env
python -m app.seed
uvicorn app.main:app --reload
```
Backend: http://localhost:8000  
Swagger: http://localhost:8000/docs

### Frontend
```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```
Frontend: http://localhost:5173

Admin login (change this password immediately): `admin@todo.local` / `Admin123!ChangeMe`.
Customers register through the UI.

## 2. Run the whole stack with Docker Compose
From repository root:
```bash
docker compose up --build
```
Open http://localhost:5173. Seed admin after first start:
```bash
docker compose exec backend python -m app.seed
```
Stop: `docker compose down`; preserve DB volume. To delete local DB data: `docker compose down -v`.

## 3. Important implementation notes
- Customers can only read/update their own routines and daily entries; admin endpoints require the admin role.
- Admin account is seeded for local development. Do not expose the sample credentials in production.
- Daily entries are generated when a customer opens a date. History API returns up to 30 calendar days.
- This starter uses SQLAlchemy `create_all` for local bootstrap. Add Alembic migrations before production.
- Configure HTTPS, secure secrets, database backups, rate limiting, password reset, audit logs, and stronger session/token handling before production.
- Frontend dev server is used in the starter Dockerfile. For production, build static assets and serve via Nginx or S3/CloudFront.

## 4. API overview
- `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- `GET /api/tasks`; admin: `POST/PATCH/DELETE /api/admin/tasks`
- `GET/POST /api/routines`; `PATCH/DELETE /api/routines/{id}`
- `GET /api/daily?day=YYYY-MM-DD`; `PATCH /api/daily/{entry_id}`
- `GET /api/history?days=30`
- Admin: `GET /api/admin/users`, `GET /api/admin/users/{user_id}/history`

## 5. AWS deployment direction
Use ECR for images and EKS for Kubernetes. Provision MySQL using Amazon RDS for MySQL (recommended) rather than running a production database in the cluster. Use AWS Load Balancer Controller for ingress and ACM for TLS. GitHub Actions should build/test images, push to ECR, then update EKS deployments. See deployment/README.md.
