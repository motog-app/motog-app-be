# app/schemas.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from .models import VehicleTypeEnum # Import from your models
from fastapi import UploadFile, File

# --- User Schemas ---
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)

class User(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True # Pydantic V2 (was orm_mode = True in V1)

# --- Token Schemas (for JWT) ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None


# --- Vehicle Listing Schemas ---
class VehicleListingBase(BaseModel):
    vehicle_type: VehicleTypeEnum
    reg_no: str = Field(..., min_length=7, max_length=10)
    # make: str = Field(..., min_length=2)
    # model: str = Field(..., min_length=1)
    # year: int = Field(..., gt=1950, lt=datetime.now().year + 2) # Sensible year range
    kilometers_driven: int = Field(..., ge=0)
    price: int = Field(..., gt=0)
    usr_inp_city: str = Field(..., min_length=2)
    city: str = Field(..., min_length=2)
    seller_phone: str = Field(..., min_length=10, max_length=15) # Basic phone validation
    description: Optional[str] = None
    primary_image_url: Optional[str] = None


class VehicleListingCreate(VehicleListingBase):
    pass # All fields inherited from VehicleListingBase are needed for creation by user

class VehicleListingUpdate(BaseModel):
    # For updates, make all fields optional if needed, or define specific update schema
    # vehicle_type: Optional[VehicleTypeEnum] = None
    # make: Optional[str] = Field(None, min_length=2)
    # model: Optional[str] = Field(None, min_length=1)
    # year: Optional[int] = Field(None, gt=1950, lt=datetime.now().year + 2)
    kilometers_driven: Optional[int] = Field(None, ge=0)
    price: Optional[int] = Field(None, gt=0)
    city: Optional[str] = Field(None, min_length=2)
    # city: Optional[str] = Field(None, min_length=2)
    seller_phone: Optional[str] = Field(None, min_length=10, max_length=15)
    description: Optional[str] = Field(None, min_length=1, max_length=250)
    # primary_image_url: Optional[UploadFile] = File(...) # get it separately


class VehicleListing(VehicleListingBase):
    id: int
    user_id: int
    is_active: bool
    created_at: datetime
    primary_image_url: Optional[str] = None # ADDED: This should be here for responses
    owner_email: Optional[EmailStr] = None # For display purposes

    class Config:
        from_attributes = True
        
class RCRequest(BaseModel):
    reg_no: str

class VehicleVerificationResponse(BaseModel):
    reg_no: str
    status: str
    data: dict