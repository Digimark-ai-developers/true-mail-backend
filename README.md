# True Mail API

A FastAPI backend for email verification, user management, and Stripe-based subscription services. This project provides endpoints for user authentication, email validation (single and bulk), profile management, and payment processing.

## Features

- **User Authentication**: Register, verify email, login, password reset, and profile management.
- **Email Validation**: Validate single or multiple emails, check validation status, and download results.
- **Stripe Integration**: Purchase credits, manage subscriptions, and view invoices.
- **Admin/User Credits**: Assign and track credits for email validation.
- **CORS Support**: Configurable for frontend integration.

## Tech Stack

- Python 3.10+
- FastAPI
- SQLAlchemy
- Alembic (migrations)
- SQLite (default, configurable)
- Stripe API
- JWT Authentication
- Vercel (optional deployment)

## Project Structure

```text
true-mail-backend/
├── alembic/                # Database migrations (Alembic)
│   ├── env.py
│   ├── versions/
│   └── ...
├── app/                    # Main application code
│   ├── core/               # Core config and security
│   ├── db/                 # Database session and init
│   ├── dependencies/       # Dependency overrides (e.g., auth)
│   ├── models/             # SQLAlchemy models
│   ├── routes/             # API route definitions
│   ├── schemas/            # Pydantic schemas
│   ├── services/           # Business logic/services
│   ├── utils/              # Utility functions (mailer, cache, etc.)
│   └── main.py             # FastAPI app entry point
├── requirements.txt        # Python dependencies
├── alembic.ini             # Alembic config
├── vercel.json             # Vercel deployment config
├── .example.env            # Example environment variables
└── README.md               # Project documentation
```

- **alembic/**: Handles database migrations.
- **app/**: Main backend code, organized by feature and responsibility.
- **requirements.txt**: Lists all Python dependencies.
- **alembic.ini**: Alembic migration configuration.
- **vercel.json**: Configuration for Vercel deployment.
- **.example.env**: Template for required environment variables.
- **README.md**: Project documentation (this file).

## Getting Started

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd true-mail-backend
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.example.env` to `.env` and fill in your secrets:

```bash
cp .example.env .env
```

Edit `.env`:

```
DATABASE_URL=sqlite:///./truemail.db  # Or your DB URL
JWT_SECRET=your-secret-key
FIREBASE_API_KEY=your-firebase-key
STRIPE_SECRET_KEY=your-stripe-secret
STRIPE_WEBHOOK_SECRET=your-stripe-webhook-secret
FRONTEND_DOMAIN=https://your-frontend-domain.com
```

### 5. Run database migrations

```bash
alembic upgrade head
```

### 6. Start the development server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## API Overview

- `POST /auth/register` — Register a new user
- `GET /auth/verify-email/{token}` — Verify user email
- `POST /auth/login` — Login and receive JWT tokens
- `POST /auth/refresh` — Refresh JWT tokens
- `PUT /auth/forgot-password` — Request password reset (OTP)
- `POST /auth/change_password` — Change password
- `POST /auth/verify-otp` — Verify OTP for password reset
- `GET /user/me` — Get current user profile
- `PUT /user/update-profile` — Update user profile
- `POST /validation/single_email` — Validate a single email
- `POST /validation/validate_copy_pasted_emails` — Bulk email validation
- `GET /validation/all_validated_emails` — List all validated emails
- `POST /stripe/create_checkout_session` — Create Stripe checkout session
- `GET /stripe/invoices` — List user invoices

See the FastAPI docs at `/docs` for full API details.

## Deployment

### Deploy on Vercel

- The project includes a `vercel.json` for deployment on Vercel using Python 3.10.
- Ensure your environment variables are set in the Vercel dashboard.
- The entry point is `app/main.py`.

### Manual Deployment

- Deploy as a standard FastAPI app (e.g., with Uvicorn, Gunicorn, or Docker).

## Database Migrations

- Alembic is used for migrations. Update models, then run:

```bash
alembic revision --autogenerate -m "Your message"
alembic upgrade head
```

## Environment Variables

See `.example.env` for all required variables:

- `DATABASE_URL`
- `JWT_SECRET`
- `FIREBASE_API_KEY`
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `FRONTEND_DOMAIN`

## License

MIT License. See `LICENSE` file if present.

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.
