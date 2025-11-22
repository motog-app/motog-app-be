# app/apis/v1/endpoints/boosts.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import crud, schemas, models
from app.dependencies import get_db, get_current_user

router = APIRouter()

@router.get("/packages", response_model=List[schemas.BoostPackage])
def list_boost_packages(db: Session = Depends(get_db)):
    """
    Get a list of all available boost packages.
    """
    packages = crud.list_boost_packages(db=db)
    return packages

from app.core.config import settings
from app.payments import get_payment_driver


@router.post("/subscribe", response_model=schemas.BoostSubscriptionResponse)
async def subscribe_to_boost(
    boost_in: schemas.BoostSubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Subscribe to a boost package. This will create a Razorpay order and return the
    order details to the client to complete the payment.
    """
    try:
        order = await crud.create_boost_subscription_order(db=db, user_id=current_user.id, boost_in=boost_in)
        
        package = crud.list_boost_packages(db=db, id=boost_in.package_id)

        return schemas.BoostSubscriptionResponse(
            order_id=order['id'],
            razorpay_key_id=settings.RAZORPAY_KEY_ID,
            amount=order['amount'],
            currency=order['currency'],
            name=package.name,
            description=f"Boost package: {package.name}",
            prefill={
                "email": current_user.email,
            }
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        # Generic error for unexpected issues
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")


@router.post("/verify-payment", response_model=schemas.BoostPaymentVerificationResponse)
async def verify_payment(
    verification_data: schemas.BoostPaymentVerification,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Verify the payment and create the user boost.
    """
    payment_driver = get_payment_driver("razorpay")
    is_payment_valid = await payment_driver.verify_payment(
        payment_id=verification_data.razorpay_payment_id,
        order_id=verification_data.razorpay_order_id,
        signature=verification_data.razorpay_signature
    )

    if not is_payment_valid:
        raise HTTPException(status_code=400, detail="Invalid payment signature")

    try:
        user_boost = crud.create_user_boost(
            db=db,
            user_id=current_user.id,
            boost_in=schemas.UserBoostCreate(
                package_id=verification_data.package_id,
                listing_id=verification_data.listing_id
            )
        )
        return {"status": "success", "user_boost": user_boost}
    except HTTPException as e:
        raise e
    except Exception as e:
        # Generic error for unexpected issues
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")

