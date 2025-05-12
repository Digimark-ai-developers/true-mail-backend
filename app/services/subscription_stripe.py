from datetime import datetime, timedelta, timezone
import json
import stripe
from sqlalchemy.orm import Session
from app.models.subscriptions_stripe import Invoices
from app.models.user import User
from app.models.credits import Credit, CreditHistory
from dotenv import load_dotenv
import random


load_dotenv()

# stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
# endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
# YOUR_DOMAIN = os.getenv("FRONTEND_DOMAIN")

stripe.api_key = "sk_test_51PY76e2MGeqNp340z0BavRh70aMrc5NqSmof5lIAXPzSfgpPBWOUg5YQo8ICUmHyXZhmFDogyklDoG90gmuEFcw400JIZnaQiI"
endpoint_secret = "whsec_282f3a4ad56bc05adbeaa907b181be408135945a8f6c3286a7b75fc9c2bf677f"
YOUR_DOMAIN = "http://127.0.0.1:8000"


def create_checkout_session(email: str, card_title: str, card_price: int, user_id: str):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            billing_address_collection="auto",
            customer_email=email,
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": card_title,
                            "description": "Access to selected plan",
                        },
                        "unit_amount": card_price,
                    },
                    "quantity": 1,
                }
            ],
            success_url=f"{YOUR_DOMAIN}/docs",
            cancel_url=f"{YOUR_DOMAIN}",
            metadata={
                "user_id": user_id  # Adding user_id as metadata
            },

        )
        print("session", session)
        return session.url
    except Exception as e:
        raise Exception(f"Stripe error: {str(e)}")


def handle_webhook(payload: bytes, sig_header: str, db: Session):
    print("Creating checkout session...")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except stripe.error.SignatureVerificationError:
        print("Invalid signature.")
        raise ValueError("Invalid signature")

    try:
        event_data = json.loads(payload.decode("utf-8"))
        print("Raw JSON from StripeXXX:", json.dumps(event_data, indent=2))
    except Exception as e:
        print("Failed to parse raw payload:", str(e))

    try:
        event_type = event["type"]
        data_object = event["data"]["object"]
        print("Event type:", event_type)

        user_id = data_object.get("metadata", {}).get("user_id")
        print("User ID from metadata:", user_id)

        if event_type == "checkout.session.completed":
            email = data_object.get("customer_email")
            amount_total = data_object.get("amount_total")

            existing_credit = db.query(Credit).filter_by(user_id=user_id).first()
            number = random.randint(1000000, 9999999)  # 7-digit number
            new_credit = Credit(
                user_id=user_id,
                is_paid=True,
                total_credits=(existing_credit.total_credits if existing_credit else 0) + amount_total,
                remaining_credits=amount_total,
                created_at=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=730),
            )

            new_credit_history = CreditHistory(
                user_id=user_id,
                credits_purchased=666,
                amount=amount_total,
                purchased_at=datetime.now(timezone.utc),
            )
            new_invoice = Invoices(
                user_id=user_id,
                amount=amount_total,
                number=number,
                status="paid",
                created_at=datetime.now(timezone.utc),
            )
            db.add(new_credit)
            db.add(new_credit_history)
            db.add(new_invoice)

            db.commit()

        elif event_type == "invoice.payment_failed":
            email = data_object.get("customer_email")
            user = db.query(User).filter_by(email=email).first()
            if user:
                user.status = "payment_failed"
                db.commit()

        return {"success": True}

    except Exception as e:
        print("Stripe error occurred:", str(e))
        raise Exception(f"Stripe error: {str(e)}")
