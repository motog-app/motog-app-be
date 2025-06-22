# app/models.py
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base # Ensure Base is correctly imported
import enum

# Define VehicleTypeEnum here if it's not already in its own file
class VehicleTypeEnum(str, enum.Enum):
    car = "car"
    bike = "bike"

# User SQLAlchemy ORM Model
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Define relationship to listings
    listings = relationship("VehicleListing", back_populates="owner")

# VehicleListing SQLAlchemy ORM Model
class VehicleListing(Base):
    __tablename__ = "vehicle_listings" # Ensure this matches your actual table name

    id = Column(Integer, primary_key=True, index=True)
    vehicle_type = Column(Enum(VehicleTypeEnum), index=True) # Use Enum type
    # make = Column(String, index=True)
    # model = Column(String, index=True)
    # year = Column(Integer)
    kilometers_driven = Column(Integer)
    price = Column(Integer)
    usr_inp_city = Column(String, index=True)
    city = Column(String)
    latitude = Column(Float, nullable=True) # <-- ADDED
    longitude = Column(Float, nullable=True) # <-- ADDED
    seller_phone = Column(String)
    description = Column(String)
    primary_image_url = Column(String, nullable=True) # URL from Cloudinary
    is_active = Column(Boolean, default=True) # For soft delete

    user_id = Column(Integer, ForeignKey("users.id"))
    owner = relationship("User", back_populates="listings") # Relationship back to User

    reg_no = Column(String, ForeignKey("vehicle_verifications.reg_no"), nullable=False)
    verification = relationship("VehicleVerification", back_populates="listing", lazy="joined")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
class VehicleVerification(Base):
    __tablename__ = "vehicle_verifications"
    
    reg_no = Column(String, primary_key=True, index=True)
    status = Column(String)
    raw_data = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    #define relationship to Vehicle Listing
    listing = relationship("VehicleListing", back_populates="verification", uselist=False)