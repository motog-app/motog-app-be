from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Text, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime
import enum

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True) # Can be used to deactivate users

    listings = relationship("VehicleListing", back_populates="owner")


class VehicleTypeEnum(str, enum.Enum):
    CAR = "car"
    BIKE = "bike"


class VehicleListing(Base):
    __tablename__ = "vehicle_listings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    vehicle_type = Column(SQLAlchemyEnum(VehicleTypeEnum), nullable=False)
    make = Column(String, index=True, nullable=False)
    model = Column(String, index=True, nullable=False)
    year = Column(Integer, nullable=False)
    kilometers_driven = Column(Integer, nullable=False)
    price = Column(Integer, nullable=False)
    city = Column(String, index=True, nullable=False)
    seller_phone = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    primary_image_url = Column(String, nullable=True) # Store URL of the image
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True) # For soft delete or admin approval

    owner = relationship("User", back_populates="listings")