from app.models.credits import Credit, CreditHistory, CreditUsage
from sqlalchemy.orm import Session


class CreditService:
    def __init__(self, db: Session):
        self.db = db

    def fetch_credit_balance(self, user_id: str) -> int:
        credit = self.db.query(Credit.remaining_credits).filter(Credit.user_id == user_id).first()
        return credit.remaining_credits if credit else 0

    def fetch_credit_usage(self, user_id: str):
        return self.db.query(CreditUsage).filter(CreditUsage.user_id == user_id).all()

    def fetch_credit_history(self, user_id: str):
        return self.db.query(CreditHistory).filter(CreditHistory.user_id == user_id).all()
