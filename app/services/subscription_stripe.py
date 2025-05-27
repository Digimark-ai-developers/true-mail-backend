from datetime import datetime, timedelta
import uuid
from fastapi import HTTPException
import stripe
from sqlalchemy.orm import Session
from app.models.subscriptions_stripe import Invoices
from app.models.user import User
from app.models.credits import Credit, CreditHistory
from dotenv import load_dotenv

load_dotenv()

# stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
# endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
# YOUR_DOMAIN = os.getenv("FRONTEND_DOMAIN")

stripe.api_key = "sk_test_51PY76e2MGeqNp340z0BavRh70aMrc5NqSmof5lIAXPzSfgpPBWOUg5YQo8ICUmHyXZhmFDogyklDoG90gmuEFcw400JIZnaQiI"
endpoint_secret = "whsec_k05E5GLSADRVJfvI7JdSAg4LtBFGMYyV"
# endpoint_secret = "whsec_282f3a4ad56bc05adbeaa907b181be408135945a8f6c3286a7b75fc9c2bf677f"

YOUR_DOMAIN = "http://127.0.0.1:5173"


class PaymentService:
    def __init__(self, db: Session):
        self.db = db

    def create_checkout_session(self, email: str, success_url: str, card_price: int, credits: int, user_id: str):
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
                            "product_data": {"name": "Credit Purchase", "description": f"{credits} credits package"},
                            "unit_amount": card_price,
                        },
                        "quantity": 1,
                    }
                ],
                success_url=success_url,
                cancel_url=success_url,
                metadata={
                    "user_id": str(user_id),
                    "credits": str(credits),
                },
            )
            return session.url
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

    def handle_webhook(self, payload: bytes, sig_header: str):
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")

        try:
            event_type = event["type"]
            data_object = event["data"]["object"]

            if event_type in ["checkout.session.completed"]:
                self._handle_successful_checkout(data_object)

            elif event_type == "invoice.payment_failed":
                self._handle_payment_failed(data_object)

            return {
                "message": "Stripe webhook processed successfully",
                "status_code": 200,
                "success": True,
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

    def _handle_successful_checkout(self, data_object):
        user_id = data_object.get("metadata", {}).get("user_id")

        credits = int(data_object.get("metadata", {}).get("credits", 0))
        # email = data_object.get("customer_email")
        amount_total = data_object.get("amount_total")

        existing_credit = self.db.query(Credit).filter_by(user_id=user_id).first()
        if not existing_credit:
            raise Exception("Credit record not found for user")

        number = uuid.uuid4().hex[:12]

        existing_credit.is_paid = True
        existing_credit.total_credits += credits
        existing_credit.remaining_credits += credits
        existing_credit.last_updated = datetime.now()
        existing_credit.expires_at = datetime.now() + timedelta(days=730)

        new_credit_history = CreditHistory(
            user_id=user_id,
            credits_purchased=credits,
            amount=amount_total,
            purchased_at=datetime.now(),
        )

        new_invoice = Invoices(
            user_id=user_id,
            amount=amount_total,
            number=number,
            status=True,
            created_at=datetime.now(),
        )

        self.db.add(new_credit_history)
        self.db.add(new_invoice)
        self.db.commit()

    def _handle_payment_failed(self, data_object):
        email = data_object.get("customer_email")
        user = self.db.query(User).filter_by(email=email).first()
        if user:
            user.status = "payment_failed"
            self.db.commit()

    def get_invoices(self, user_id: str):
        invoices = self.db.query(Invoices).filter(Invoices.user_id == user_id).order_by(Invoices.created_at.desc()).all()
        return invoices
