## Create Virtual Environment

```bash
python3.10 -m venv .venv
```

## Activate Virtual Enviroment

```bash
.venv/Scripts/activate
```

OR in Mac/Linux

```bash
source .venv/bin/activate
```

## Run Command

```bash
uvicorn app.main:app --reload
```

OR run the following to specify port number and to allow all host:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

```

```
true-mail-backend/
├── alembic/                          # Alembic migrations folder
│   └── (versions, env.py, etc.)
├── app/
│   ├── database/
│   │   └── db_config.py              # Database connection and config
│   ├── middlewares/
│   │   └── auth_middleware.py        # Authentication middleware (fixed spelling)
│   ├── models/
│   │   ├── emails.py            # Bulk email-related DB models
│   │   ├── subscriptions_stripe.py   # Stripe subscription models
│   │   └── user.py                   # User models
│   ├── routes/
│   │   ├── email.py                  # e-mail api for check bulk and single
│   │   ├── credit.py                 # credit use , purchase, and history call
│   │   ├── subscription_stripe.py
│   │   ├── auth.py                   # Auth routes (login, signup, etc.)
│   │   └── user.py                   # User management routes
│   ├── schemas/
│   │   ├── email.py                  # email schema
│   │   ├── auth.py                   # Auth-related Pydantic schemas
│   │   ├── otp.py                    # OTP-related schemas
│   │   └── user.py                   # User schemas
│   ├── services/
│   │   ├── auth_services.py          # Authentication services
│   │   ├── subscription_stripe.py    # subscription for stripe
│   │   └── user_services.py          # User services (profile update, etc.)
│   ├── utils/
│   │   ├── email_validator.py        # Email validation utility
│   │   ├── firebase.py               # for firebase auth
│   │   ├── jwt_handler.py
│   │   └── jwt.py
│   └── main.py                       # FastAPI app entry point
├── requirements.txt                  # Project dependencies
├── .env                               # Environment variables
└── README.md
```
