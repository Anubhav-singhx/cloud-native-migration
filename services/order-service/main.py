# services/order-service/main.py
# Owns: Order lifecycle (create, get, update status)
# Database: Own PostgreSQL schema (orders table)
# Talks to: product-service (HTTP) to check/reduce stock
# Talks to: notification-service (HTTP) to send order confirmation

from fastapi import FastAPI, HTTPException, Depends, Header
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
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

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/order_db")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://auth-service:8001")
PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8002")
NOTIFICATION_SERVICE_URL = os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8004")
JAEGER_ENDPOINT = os.getenv("JAEGER_ENDPOINT", "http://jaeger:4317")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# TRACING
# ─────────────────────────────────────────────

from opentelemetry.sdk.resources import Resource

provider = TracerProvider(
    resource=Resource.create({"service.name": "order-service"})
)
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=JAEGER_ENDPOINT, insecure=True)))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)
RequestsInstrumentor().instrument()

# ─────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    product_id = Column(Integer, nullable=False)
    product_name = Column(String(100))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(String(50), default="confirmed")
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# ─────────────────────────────────────────────
# APP
# ─────────────────────────────────────────────

app = FastAPI(title="Order Service", version="1.0.0")
Instrumentator().instrument(app).expose(app)
FastAPIInstrumentor.instrument_app(app)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def require_auth(authorization: str = Header(None)) -> dict:
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

# ─────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────

class OrderCreate(BaseModel):
    product_id: int
    quantity: int

# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "healthy", "service": "order-service", "timestamp": datetime.utcnow().isoformat()}

@app.post("/orders", status_code=201)
def create_order(order_data: OrderCreate, db: Session = Depends(get_db),
                 user: dict = Depends(require_auth), authorization: str = Header(None)):
    with tracer.start_as_current_span("create-order") as span:
        span.set_attribute("user.id", user["user_id"])
        span.set_attribute("product.id", order_data.product_id)
        
        # Step 1: Fetch product details from product-service (HTTP call, not DB query)
        try:
            product_response = requests.get(
                f"{PRODUCT_SERVICE_URL}/products/{order_data.product_id}",
                timeout=5
            )
        except requests.exceptions.RequestException:
            raise HTTPException(status_code=503, detail="Product service unavailable")
        
        if product_response.status_code == 404:
            raise HTTPException(status_code=404, detail="Product not found")
        
        product = product_response.json()
        
        if product["stock"] < order_data.quantity:
            raise HTTPException(status_code=400, detail="Insufficient stock")
        
        total_price = product["price"] * order_data.quantity
        
        # Step 2: Reduce stock via product-service API
        try:
            stock_response = requests.patch(
                f"{PRODUCT_SERVICE_URL}/products/{order_data.product_id}/stock",
                json={"quantity": -order_data.quantity},
                timeout=5
            )
            if stock_response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to update stock")
        except requests.exceptions.RequestException:
            raise HTTPException(status_code=503, detail="Product service unavailable")
        
        # Step 3: Save order to our own DB
        order = Order(
            user_id=user["user_id"],
            product_id=order_data.product_id,
            product_name=product["name"],
            quantity=order_data.quantity,
            unit_price=product["price"],
            total_price=total_price,
            status="confirmed"
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        
        logger.info(f"Order {order.id} created for user {user['user_id']}")
        
        # Step 4: Notify via notification-service (async, fire-and-forget)
        # Even if this fails, the order is already saved — graceful degradation
        try:
            requests.post(
                f"{NOTIFICATION_SERVICE_URL}/notifications",
                json={
                    "user_id": user["user_id"],
                    "message": f"Order #{order.id} confirmed! {order_data.quantity}x {product['name']} for ${total_price:.2f}",
                    "notification_type": "order_confirmation"
                },
                timeout=3
            )
        except Exception:
            logger.warning(f"Notification service unavailable for order {order.id} — continuing")
        
        return {
            "order_id": order.id,
            "product_name": product["name"],
            "quantity": order_data.quantity,
            "total_price": total_price,
            "status": order.status
        }

@app.get("/orders")
def get_orders(db: Session = Depends(get_db), user: dict = Depends(require_auth)):
    with tracer.start_as_current_span("get-user-orders"):
        orders = db.query(Order).filter(Order.user_id == user["user_id"]).all()
        return [{
            "order_id": o.id,
            "product_name": o.product_name,
            "quantity": o.quantity,
            "total_price": o.total_price,
            "status": o.status,
            "created_at": o.created_at.isoformat()
        } for o in orders]