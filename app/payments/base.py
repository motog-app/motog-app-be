from abc import ABC, abstractmethod

class PaymentDriver(ABC):
    @abstractmethod
    async def create_order(self, amount: float, currency: str, receipt: str, notes: dict = None) -> dict:
        pass

    @abstractmethod
    async def verify_payment(self, payment_id: str, order_id: str, signature: str) -> bool:
        pass

    @abstractmethod
    async def refund_payment(self, payment_id: str, amount: float = None) -> dict:
        pass
