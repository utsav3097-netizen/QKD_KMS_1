import uuid
import enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Enum as SQLEnum, DateTime, func

Base = declarative_base()

class ItemState(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    CONSUMED = "CONSUMED"

class QKDKeyModel(Base):
    __tablename__ = "qkd_keys"

    key_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    key_material = Column(String, nullable=False)  # Stored as HEX entropy
    slave_sae_id = Column(String, nullable=True)   # Target Secure Application Entity ID
    state = Column(SQLEnum(ItemState), default=ItemState.AVAILABLE, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())