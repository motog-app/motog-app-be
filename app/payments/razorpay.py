import razorpay
from app.payments.base import PaymentDriver
from app.core.config import settings

class RazorpayDriver(PaymentDriver):
    def __init__(self):
        self.client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET.get_secret_value()
            )
        )
        self.client.set_app_details({"title": "MotoG App", "version": "1.0"})

    async def create_order(self, amount: float, currency: str, receipt: str, notes: dict = None) -> dict:
        data = {
            "amount": int(amount * 100),  # Razorpay expects amount in paisa
            "currency": currency,
            "receipt": receipt,
            "notes": notes if notes else {}
        }
        order = self.client.order.create(data=data)
        return order

    async def verify_payment(self, payment_id: str, order_id: str, signature: str) -> bool:
        try:
            self.client.utility.verify_payment_signature({
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            })
            return True
        except Exception:
            return False

    async def refund_payment(self, payment_id: str, amount: float = None) -> dict:
        data = {}
        if amount:
            data["amount"] = int(amount * 100)
        refund = self.client.payment.refund(payment_id, data)
        return refund
