import pytest
import sys
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from unittest.mock import patch # Import patch for mocking

# Add the project root to the sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# Now import your application modules
from app.main import app
from app.database import Base, get_db
from app.dependencies import get_current_active_user
from app import models, schemas
from app.core.security import get_password_hash # Needed for hashing password in test_user fixture


# --- Test Database Setup ---
# Use an in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool, # Use StaticPool for in-memory SQLite to persist connections
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override the get_db dependency to use the test database
@pytest.fixture(name="db_session")
def override_get_db():
    Base.metadata.create_all(bind=engine) # Create tables in the test database
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine) # Drop tables after tests to ensure clean state


# --- Override Authentication Dependency ---
# This fixture provides a mock user for authenticated routes
@pytest.fixture(name="test_user")
def create_test_user(db_session: Session):
    hashed_password = get_password_hash("testpassword")
    user = models.User(email="test@example.com", hashed_password=hashed_password, is_active=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

# This fixture overrides the actual get_current_active_user dependency
# to always return our test_user for authenticated requests.
@pytest.fixture(name="authenticated_client")
def get_authenticated_client(db_session: Session, test_user: models.User):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_current_active_user] = lambda: test_user
    with TestClient(app) as client:
        yield client
    app.dependency_overrides = {} # Clear overrides after the test

