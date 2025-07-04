# app/models.py
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base
import enum


class VehicleTypeEnum(str, enum.Enum):
    car = "car"
    bike = "bike"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=True)
    is_email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Define relationship to listings
    listings = relationship("VehicleListing", back_populates="owner")


class VehicleListing(Base):
    __tablename__ = "vehicle_listings"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_type = Column(Enum(VehicleTypeEnum), index=True)
    kilometers_driven = Column(Integer)
    price = Column(Integer)
    usr_inp_city = Column(String, index=True)
    city = Column(String)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    seller_phone = Column(String)
    description = Column(String)
    is_active = Column(Boolean, default=True)  # For soft delete

    user_id = Column(Integer, ForeignKey("users.id"))
    # Relationship back to User
    owner = relationship("User", back_populates="listings")

    reg_no = Column(String, ForeignKey(
        "vehicle_verifications.reg_no"), nullable=False)
    verification = relationship(
        "VehicleVerification", back_populates="listing", lazy="joined")

    images = relationship(
        "ListingImage", back_populates="listing", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class VehicleVerification(Base):
    __tablename__ = "vehicle_verifications"

    reg_no = Column(String, primary_key=True, index=True)
    status = Column(String)
    raw_data = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # define relationship to Vehicle Listing
    listing = relationship(
        "VehicleListing", back_populates="verification", uselist=False)


class ListingImage(Base):
    __tablename__ = "listing_images"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey(
        "vehicle_listings.id", ondelete="CASCADE"))
    url = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False)

    listing = relationship("VehicleListing", back_populates="images")
