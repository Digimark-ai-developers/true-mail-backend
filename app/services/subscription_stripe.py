import stripe
from sqlalchemy.orm import Session
from app.models.user import User
from dotenv import load_dotenv

load_dotenv()

# stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
# endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
# YOUR_DOMAIN = os.getenv("FRONTEND_DOMAIN")

stripe.api_key = "sk_test_51PdOZdJlFVBgWA13eLwspmL3qoiV1rafbnoh4rO4oHGUqP9cI00B7A94iemLebwi6AKReeSwEMm2G9yZPk3ivNZY00qpHRQLd9"
endpoint_secret = (
    "whsec_97c86c0438680c2a895e97f922deb77d21f5a3140838ce1c02f95ae9fc0fa944"
)
YOUR_DOMAIN = "http://127.0.0.1:8002"


def create_checkout_session(email: str, card_title: str, card_price: int):
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
            cancel_url=f"{YOUR_DOMAIN}/docs",
        )
        return session.url
    except Exception as e:
        raise Exception(f"Stripe error: {str(e)}")


def handle_webhook(payload: bytes, sig_header: str, db: Session):
    print("Creating checkout session...")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except stripe.error.SignatureVerificationError:
        raise ValueError("Invalid signature")
    print("Received event: ", event)
    event_type = event["type"]
    data_object = event["data"]["object"]
    print("debugging 1", data_object)

    if event_type == "checkout.session.completed":
        email = data_object.get("customer_email")
        subscription_id = data_object.get("subscription")
        amount_total = data_object.get("amount_total")

        print("debugging 2", email, subscription_id, amount_total)

    elif event_type == "invoice.payment_failed":
        email = data_object.get("customer_email")
        user = db.query(User).filter_by(email=email).first()
        if user:
            user.status = "payment_failed"
            db.commit()

    return {"success": True}
