from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status, Response
from sqlalchemy.orm import Session
import uuid

from app.db.session import get_db
from app.dependencies import get_current_active_user, get_lab_by_id, require_lab_admin
from app.models import User, Lab
from app.services.neo4j_connection import Neo4jConnectionService
from app.schemas.neo4j_connection import (
    Neo4jConnectionCreate, Neo4jConnectionUpdate, Neo4jConnectionResponse, Neo4jConnectionListResponse,
    Neo4jConnectionTestRequest, Neo4jConnectionTestResponse,
    Neo4jConnectionHealthResponse,
    Neo4jConnectionSyncRequest, Neo4jConnectionSyncResponse,
    Neo4jConnectionRotateSecretRequest, Neo4jConnectionRotateSecretResponse
)
from app.utils.exceptions import NotFoundError, ConflictError, AuthorizationError, ValidationError

router = APIRouter(prefix="/v1", tags=["Neo4j Connections"])


# Lab-scoped endpoints
@router.post("/labs/{lab_id}/neo4j-connections", response_model=Neo4jConnectionResponse, status_code=status.HTTP_201_CREATED)
async def create_neo4j_connection(
    lab_id: uuid.UUID,
    request: Neo4jConnectionCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    response: Response
):
    """Create Neo4j connection configuration for lab (Admin only)"""
    try:
        service = Neo4jConnectionService(db)
        connection = await service.create_connection(current_user.id, lab_id, request)
        
        # Set Location header
        response.headers["Location"] = f"/v1/neo4j-connections/{connection.id}"
        
        return connection
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/labs/{lab_id}/neo4j-connections", response_model=Neo4jConnectionListResponse)
async def get_lab_neo4j_connections(
    lab_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    q: Optional[str] = Query(None, description="Search query for name, URI, or database"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    sort: str = Query("created_at", description="Sort field: created_at, updated_at"),
    order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    is_active: Optional[bool] = Query(None, description="Filter by active status")
):
    """List Neo4j connections for a lab"""
    try:
        service = Neo4jConnectionService(db)
        return await service.get_lab_connections(
            user_id=current_user.id,
            lab_id=lab_id,
            q=q,
            page=page,
            limit=limit,
            sort=sort,
            order=order,
            is_active=is_active
        )
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/labs/{lab_id}/neo4j-connections/active", response_model=Neo4jConnectionResponse)
async def get_active_neo4j_connection(
    lab_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Get active Neo4j connection for lab"""
    try:
        service = Neo4jConnectionService(db)
        connection = await service.get_active_connection(current_user.id, lab_id)
        if not connection:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active connection found")
        return connection
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/labs/{lab_id}/neo4j-connections/{connection_id}/activate", response_model=Neo4jConnectionResponse)
async def activate_neo4j_connection(
    lab_id: uuid.UUID,
    connection_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Activate Neo4j connection for the lab (Admin only)"""
    try:
        service = Neo4jConnectionService(db)
        return await service.activate_connection(current_user.id, lab_id, connection_id)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


# Connection-specific endpoints
@router.get("/neo4j-connections/{connection_id}", response_model=Neo4jConnectionResponse)
async def get_neo4j_connection(
    connection_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Get Neo4j connection details (excludes secret)"""
    try:
        service = Neo4jConnectionService(db)
        return await service.get_connection_by_id(current_user.id, connection_id)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.patch("/neo4j-connections/{connection_id}", response_model=Neo4jConnectionResponse)
async def update_neo4j_connection(
    connection_id: uuid.UUID,
    request: Neo4jConnectionUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Update Neo4j connection (Admin only)"""
    try:
        service = Neo4jConnectionService(db)
        return await service.update_connection(current_user.id, connection_id, request)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.delete("/neo4j-connections/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_neo4j_connection(
    connection_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    force: bool = Query(False, description="Force delete even if active")
):
    """Delete Neo4j connection (Admin only)"""
    try:
        service = Neo4jConnectionService(db)
        await service.delete_connection(current_user.id, connection_id, force)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ConflictError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/neo4j-connections/{connection_id}/test", response_model=Neo4jConnectionTestResponse)
async def test_neo4j_connection(
    connection_id: uuid.UUID,
    request: Neo4jConnectionTestRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Test Neo4j connection (Admin only)"""
    try:
        service = Neo4jConnectionService(db)
        return await service.test_connection(current_user.id, connection_id, request)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.get("/neo4j-connections/{connection_id}/health", response_model=Neo4jConnectionHealthResponse)
async def get_neo4j_connection_health(
    connection_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Get Neo4j connection health status"""
    try:
        service = Neo4jConnectionService(db)
        return await service.get_connection_health(current_user.id, connection_id)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/neo4j-connections/{connection_id}/sync", response_model=Neo4jConnectionSyncResponse, status_code=status.HTTP_202_ACCEPTED)
async def sync_neo4j_connection(
    connection_id: uuid.UUID,
    request: Neo4jConnectionSyncRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Sync Neo4j connection with active schema (Admin or Editor+ with run_jobs permission)"""
    try:
        service = Neo4jConnectionService(db)
        return await service.sync_connection(current_user.id, connection_id, request)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/neo4j-connections/{connection_id}/index-rebuild", response_model=Neo4jConnectionSyncResponse, status_code=status.HTTP_202_ACCEPTED)
async def rebuild_neo4j_indexes(
    connection_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Rebuild indexes for Neo4j connection (Admin or Editor+ with run_jobs permission)"""
    try:
        service = Neo4jConnectionService(db)
        return await service.rebuild_indexes(current_user.id, connection_id)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/neo4j-connections/{connection_id}/rotate-secret", response_model=Neo4jConnectionRotateSecretResponse)
async def rotate_neo4j_connection_secret(
    connection_id: uuid.UUID,
    request: Neo4jConnectionRotateSecretRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)]
):
    """Rotate Neo4j connection secret (Admin only)"""
    try:
        service = Neo4jConnectionService(db)
        return await service.rotate_secret(current_user.id, connection_id, request)
    except AuthorizationError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
