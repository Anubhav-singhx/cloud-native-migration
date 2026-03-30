from fastapi import FastAPI, HTTPException, Depends, Header
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from datetime import datetime
import requests
import os
import logging

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/product_db")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")
JAEGER_ENDPOINT = os.getenv("JAEGER_ENDPOINT", "http://jaeger:4317")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from opentelemetry.sdk.resources import Resource

grpc_endpoint = JAEGER_ENDPOINT.replace("http://", "").replace("https://", "")
provider = TracerProvider(resource=Resource.create({"service.name": "product-service"}))
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=grpc_endpoint, insecure=True)))

trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)
RequestsInstrumentor().instrument()

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Product Service", version="1.0.0")
Instrumentator().instrument(app).expose(app)
FastAPIInstrumentor.instrument_app(app)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def require_auth(authorization: str = Header(None)) -> dict:
    """
    Validate JWT by calling auth-service.
    This is the microservices pattern: no shared JWT logic.
    Each service delegates auth to the auth-service.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header required")
    
    try:
        response = requests.get(
            f"{AUTH_SERVICE_URL}/auth/validate",
            headers={"Authorization": authorization},
            timeout=5
        )
         
        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Invalid token")
        return response.json()
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=503, detail="Auth service unavailable")


class ProductCreate(BaseModel):
    name: str
    description: str = ""
    price: float
    stock: int = 0

class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    stock: int | None = None

class StockUpdate(BaseModel):
    quantity: int  

@app.get("/health")
@app.get("/products/health")
def health():
    return {"status": "healthy", "service": "product-service", "timestamp": datetime.utcnow().isoformat()}

@app.get("/products")
def list_products(db: Session = Depends(get_db)):
    with tracer.start_as_current_span("list-products"):
        products = db.query(Product).all()
        return [{"id": p.id, "name": p.name, "description": p.description, 
                 "price": p.price, "stock": p.stock} for p in products]

@app.get("/products/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    with tracer.start_as_current_span("get-product"):
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return {"id": product.id, "name": product.name, "description": product.description,
                "price": product.price, "stock": product.stock}

@app.post("/products", status_code=201)
def create_product(product_data: ProductCreate, db: Session = Depends(get_db), 
                   user: dict = Depends(require_auth)):
    with tracer.start_as_current_span("create-product"):
        product = Product(**product_data.dict())
        db.add(product)
        db.commit()
        db.refresh(product)
        logger.info(f"Product created: {product.name} by user {user['user_id']}")
        return {"id": product.id, "name": product.name, "message": "Product created"}

@app.patch("/products/{product_id}/stock")
def update_stock(product_id: int, update: StockUpdate, db: Session = Depends(get_db)):
    """
    Called internally by order-service to reduce stock when an order is placed.
    This is the key difference from the monolith: order-service cannot directly
    modify the products table — it must go through this API.
    """
    with tracer.start_as_current_span("update-stock"):
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        new_stock = product.stock + update.quantity
        if new_stock < 0:
            raise HTTPException(status_code=400, detail="Insufficient stock")
        
        product.stock = new_stock
        db.commit()
        logger.info(f"Stock updated for product {product_id}: {update.quantity} units")
        return {"product_id": product_id, "new_stock": product.stock}
