# app/schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any
from datetime import datetime, date
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
    latitude: float
    longitude: float
    seller_phone: str = Field(..., min_length=10, max_length=15)
    description: Optional[str] = None


class VehicleListingCreate(BaseModel):
    vehicle_type: VehicleTypeEnum
    reg_no: str = Field(..., example="HJ01ME5678", min_length=7, max_length=10)
    kilometers_driven: int = Field(..., ge=0)
    price: int = Field(..., gt=0)
    city: str = Field(..., min_length=2)
    latitude: float
    longitude: float
    seller_phone: str = Field(..., min_length=10, max_length=15)
    description: Optional[str] = None


class VehicleListingUpdate(BaseModel):
    kilometers_driven: Optional[int] = Field(None, ge=0)
    price: Optional[int] = Field(None, gt=0)
    city: Optional[str] = Field(None, min_length=2)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
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
    distance: Optional[float] = None
    is_boosted: Optional[bool] = False

    class Config:
        from_attributes = True


class RCRequest(BaseModel):
    reg_no: str


class VehicleVerificationResponse(BaseModel):
    reg_no: str
    status: str
    data: dict


class LocationRequest(BaseModel):
    lat: Optional[str] = Field(None, example="24.5164769", description="Latitude of the Location")
    lng: Optional[str] = Field(None, example="93.9582257", description="Longitude of the Location")
    placeId: Optional[str] = Field(None, example="ChIJx1TRmPU4STcRRIakUus7TY4", description="Google Places API Place ID")


class LocationDetail(BaseModel):
    mainText: str = Field(..., description="The main address text or Place name")
    secondaryText: Optional[str] = Field(None, description="The secondary address text")
    state: str = Field(..., description="State name")
    country: str = Field(..., description="Country name")
    lat: float
    lng: float
    placeId: Optional[str] = None





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


class GoogleToken(BaseModel):
    token: str


# --- Boost Schemas ---

class BoostPackageBase(BaseModel):
    name: str
    duration_days: int
    price: float
    type: str

class BoostPackage(BoostPackageBase):
    id: int
    is_active: bool

    class Config:
        from_attributes = True

class UserBoostBase(BaseModel):
    package_id: int
    listing_id: Optional[int] = None

class UserBoostCreate(UserBoostBase):
    pass

class UserBoost(UserBoostBase):
    id: int
    user_id: int
    start_date: datetime
    end_date: datetime

    class Config:
        from_attributes = True


class BoostSubscriptionCreate(BaseModel):
    package_id: int
    listing_id: Optional[int] = None


class BoostSubscriptionResponse(BaseModel):
    order_id: str
    razorpay_key_id: str
    amount: float
    currency: str
    name: str
    description: str
    prefill: dict


class BoostPaymentVerification(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str
    package_id: int
    listing_id: Optional[int] = None


class BoostPaymentVerificationResponse(BaseModel):
    status: str
    user_boost: UserBoost


# --- Stats Schemas ---

class UserActivityBase(BaseModel):
    activity_type: str
    details: Optional[dict] = None


class UserActivityCreate(UserActivityBase):
    user_id: int


class UserActivity(UserActivityBase):
    id: int
    user_id: int
    timestamp: datetime

    class Config:
        from_attributes = True


class ListingViewBase(BaseModel):
    listing_id: int
    user_id: Optional[int] = None


class ListingViewCreate(ListingViewBase):
    pass


class ListingView(ListingViewBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True


class ListingStats(BaseModel):
    total_views: int
    views_last_7_days: int
    today_views: int
    views_last_30_days: int