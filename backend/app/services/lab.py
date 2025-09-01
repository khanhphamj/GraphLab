from __future__ import annotations

from sqlalchemy.orm import Session
from app.models.lab import Lab
from app.schemas.lab import LabCreate, LabUpdate, LabResponse
from app.core.validators import validate_name, validate_description
from typing import Optional
from datetime import datetime, timezone
import logging
import uuid

logger = logging.getLogger(__name__)

class LabServiceError(Exception):
    def __init__(self, message: str, error_code: str = None, details: dict = None):
        super().__init__(message)
        self.error_code = error_code
        self.details = details
        self.timestamp = datetime.now(timezone.utc)

class LabNameAlreadyExistsError(LabServiceError):
    def __init__(self, name, owner_id: uuid.UUID):
        super().__init__(
            f"Lab name {name} already exists",
            error_code="LAB_NAME_ALREADY_EXISTS",
            details={"name": name, "owner_id": owner_id}
            )

class LabNotFoundError(LabServiceError):
    def __init__(self, name, owner_id: uuid.UUID):
        super().__init__(
            f"Lab not found with name: {name}",
            error_code="LAB_NOT_FOUND", 
            details={"name": name, "owner_id": owner_id}
            )

#Helper functions
def _active_by_name_owner_id(db: Session, name: str, owner_id: uuid.UUID = None) -> Optional[Lab]:
    return db.query(Lab).filter(
        Lab.name == name,
        Lab.deleted_at.is_(None),
        Lab.owner_id == owner_id if owner_id else True
        ).first()

#Service functions
def create_lab(db: Session, lab_in: LabCreate) -> LabResponse:
    try:
        #Validate name
        validate_name(lab_in.name)
        #Validate description
        validate_description(lab_in.description)
        existing_lab = _active_by_name_owner_id(db, lab_in.name, lab_in.owner_id)
        if existing_lab:
            logger.warning(f"Lab name {lab_in.name} already exists")
            raise LabNameAlreadyExistsError(lab_in.name, lab_in.owner_id)
        #Create lab
        lab = Lab(
            name=lab_in.name,
            description=lab_in.description,
            owner_id=lab_in.owner_id
            )
        #Add lab to database
        db.add(lab)
        db.commit()
        db.refresh(lab)
        logger.info(f"Lab {lab.id}, name {lab.name} created successfully")
        return LabResponse.model_validate(lab)

    except Exception as e:
        logger.error(f"Error creating lab: {e}")
        db.rollback()
        raise

def get_lab(db: Session, lab_name: str, owner_id: uuid.UUID) -> LabResponse:
    try:
        if not lab_name or not lab_name.strip():
            logger.warning("Lab name is required")
            raise ValueError("Lab name is required")

        if not owner_id:
            logger.warning("Owner ID is required")
            raise ValueError("Owner ID is required")

        lab = _active_by_name_owner_id(db, lab_name, owner_id)
        if not lab:
            logger.warning(f"Lab {lab_name} not found")
            raise LabNotFoundError(lab_name, owner_id)
        return LabResponse.model_validate(lab)
    except Exception as e:
        logger.error(f"Error getting lab: {e}")
        raise

def get_lab_model(db: Session, lab_name: str, owner_id: uuid.UUID) -> Lab:
    try:
        if not lab_name or not lab_name.strip():
            logger.warning("Lab name is required")
            raise ValueError("Lab name is required")

        if not owner_id:
            logger.warning("Owner ID is required")
            raise ValueError("Owner ID is required")

        lab = _active_by_name_owner_id(db, lab_name, owner_id)
        if not lab:
            logger.warning(f"Lab {lab_name} not found")
            raise LabNotFoundError(lab_name, owner_id)
        return lab
    except Exception as e:
        logger.error(f"Error getting lab: {e}")
        raise

def get_user_labs(db: Session, owner_id: uuid.UUID) -> list[LabResponse]:
    try:
        if not owner_id:
            logger.warning("Owner ID is required")
            raise ValueError("Owner ID is required")
        labs = db.query(Lab).filter(Lab.owner_id == owner_id, Lab.deleted_at == None).all()
        logger.info(f"User {owner_id} has {len(labs)} labs")
        return [LabResponse.model_validate(lab) for lab in labs]
    except Exception as e:
        logger.error(f"Error getting user labs: {e}")
        raise

def update_lab(db: Session, lab_name: str, owner_id: uuid.UUID, lab_in: LabUpdate) -> LabResponse:
    #Validate name
    validate_name(lab_in.name)
    #Validate description
    validate_description(lab_in.description)
    #Check if lab exists
    lab = _active_by_name_owner_id(db, lab_name, owner_id)
    if not lab:
        logger.warning(f"Lab {lab_name} not found")
        raise LabNotFoundError(lab_name, owner_id)
    if lab_in.name:
        lab.name = lab_in.name
    if lab_in.description:
        lab.description = lab_in.description
    try:
        db.commit()
        db.refresh(lab)
        logger.info(f"Lab {lab.id} updated successfully")
        return LabResponse.model_validate(lab)
    except Exception as e:
        logger.error(f"Error updating lab: {e}")
        db.rollback()
        raise

def delete_lab(db: Session, lab_name: str, owner_id: uuid.UUID) -> None:
    lab = _active_by_name_owner_id(db, lab_name, owner_id)
    if not lab:
        logger.warning(f"Lab {lab_name} not found")
        raise LabNotFoundError(lab_name, owner_id)
    try:
        db.delete(lab)
        db.commit()
        logger.info(f"Lab {lab.id} deleted successfully")
    except Exception as e:
        logger.error(f"Error deleting lab: {e}")
        db.rollback()
        raise