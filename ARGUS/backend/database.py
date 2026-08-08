from sqlalchemy import create_engine, Column, Float, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime
SQLALCHEMY_DATABASE_URL = "sqlite:///./argus.db"
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
    region = Column(String, nullable=False)
    hazard = Column(String, nullable=False)
    risk_level = Column(String, nullable=False)  # LOW, GUARDED, ELEVATED, HIGH, CRITICAL
    confidence = Column(Float, nullable=False)
    explanation = Column(String, nullable=True)  
    recommendation = Column(String, nullable=False)
def init_db():
    Base.metadata.create_all(bind=engine)
