# app/models.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Boolean,
    ForeignKey,
    Enum,
    Numeric,
    Index,
)
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
    boosts = relationship("UserBoost", back_populates="owner")
    activities = relationship("UserActivity", back_populates="user")
    views = relationship("ListingView", back_populates="user")


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

    reg_no = Column(String, ForeignKey("vehicle_verifications.reg_no"), nullable=False)
    verification = relationship(
        "VehicleVerification", back_populates="listing", lazy="joined"
    )

    images = relationship(
        "ListingImage", back_populates="listing", cascade="all, delete-orphan"
    )
    boosts = relationship("UserBoost", back_populates="listing")
    views = relationship("ListingView", back_populates="listing")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        Index(
            'idx_vehicle_listings_location',
            'latitude',
            'longitude',
            postgresql_using='gist'
        ),
    )


class VehicleVerification(Base):
    __tablename__ = "vehicle_verifications"

    reg_no = Column(String, primary_key=True, index=True)
    status = Column(String)
    raw_data = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # define relationship to Vehicle Listing
    listing = relationship(
        "VehicleListing", back_populates="verification", uselist=False
    )


class ListingImage(Base):
    __tablename__ = "listing_images"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("vehicle_listings.id", ondelete="CASCADE"))
    url = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False)

    listing = relationship("VehicleListing", back_populates="images")


class BoostPackage(Base):
    __tablename__ = "boost_packages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    duration_days = Column(Integer, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    type = Column(String(50), nullable=False)  # 'single_listing' or 'bundle'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user_boosts = relationship("UserBoost", back_populates="package")


class UserBoost(Base):
    __tablename__ = "user_boosts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    package_id = Column(Integer, ForeignKey("boost_packages.id"), nullable=False)
    listing_id = Column(
        Integer, ForeignKey("vehicle_listings.id"), nullable=True
    )  # Nullable for bundle boosts
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="boosts")
    package = relationship("BoostPackage", back_populates="user_boosts")
    listing = relationship("VehicleListing", back_populates="boosts")


class UserActivityTypeEnum(str, enum.Enum):
    login = "login"
    search = "search"


class UserActivity(Base):
    __tablename__ = "user_activities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    activity_type = Column(Enum(UserActivityTypeEnum), index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    details = Column(JSONB)

    user = relationship("User", back_populates="activities")


class ListingView(Base):
    __tablename__ = "listing_views"

    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("vehicle_listings.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    listing = relationship("VehicleListing", back_populates="views")
    user = relationship("User", back_populates="views")