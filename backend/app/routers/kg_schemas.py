from typing import Annotated, Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uuid

from app.db.session import get_db
from app.dependencies import get_current_active_user, get_lab_by_id, require_lab_admin
from app.models import User, Lab
from app.services.kg_schema import KgSchemaService
from app.schemas.kg_schema import (
    KgSchemaCreate, KgSchemaUpdate, KgSchemaResponse, KgSchemaListResponse,
    KgSchemaValidationRequest, KgSchemaValidationResponse,
    KgSchemaDiffRequest, KgSchemaDiffResponse,
    KgSchemaMigrateRequest, KgSchemaMigrateResponse,
    KgSchemaCloneRequest, KgSchemaImportRequest,
    KgSchemaUsageResponse
)
from app.utils.exceptions import NotFoundError, ConflictError, AuthorizationError, ValidationError

router = APIRouter(prefix="/v1", tags=["KG Schemas"])


# Lab-scoped endpoints
@router.post("/labs/{lab_id}/kg-schemas", response_model=KgSchemaResponse, status_code=status.HTTP_201_CREATED)
async def create_kg_schema(
    lab_id: uuid.UUID,
    request: KgSchemaCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    response: Response
):
    """Create a new KG schema version for lab"""
    try:
        service = KgSchemaService(db)
        schema = await service.create_schema(current_user.id, lab_id, request)
        
        # Set Location header
        response.headers["Location"] = f"/v1/kg-schemas/{schema.id}"
        
        return schema
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/labs/{lab_id}/kg-schemas", response_model=KgSchemaListResponse)
async def get_lab_kg_schemas(
    lab_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    q: Optional[str] = Query(None, description="Search query for description or version"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort: str = Query("created_at", description="Sort field: created_at, updated_at, version"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
):
    """List KG schemas for a lab"""
    try:
        service = KgSchemaService(db)
        return await service.get_lab_schemas(
            user_id=current_user.id,
            lab_id=lab_id,
            is_active=is_active,
            q=q,
            page=page,
            limit=limit,
            sort=sort,
            order=order
        )
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/labs/{lab_id}/kg-schemas/active", response_model=KgSchemaResponse)
async def get_active_kg_schema(
    lab_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Get active KG schema for lab"""
    try:
        service = KgSchemaService(db)
        schema = await service.get_active_schema(current_user.id, lab_id)
        if not schema:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active schema found")
        return schema
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/labs/{lab_id}/kg-schemas/{schema_id}/activate", response_model=KgSchemaResponse)
async def activate_kg_schema(
    lab_id: uuid.UUID,
    schema_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Activate a KG schema for the lab (Admin only)"""
    try:
        service = KgSchemaService(db)
        return await service.activate_schema(current_user.id, lab_id, schema_id)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/labs/{lab_id}/kg-schemas:import", response_model=KgSchemaResponse, status_code=status.HTTP_201_CREATED)
async def import_kg_schema(
    lab_id: uuid.UUID,
    request: KgSchemaImportRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Import KG schema from JSON data"""
    try:
        service = KgSchemaService(db)
        return await service.import_schema(current_user.id, lab_id, request)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


# Schema-specific endpoints
@router.get("/kg-schemas/{schema_id}", response_model=KgSchemaResponse)
async def get_kg_schema(
    schema_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    expand: Optional[str] = Query(None, description="Comma-separated list of fields to expand: usage,diff_target")
):
    """Get KG schema details with optional expansions"""
    try:
        service = KgSchemaService(db)
        expand_list = expand.split(",") if expand else None
        return await service.get_schema_by_id(current_user.id, schema_id, expand_list)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/kg-schemas/{schema_id}", response_model=KgSchemaResponse)
async def update_kg_schema(
    schema_id: uuid.UUID,
    request: KgSchemaUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Update KG schema description/definition (Editor+ only)"""
    try:
        service = KgSchemaService(db)
        return await service.update_schema(current_user.id, schema_id, request)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.delete("/kg-schemas/{schema_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kg_schema(
    schema_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    force: bool = Query(False, description="Force delete even if active or referenced")
):
    """Delete KG schema (Admin only)"""
    try:
        service = KgSchemaService(db)
        await service.delete_schema(current_user.id, schema_id, force)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/kg-schemas/{schema_id}/validate", response_model=KgSchemaValidationResponse)
async def validate_kg_schema(
    schema_id: uuid.UUID,
    request: KgSchemaValidationRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Validate KG schema definition (Editor+ only)"""
    try:
        service = KgSchemaService(db)
        return await service.validate_schema(current_user.id, schema_id, request)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/kg-schemas/{schema_id}/diff", response_model=KgSchemaDiffResponse)
async def get_kg_schema_diff(
    schema_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    against: str = Query(..., description="Version number or schema ID to compare against")
):
    """Compare KG schemas (Editor+ only)"""
    try:
        service = KgSchemaService(db)
        request = KgSchemaDiffRequest(against=against)
        return await service.get_schema_diff(current_user.id, schema_id, request)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/kg-schemas/{schema_id}/migrate", response_model=KgSchemaMigrateResponse, status_code=status.HTTP_202_ACCEPTED)
async def migrate_kg_schema(
    schema_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    dry_run: bool = Query(True, description="Whether to perform a dry run")
):
    """Create migration job for KG schema (Admin or Editor+ with run_jobs permission)"""
    try:
        service = KgSchemaService(db)
        request = KgSchemaMigrateRequest(dry_run=dry_run)
        return await service.migrate_schema(current_user.id, schema_id, request)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/kg-schemas/{schema_id}/clone", response_model=KgSchemaResponse, status_code=status.HTTP_201_CREATED)
async def clone_kg_schema(
    schema_id: uuid.UUID,
    request: KgSchemaCloneRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Clone KG schema to new version (Editor+ only)"""
    try:
        service = KgSchemaService(db)
        return await service.clone_schema(current_user.id, schema_id, request)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/kg-schemas/{schema_id}:export")
async def export_kg_schema(
    schema_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Export KG schema as JSON"""
    try:
        service = KgSchemaService(db)
        schema_data = await service.export_schema(current_user.id, schema_id)
        
        return JSONResponse(
            content=schema_data,
            headers={
                "Content-Disposition": f"attachment; filename=kg_schema_{schema_id}.json"
            }
        )
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
