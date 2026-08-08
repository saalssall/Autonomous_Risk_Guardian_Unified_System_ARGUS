from sqlalchemy import create_engine, Column, Float, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
import os

# ADDED: configurable via env var so a Docker volume can be mounted at a
# stable path and survive container restarts. Defaults to "." — the exact
# previous behavior — for local (non-Docker) runs.
DATA_DIR = os.environ.get("ARGUS_DATA_DIR", ".")
os.makedirs(DATA_DIR, exist_ok=True)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DATA_DIR}/argus.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
class NodeModel(Base):
    __tablename__ = "nodes"
    node_id = Column(String, primary_key=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    status = Column(String, nullable=False)  # HEALTHY, DEGRADED, OFFLINE
    last_seen = Column(DateTime, default=datetime.datetime.utcnow)
    battery = Column(Integer, nullable=False)
    # Relationships with cascade deletion
    sensor_readings = relationship("SensorReadingModel", back_populates="node", cascade="all, delete-orphan")
    camera_observations = relationship("CameraObservationModel", back_populates="node", cascade="all, delete-orphan")
class SensorReadingModel(Base):
    __tablename__ = "sensor_readings"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    node_id = Column(String, ForeignKey("nodes.node_id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    distance = Column(Float, nullable=False)
    sound = Column(Float, nullable=True)         
    beam_status = Column(String, nullable=True)  
    latitude = Column(Float, nullable=True)      
    longitude = Column(Float, nullable=True)
    # ADDED — device condition, per the "common variables" spec
    esp32_online = Column(Boolean, nullable=True)
    dht11_status = Column(String, nullable=True)
    hcsr04_status = Column(String, nullable=True)
    ir_beam_status = Column(String, nullable=True)
    network_status = Column(String, nullable=True)
    node = relationship("NodeModel", back_populates="sensor_readings")
class CameraObservationModel(Base):
    __tablename__ = "camera_observations"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    node_id = Column(String, ForeignKey("nodes.node_id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    image_url = Column(String, nullable=False)   
    smoke = Column(Boolean, default=False)
    water = Column(Boolean, default=False)
    person = Column(Boolean, default=False)
    debris = Column(Boolean, default=False)
    confidence = Column(Float, nullable=False)
    node = relationship("NodeModel", back_populates="camera_observations")
class RiskAssessmentModel(Base):
    __tablename__ = "risk_assessments"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    node_id = Column(String, ForeignKey("nodes.node_id", ondelete="CASCADE"), nullable=True, index=True)  # ADDED — nullable so old seeded rows stay valid
    region = Column(String, nullable=False)
    hazard = Column(String, nullable=False)
    risk_score = Column(Float, nullable=True)  # ADDED — real 0-100 computed score; risk_level below is just its bucket
    risk_level = Column(String, nullable=False)  # LOW, GUARDED, ELEVATED, HIGH, CRITICAL
    confidence = Column(Float, nullable=False)
    trend = Column(String, nullable=True)  # ADDED — increasing / decreasing / steady
    disaster_profile = Column(String, nullable=True)  # ADDED — which weight profile was used: general/flood/heat
    explanation = Column(String, nullable=True)  
    recommendation = Column(String, nullable=False)
    node = relationship("NodeModel")
def init_db():
    Base.metadata.create_all(bind=engine)
