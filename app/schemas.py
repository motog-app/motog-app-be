# app/schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime
from .models import VehicleTypeEnum  # Import from your models
from fastapi import UploadFile, File

# --- User Schemas ---


class UserBase(BaseModel):
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=8)


class User(UserBase):
    id: int
    is_active: bool
    is_email_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic V2 (was orm_mode = True in V1)

# --- Token Schemas (for JWT) ---


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class LoginResponse(Token):
    user: User


class ListingImageCreate(BaseModel):
    url: str
    is_primary: bool = False


class ListingImage(BaseModel):
    id: int
    url: str
    is_primary: bool = False

    class Config:
        from_attributes = True

# --- Vehicle Listing Schemas ---


class VehicleListingBase(BaseModel):
    vehicle_type: VehicleTypeEnum
    reg_no: str = Field(..., min_length=7, max_length=10)
    kilometers_driven: int = Field(..., ge=0)
    price: int = Field(..., gt=0)
    usr_inp_city: str = Field(..., min_length=2)
    city: str = Field(..., min_length=2)
    seller_phone: str = Field(..., min_length=10, max_length=15)
    description: Optional[str] = None


class VehicleListingCreate(BaseModel):
    vehicle_type: VehicleTypeEnum
    reg_no: str = Field(..., example="HJ01ME5678", min_length=7, max_length=10)
    kilometers_driven: int = Field(..., ge=0)
    price: int = Field(..., gt=0)
    city: str = Field(..., min_length=2)
    seller_phone: str = Field(..., min_length=10, max_length=15)
    description: Optional[str] = None


class VehicleListingUpdate(BaseModel):
    kilometers_driven: Optional[int] = Field(None, ge=0)
    price: Optional[int] = Field(None, gt=0)
    city: Optional[str] = Field(None, min_length=2)
    seller_phone: Optional[str] = Field(None, min_length=10, max_length=15)
    description: Optional[str] = Field(None, min_length=1, max_length=250)


class VehicleListing(VehicleListingBase):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    owner_email: Optional[EmailStr] = None
    rc_details: Optional[Any] = None
    images: List[ListingImage] = []

    class Config:
        from_attributes = True


class RCRequest(BaseModel):
    reg_no: str


class VehicleVerificationResponse(BaseModel):
    reg_no: str
    status: str
    data: dict


class LocationFrmLatLngRequest(BaseModel):
    lat: str = Field(..., example="24.5164769",
                     description="Latitute of the Location")
    lng: str = Field(..., example="93.9582257",
                     description="Longitude of the Location")


class LocationFrmLatLngResponse(BaseModel):
    mainText: str = Field(...,
                          description="The main address text or Place name")
    State: str = Field(..., description="State name")
    Country: str = Field(..., description="Country name")


class LocAutoCompleteRequest(BaseModel):
    addrStr: str = Field(..., example="Imp",
                         description="Part or full address input from user.")
    sessionToken: Optional[str] = Field(
        None,
        example="a7e60d8a-528d-476c-b9f3-7f3b07ba912a",
        description="UUID to group autocomplete requests (valid for ~3 minutes)."
    )
    latLng: Optional[str] = Field(
        None,
        example="28.5079920,77.2025578",
        description="Latitude,Longitude to bias results geographically."
    )


class LocationSuggestion(BaseModel):
    placeId: str = Field(..., description="Unique identifier of the place")
    mainText: str = Field(...,
                          description="Main display text for the prediction")
    secondaryText: str = Field(...,
                               description="Additional context for the prediction")


class LocAutoCompleteResponse(BaseModel):
    suggestions: List[LocationSuggestion]


class ResendEmailRequest(BaseModel):
    email: EmailStr


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)
