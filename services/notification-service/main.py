

from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from datetime import datetime
import os
import logging

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/notification_db")
JAEGER_ENDPOINT = os.getenv("JAEGER_ENDPOINT", "http://jaeger:4317")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from opentelemetry.sdk.resources import Resource

provider = TracerProvider(
    resource=Resource.create({"service.name": "notification-service"})
)
provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=JAEGER_ENDPOINT, insecure=True)))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer(__name__)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50))
    sent_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Notification Service", version="1.0.0")
Instrumentator().instrument(app).expose(app)
FastAPIInstrumentor.instrument_app(app)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class NotificationCreate(BaseModel):
    user_id: int
    message: str
    notification_type: str = "general"

@app.get("/health")
def health():
    return {"status": "healthy", "service": "notification-service", "timestamp": datetime.utcnow().isoformat()}

@app.post("/notifications", status_code=201)
def send_notification(data: NotificationCreate, db: Session = Depends(get_db)):
    with tracer.start_as_current_span("send-notification"):
        notification = Notification(
            user_id=data.user_id,
            message=data.message,
            notification_type=data.notification_type
        )
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        logger.info(f"📧 NOTIFICATION [user={data.user_id}] [{data.notification_type}]: {data.message}")
        
        return {"notification_id": notification.id, "status": "sent"}

@app.get("/notifications/{user_id}")
def get_notifications(user_id: int, db: Session = Depends(get_db)):
    notifications = db.query(Notification).filter(
        Notification.user_id == user_id
    ).order_by(Notification.sent_at.desc()).all()
    
    return [{
        "id": n.id,
        "message": n.message,
        "type": n.notification_type,
        "sent_at": n.sent_at.isoformat()
    } for n in notifications]