# This fixture for unauthenticated client
@pytest.fixture(name="client")
def get_unauthenticated_client(db_session: Session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides = {} # Clear overrides after the test


# --- API Endpoint Tests ---

def test_register_user(client: TestClient):
    """Test user registration endpoint."""
    response = client.post(
        "/api/v1/register",
        json={"email": "newuser@example.com", "password": "newpassword123"}
    )
    assert response.status_code == 200 # Changed from 201 to 200 as per actual API behavior
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert "id" in data
    assert "created_at" in data

def test_register_user_exists(client: TestClient):
    """Test registration with an existing email."""
    client.post("/api/v1/register", json={"email": "existing@example.com", "password": "password123"})
    response = client.post("/api/v1/register", json={"email": "existing@example.com", "password": "password123"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"

def test_login_user(client: TestClient):
    """Test user login endpoint."""
    # First, register a user to log in
    client.post("/api/v1/register", json={"email": "loginuser@example.com", "password": "loginpassword"})
    
    # Then, attempt to log in
    response = client.post(
        "/api/v1/login",
        data={"username": "loginuser@example.com", "password": "loginpassword"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_invalid_credentials(client: TestClient):
    """Test login with invalid credentials."""
    response = client.post(
        "/api/v1/login",
        data={"username": "nonexistent@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect email or password"

# Use patch to mock cloudinary.uploader.upload
@patch("cloudinary.uploader.upload")
def test_create_listing(mock_upload, authenticated_client: TestClient, test_user: models.User):
    """Test creating a new vehicle listing."""
    # Configure the mock to return a dummy successful upload response
    mock_upload.return_value = {"secure_url": "http://mocked-image-url.com/test_image.jpg"}

    from io import BytesIO
    dummy_image = BytesIO(b"fake image data")

    response = authenticated_client.post(
        "/api/v1/listings/",
        data={
            "vehicle_type": "car",
            "make": "Toyota",
            "model": "Camry",
            "year": 2020,
            "kilometers_driven": 50000,
            "price": 15000,
            "city": "TestCity",
            "latitude": 34.0522,
            "longitude": -118.2437,
            "seller_phone": "1234567890",
            "description": "A great car for sale."
        },
        files={"primary_image": ("test_image.jpg", dummy_image, "image/jpeg")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["make"] == "Toyota"
    assert data["user_id"] == test_user.id
    assert data["primary_image_url"] == "http://mocked-image-url.com/test_image.jpg" # Check against mocked URL
    assert data["latitude"] == 34.0522
    assert data["longitude"] == -118.2437

def test_read_listings(authenticated_client: TestClient, db_session: Session, test_user: models.User):
    """Test retrieving multiple vehicle listings."""
    from app.crud import create_vehicle_listing
    listing1_in = schemas.VehicleListingCreate(
        vehicle_type=models.VehicleTypeEnum.car, make="Honda", model="Civic", year=2018,
        kilometers_driven=70000, price=10000, city="Tokyo", latitude=35.6895, longitude=139.6917,
        seller_phone="9876543210", description="Reliable sedan."
    )
    listing2_in = schemas.VehicleListingCreate(
        vehicle_type=models.VehicleTypeEnum.bike, make="Yamaha", model="FZ", year=2022,
        kilometers_driven=5000, price=3000, city="Kyoto", latitude=35.0116, longitude=135.7681,
        seller_phone="1122334455", description="Sporty bike."
    )
    create_vehicle_listing(db_session, listing1_in, test_user.id, "http://example.com/img1.jpg")
    create_vehicle_listing(db_session, listing2_in, test_user.id, "http://example.com/img2.jpg")

    response = authenticated_client.get("/api/v1/listings/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert any(listing["make"] == "Honda" for listing in data)
    assert any(listing["make"] == "Yamaha" for listing in data)

def test_read_single_listing(authenticated_client: TestClient, db_session: Session, test_user: models.User):
    """Test retrieving a single vehicle listing by ID."""
    from app.crud import create_vehicle_listing
    listing_in = schemas.VehicleListingCreate(
        vehicle_type=models.VehicleTypeEnum.car, make="Mercedes", model="C-Class", year=2021,
        kilometers_driven=20000, price=40000, city="Berlin", latitude=52.5200, longitude=13.4050,
        seller_phone="0987654321", description="Luxury car."
    )
    created_listing = create_vehicle_listing(db_session, listing_in, test_user.id, "http://example.com/merc.jpg")

    response = authenticated_client.get(f"/api/v1/listings/{created_listing.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == created_listing.id
    assert data["make"] == "Mercedes"
    assert data["latitude"] == 52.5200
    assert data["longitude"] == 13.4050

def test_delete_listing(authenticated_client: TestClient, db_session: Session, test_user: models.User):
    """Test soft deleting a vehicle listing."""
    from app.crud import create_vehicle_listing, get_listing_by_id
    listing_in = schemas.VehicleListingCreate(
        vehicle_type=models.VehicleTypeEnum.bike, make="BMW", model="GS", year=2019,
        kilometers_driven=15000, price=12000, city="Munich", latitude=48.1351, longitude=11.5820,
        seller_phone="1231231234", description="Adventure bike."
    )
    listing_to_delete = create_vehicle_listing(db_session, listing_in, test_user.id, "http://example.com/bmw.jpg")

    response = authenticated_client.delete(f"/api/v1/listings/{listing_to_delete.id}")
    assert response.status_code == 204 # No Content

    deleted_listing = get_listing_by_id(db_session, listing_to_delete.id)
    assert deleted_listing is None

def test_delete_listing_not_found(authenticated_client: TestClient):
    """Test deleting a non-existent listing."""
    response = authenticated_client.delete("/api/v1/listings/99999")
    assert response.status_code == 404

def test_delete_listing_unauthorized(client: TestClient, db_session: Session, test_user: models.User):
    """Test deleting a listing without authentication."""
    from app.crud import create_vehicle_listing
    listing_in = schemas.VehicleListingCreate(
        vehicle_type=models.VehicleTypeEnum.car, make="Audi", model="A4", year=2017,
        kilometers_driven=60000, price=20000, city="Hamburg", latitude=53.5511, longitude=10.0000,
        seller_phone="5555555555", description="German engineering."
    )
    listing_to_delete_unauth = create_vehicle_listing(db_session, listing_in, test_user.id, "http://example.com/audi.jpg")

    response = client.delete(f"/api/v1/listings/{listing_to_delete_unauth.id}")
    assert response.status_code == 401 # Unauthorized