# StockFlow API

E-commerce and inventory management backend built with FastAPI, PostgreSQL (Supabase), and SQLAlchemy. Businesses manage products, stock, suppliers, and purchase orders. Customers place orders against live inventory.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

## Features

- **Two roles:** `BUSINESS` and `CUSTOMER`, enforced through reusable FastAPI dependencies (`require_business`, `require_customer`)
- **Authentication:** Supabase Auth with JWT verification via JWKS; register, login, refresh, and logout endpoints
- **Catalog:** categories and products with ACTIVE / INACTIVE status
- **Inventory:** per-product stock with manual adjustments (negative stock is rejected)
- **Orders:** customers order multiple items in one request; stock is deducted inside a single transaction using row-level locks (`SELECT ... FOR UPDATE`). Cancelling an order returns stock.
- **Suppliers and purchase orders:** PENDING → ORDERED → RECEIVED / CANCELLED; receiving a purchase order increases stock
- **Ownership checks:** businesses only see and change their own products, suppliers, and purchase orders; customers only see their own orders

## Tech Stack

| Area | Tools |
| --- | --- |
| API | FastAPI, Pydantic v2, Uvicorn |
| Database | PostgreSQL on Supabase, SQLAlchemy 2.0, Alembic |
| Auth | Supabase Auth, python-jose (JWKS verification) |
| Testing | Pytest, HTTPX (130+ tests) |
| Tooling | uv, Docker, Docker Compose |

## Project Structure

```
app/
├── core/          # settings, JWT/JWKS verification, Supabase clients
├── db/            # engine and session
├── dependencies/  # current user and role guards
├── models/        # SQLAlchemy models and enums
├── schemas/       # Pydantic request/response models
├── services/      # business logic
├── routers/       # API endpoints
└── main.py
migrations/        # Alembic migrations
tests/             # Pytest suite
```

## API Overview

| Group | Prefix | Access |
| --- | --- | --- |
| Authentication | `/Auth` | Public (register, login, refresh), authenticated (logout) |
| Users | `/me` | Authenticated |
| Categories | `/categories` | Read: any user. Write: BUSINESS |
| Products | `/products` | Read: any user. Write: BUSINESS (owner) |
| Inventory | `/inventory` | BUSINESS (owner) |
| Suppliers | `/suppliers` | BUSINESS |
| Purchase orders | `/purchase-orders` | BUSINESS |
| Orders | `/orders` | CUSTOMER places and views; BUSINESS updates status |

Full interactive documentation is available at `/docs` (Swagger UI) once the server is running.

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- A Supabase project (database and Auth)

### Setup

```powershell
git clone https://github.com/Moeed009/Stockflow-_api.git
cd Stockflow-_api
uv sync
Copy-Item .env.example .env
```

Fill in `.env`:

| Variable | Description |
| --- | --- |
| `DATABASE_URL` | PostgreSQL connection string |
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key (server only, never expose) |
| `SUPABASE_JWT_SECRET` | Supabase JWT secret |
| `APP_NAME` | Application name shown in Swagger |
| `ENVIRONMENT` | `development` or `production` |

### Run

```powershell
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs.

### Docker

```powershell
docker compose -f app/docker-compose.yml up --build
```

## Running Tests

```powershell
uv run pytest
```

Tests run against an in-memory SQLite database with the Supabase client mocked, so no external services are needed.

## Design Notes

- **Stock consistency:** order creation locks product and inventory rows, validates stock, deducts quantities, and commits as one transaction. Any failure rolls the whole order back.
- **Price snapshots:** each order item stores `unit_price` and `subtotal` at purchase time, so later price changes do not alter past orders.
- **Layering:** routers handle HTTP, services hold business rules, models and schemas stay separate.

## License

Add a license before reuse (for example MIT).
