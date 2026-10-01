from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import session, engine
import database_models
from sqlalchemy.orm import Session
from database_models import ItemState, QKDKeyModel
from pydantic import BaseModel

import structlog
import logging

# Configure structlog to output professional JSON security logs
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.dict_tracebacks,
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)

logger = structlog.get_logger()

class KeyCreate(BaseModel):
    key_material: str

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database tables
#database_models.Base.metadata.create_all(bind=engine)

@app.get("/")
def greet():
    return {"message": "ETSI QKD 014 Key Management System API Active"}

def get_db():
    db = session()
    try:
        yield db
    finally:
        db.close()

# Seed initial mock quantum keys if buffer is empty
def init_db():
    db = session()
    count = db.query(QKDKeyModel).count()
    if count == 0:
        sample_keys = [
            QKDKeyModel(key_material="A1B2C3D4E5F67890123456789ABCDEF0", slave_sae_id=None),
            QKDKeyModel(key_material="1234567890ABCDEF1234567890ABCDEF", slave_sae_id=None),
            QKDKeyModel(key_material="FEDCBA9876543210FEDCBA9876543210", slave_sae_id=None),
            QKDKeyModel(key_material="99887766554433221100FFEEDCCBBAA9", slave_sae_id=None),
            QKDKeyModel(key_material="112233445566778899AABBCCDDEEFF00", slave_sae_id=None)
        ]
        db.add_all(sample_keys)
        db.commit()

init_db()

@app.get("/api/v1/keys")
def get_all_keys(db: Session = Depends(get_db)):
    return db.query(QKDKeyModel).all()

@app.get("/api/v1/keys/{key_id}")
def get_key_by_id(key_id: str, db: Session = Depends(get_db)):
    key = db.query(QKDKeyModel).filter(QKDKeyModel.key_id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    return key

# ETSI QKD 014 Standard Endpoint: Get/Reserve keys for a specific target SAE
@app.post("/api/v1/keys/{slave_sae_id}/enc_keys")
def reserve_qkd_key(slave_sae_id: str, db: Session = Depends(get_db)):
    # Concurrency-safe row locking using PostgreSQL SKIP LOCKED
    key = db.query(QKDKeyModel)\
            .filter(QKDKeyModel.state == ItemState.AVAILABLE)\
            .with_for_update(skip_locked=True)\
            .first()

    if not key:
        logger.warning("qkd_buffer_empty", action="key_reserve_failed", sae_id=slave_sae_id)
        raise HTTPException(status_code=404, detail="No AVAILABLE keys left in buffer.")

    key.state = ItemState.RESERVED
    key.slave_sae_id = slave_sae_id
    db.commit()

    # Audit log the reservation
    logger.info("qkd_key_reserved", action="key_reserve", key_id=key.key_id, sae_id=slave_sae_id)

    # ETSI QKD 014 compliant JSON payload structure
    return {
        "keys": [
            {
                "key_id": key.key_id,
                "key": key.key_material
            }
        ]
    }

@app.post("/api/v1/keys/{key_id}/release")
def release_qkd_key(key_id: str, db: Session = Depends(get_db)):
    key = db.query(QKDKeyModel).filter(QKDKeyModel.key_id == key_id).first()

    if not key:
        raise HTTPException(status_code=404, detail="Key not found")

    old_sae = key.slave_sae_id
    key.state = ItemState.AVAILABLE
    key.slave_sae_id = None
    db.commit()

    # Audit log the release
    logger.info("qkd_key_released", action="key_release", key_id=key.key_id, released_from=old_sae)

    return {
        "message": f"Successfully released key {key.key_id} back to AVAILABLE!",
        "key_id": key.key_id,
        "new_state": key.state
    }

@app.post("/api/v1/keys/{key_id}/consume")
def consume_qkd_key(key_id: str, db: Session = Depends(get_db)):
    key = db.query(QKDKeyModel).filter(QKDKeyModel.key_id == key_id).first()

    if not key:
        raise HTTPException(status_code=404, detail="Key not found")

    if key.state != ItemState.RESERVED:
        logger.warning("qkd_invalid_consumption_attempt", action="key_consume_failed", key_id=key_id, current_state=key.state.value)
        raise HTTPException(status_code=400, detail="Only RESERVED keys can be consumed")

    key.state = ItemState.CONSUMED
    db.commit()

    # Audit log the permanent consumption
    logger.info("qkd_key_consumed", action="key_burn", key_id=key.key_id, sae_id=key.slave_sae_id)

    return {
        "message": f"Successfully consumed and retired key {key.key_id}!",
        "key_id": key.key_id,
        "new_state": key.state
    }

@app.delete("/api/v1/keys/{key_id}")
def delete_qkd_key(key_id: str, db: Session = Depends(get_db)):
    key = db.query(QKDKeyModel).filter(QKDKeyModel.key_id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="Key not found")
    db.delete(key)
    db.commit()

    logger.info("qkd_key_deleted", action="key_delete", key_id=key_id)
    return {"message": "Key deleted successfully"}

# Simulated QKD Node Endpoint: Push new entropy into the KMS buffer
@app.post("/api/v1/keys")
def add_qkd_key(key_data: KeyCreate, db: Session = Depends(get_db)):
    # The UUID and AVAILABLE state are handled automatically by the database defaults
    new_key = database_models.QKDKeyModel(key_material=key_data.key_material)

    db.add(new_key)
    db.commit()
    db.refresh(new_key)

    # Audit log the generation of new entropy
    logger.info(
        "qkd_entropy_injected",
        action="key_buffer_add",
        key_id=new_key.key_id,
        state=new_key.state.value
    )

    return {
        "message": "New key successfully injected into buffer",
        "key_id": new_key.key_id,
        "key_material": new_key.key_material
    }