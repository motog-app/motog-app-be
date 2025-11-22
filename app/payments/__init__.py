from .base import PaymentDriver
from .razorpay import RazorpayDriver

def get_payment_driver(driver_name: str) -> PaymentDriver:
    if driver_name == "razorpay":
        return RazorpayDriver()
    # Add more drivers here as needed
    raise ValueError(f"Unknown payment driver: {driver_name}")
