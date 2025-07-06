from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app import schemas, models, crud
from app.database import get_db
from app.dependencies import get_current_user
from app.core.config import settings
import requests
import uuid

router = APIRouter()


@router.post("/vehicle-verify", response_model=schemas.VehicleVerificationResponse)
def verify_vehicle_rc(request: schemas.RCRequest, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Check if already in DB
    request.reg_no = request.reg_no.upper()
    existing = crud.get_verification_by_reg_no(db, request.reg_no)
    if existing:
        return schemas.VehicleVerificationResponse(
            reg_no=existing.reg_no,
            status=existing.status,
            data=existing.raw_data
        )

    # Prepare for Cashfree API Call
    headers = {
        "x-client-id": settings.CASHFREE_CLIENT_ID,
        "x-client-secret": settings.CASHFREE_CLIENT_SECRET,
        "Content-Type": "application/json"
    }

    payload = {
        "verification_id": str(uuid.uuid4()),
        "vehicle_number": str(request.reg_no)
    }

    try:
        response = requests.post(
            settings.CASHFREE_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        api_data = response.json()
    # except Exception as e:
    #     raise HTTPException(
    #         status_code=502, detail=f"Failed to fetch data from Cashfree: {str(e)}")
    except requests.exceptions.HTTPError as http_err:
        try:
            # Try to parse Cashfree error message from JSON
            error_json = response.json()
            raise HTTPException(
                status_code=response.status_code,
                detail={
                    "code": error_json.get("code"),
                    "message": error_json.get("message"),
                    "type": error_json.get("type"),
                    "ip_hint": error_json.get("message", "").split("Your current IP is")[-1].strip() if "ip" in error_json.get("message", "") else None
                }
            )
        except Exception:
            # Fallback if response is not JSON
            raise HTTPException(
                status_code=502, detail=f"Cashfree error: {response.text}")
        except Exception as e:
            raise HTTPException(
                status_code=502, detail=f"Unexpected error: {str(e)}")

    # Save to DB
    new_verification = crud.create_verification(
        db=db,
        reg_no=request.reg_no,
        status=api_data.get("status", "UNK"),
        raw_data=api_data
    )

    return schemas.VehicleVerificationResponse(
        reg_no=new_verification.reg_no,
        status=new_verification.status,
        data=new_verification.raw_data
    )
