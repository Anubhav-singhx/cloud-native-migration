from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
import os
import logging


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/auth_db")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
JAEGER_ENDPOINT = os.getenv("JAEGER_ENDPOINT", "http://jaeger:4317")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from opentelemetry.sdk.resources import Resource

provider = TracerProvider(
    resource=Resource.create({"service.name": "auth-service"})
)

otlp_exporter = OTLPSpanExporter(endpoint=JAEGER_ENDPOINT, insecure=True)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)


engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Auth Service",
    description="Handles user registration, login, and JWT token validation",
    version="1.0.0"
)

Instrumentator().instrument(app).expose(app)

FastAPIInstrumentor.instrument_app(app)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def create_token(user_id: int, username: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str

class UserResponse(BaseModel):
    user_id: int
    username: str
    email: str


class ValidateResponse(BaseModel):
    valid: bool
    user_id: int
    username: str
@app.get("/health")
@app.get("/auth/health")
def health():
    return {"status": "healthy", "service": "auth-service", "timestamp": datetime.utcnow().isoformat()}

@app.post("/auth/register", response_model=UserResponse, status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    with tracer.start_as_current_span("register-user"):
        if db.query(User).filter(User.username == req.username).first():
            raise HTTPException(status_code=409, detail="Username already exists")
        
        if db.query(User).filter(User.email == req.email).first():
            raise HTTPException(status_code=409, detail="Email already exists")
        
        user = User(
            username=req.username,
            email=req.email,
            hashed_password=hash_password(req.password)
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"New user registered: {user.username} (id={user.id})")
        return UserResponse(user_id=user.id, username=user.username, email=user.email)

@app.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    with tracer.start_as_current_span("login-user"):
        user = db.query(User).filter(User.username == req.username).first()
        
        if not user or not verify_password(req.password, user.hashed_password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        token = create_token(user.id, user.username)
        logger.info(f"User logged in: {user.username}")
        
        return TokenResponse(
            access_token=token,
            user_id=user.id,
            username=user.username
        )
@app.get("/auth/validate", response_model=ValidateResponse)
def validate_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Called by other microservices to verify a JWT token.
    This is the key: instead of each service having JWT logic,
    they all call this endpoint.
    """
    with tracer.start_as_current_span("validate-token"):
        payload = decode_token(credentials.credentials)
        return ValidateResponse(
            valid=True,
            user_id=int(payload["sub"]),
            username=payload["username"]
        )
@app.get("/auth/profile")
def profile(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    payload = decode_token(credentials.credentials)
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user_id": user.id, "username": user.username, "email": user.email, "created_at": user.created_at.isoformat()}