from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
import uuid

from app.models import Lab, LabMember, User, KgSchema, Neo4jConnection, ProcessingJob
from app.schemas.neo4j_connection import (
    Neo4jConnectionCreate, Neo4jConnectionUpdate, Neo4jConnectionResponse, Neo4jConnectionListResponse,
    Neo4jConnectionTestRequest, Neo4jConnectionTestResponse,
    Neo4jConnectionHealthResponse,
    Neo4jConnectionSyncRequest, Neo4jConnectionSyncResponse,
    Neo4jConnectionRotateSecretRequest, Neo4jConnectionRotateSecretResponse
)
from app.utils.exceptions import NotFoundError, ConflictError, AuthorizationError, ValidationError
from app.utils.permissions import LabPermissions


class Neo4jConnectionService:
    def __init__(self, db: Session):
        self.db = db

    async def create_connection(self, user_id: uuid.UUID, lab_id: uuid.UUID, request: Neo4jConnectionCreate) -> Neo4jConnectionResponse:
        """Create a new Neo4j connection"""
        # Check permissions - only admin can create connections
        user_role = await self._get_user_role_in_lab(user_id, lab_id)
        if not LabPermissions.is_admin_role(user_role):
            raise AuthorizationError("Only lab admins can create Neo4j connections")

        # Get lab to verify it exists
        lab = await self._get_lab_or_raise(lab_id)

        # Check for duplicate connection name
        existing = self.db.query(Neo4jConnection).filter(
            and_(Neo4jConnection.lab_id == lab_id, Neo4jConnection.connection_name == request.connection_name)
        ).first()
        if existing:
            raise ConflictError(f"Connection with name '{request.connection_name}' already exists")

        # Validate schema_id if provided
        if request.schema_id:
            schema = self.db.query(KgSchema).filter(
                and_(KgSchema.id == request.schema_id, KgSchema.lab_id == lab_id)
            ).first()
            if not schema:
                raise NotFoundError("Schema not found or doesn't belong to this lab")
            schema_id = request.schema_id
        else:
            # Use active schema if available
            active_schema = self.db.query(KgSchema).filter(
                and_(KgSchema.lab_id == lab_id, KgSchema.is_active == True)
            ).first()
            if not active_schema:
                raise ValidationError("No schema specified and no active schema found")
            schema_id = active_schema.id

        # Create connection
        connection = Neo4jConnection(
            lab_id=lab_id,
            connection_name=request.connection_name,
            uri=request.uri,
            database_name=request.database_name,
            username=request.username,
            secret_id=request.secret_id,
            namespace=request.namespace or "default",
            schema_id=schema_id,
            is_active=True  # Default to active, but only one can be active per lab
        )

        self.db.add(connection)
        self.db.commit()
        self.db.refresh(connection)

        return Neo4jConnectionResponse.from_orm(connection)

    async def get_lab_connections(
        self,
        user_id: uuid.UUID,
        lab_id: uuid.UUID,
        q: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
        sort: str = "created_at",
        order: str = "desc",
        is_active: Optional[bool] = None
    ) -> Neo4jConnectionListResponse:
        """Get connections for a lab"""
        # Check lab access
        if not await self._user_has_lab_access(user_id, lab_id):
            raise AuthorizationError("Access denied")

        # Build query
        query = self.db.query(Neo4jConnection).filter(Neo4jConnection.lab_id == lab_id)

        # Apply filters
        if is_active is not None:
            query = query.filter(Neo4jConnection.is_active == is_active)

        if q:
            search_filter = or_(
                Neo4jConnection.connection_name.ilike(f"%{q}%"),
                Neo4jConnection.uri.ilike(f"%{q}%"),
                Neo4jConnection.database_name.ilike(f"%{q}%")
            )
            query = query.filter(search_filter)

        # Apply sorting
        sort_column = getattr(Neo4jConnection, sort, Neo4jConnection.created_at)
        if order.lower() == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * limit
        connections = query.offset(offset).limit(limit).all()

        # Calculate pagination info
        has_next = offset + limit < total
        has_prev = page > 1

        return Neo4jConnectionListResponse(
            connections=[Neo4jConnectionResponse.from_orm(conn) for conn in connections],
            total=total,
            page=page,
            limit=limit,
            has_next=has_next,
            has_prev=has_prev
        )

    async def get_connection_by_id(self, user_id: uuid.UUID, connection_id: uuid.UUID) -> Neo4jConnectionResponse:
        """Get connection by ID"""
        connection = self.db.query(Neo4jConnection).filter(Neo4jConnection.id == connection_id).first()
        if not connection:
            raise NotFoundError("Connection not found")

        # Check lab access
        if not await self._user_has_lab_access(user_id, connection.lab_id):
            raise AuthorizationError("Access denied")

        return Neo4jConnectionResponse.from_orm(connection)

    async def update_connection(
        self,
        user_id: uuid.UUID,
        connection_id: uuid.UUID,
        request: Neo4jConnectionUpdate
    ) -> Neo4jConnectionResponse:
        """Update connection"""
        connection = self.db.query(Neo4jConnection).filter(Neo4jConnection.id == connection_id).first()
        if not connection:
            raise NotFoundError("Connection not found")

        # Check permissions - only admin can update
        user_role = await self._get_user_role_in_lab(user_id, connection.lab_id)
        if not LabPermissions.is_admin_role(user_role):
            raise AuthorizationError("Only lab admins can update connections")

        # Check for name conflicts if changing name
        if request.connection_name and request.connection_name != connection.connection_name:
            existing = self.db.query(Neo4jConnection).filter(
                and_(
                    Neo4jConnection.lab_id == connection.lab_id,
                    Neo4jConnection.connection_name == request.connection_name,
                    Neo4jConnection.id != connection_id
                )
            ).first()
            if existing:
                raise ConflictError(f"Connection with name '{request.connection_name}' already exists")

        # Validate schema_id if provided
        if request.schema_id:
            schema = self.db.query(KgSchema).filter(
                and_(KgSchema.id == request.schema_id, KgSchema.lab_id == connection.lab_id)
            ).first()
            if not schema:
                raise NotFoundError("Schema not found or doesn't belong to this lab")

        # Update fields
        if request.connection_name is not None:
            connection.connection_name = request.connection_name
        if request.uri is not None:
            connection.uri = request.uri
        if request.database_name is not None:
            connection.database_name = request.database_name
        if request.username is not None:
            connection.username = request.username
        if request.secret_id is not None:
            connection.secret_id = request.secret_id
        if request.namespace is not None:
            connection.namespace = request.namespace
        if request.schema_id is not None:
            connection.schema_id = request.schema_id

        connection.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(connection)

        return Neo4jConnectionResponse.from_orm(connection)

    async def delete_connection(
        self,
        user_id: uuid.UUID,
        connection_id: uuid.UUID,
        force: bool = False
    ) -> None:
        """Delete connection"""
        connection = self.db.query(Neo4jConnection).filter(Neo4jConnection.id == connection_id).first()
        if not connection:
            raise NotFoundError("Connection not found")

        # Check permissions - only admin can delete
        user_role = await self._get_user_role_in_lab(user_id, connection.lab_id)
        if not LabPermissions.is_admin_role(user_role):
            raise AuthorizationError("Only lab admins can delete connections")

        # Check if connection is active
        if not force and connection.is_active:
            # Check if it's the lab's active connection
            lab = self.db.query(Lab).filter(Lab.id == connection.lab_id).first()
            if lab and lab.active_connection_id == connection_id:
                raise ConflictError("Cannot delete active connection. Activate another connection first or use force=true")

        # If force delete and this is lab's active connection, clear it
        if force and connection.is_active:
            lab = self.db.query(Lab).filter(Lab.id == connection.lab_id).first()
            if lab and lab.active_connection_id == connection_id:
                lab.active_connection_id = None
                lab.updated_at = datetime.now(timezone.utc)

        self.db.delete(connection)
        self.db.commit()

    async def activate_connection(
        self,
        user_id: uuid.UUID,
        lab_id: uuid.UUID,
        connection_id: uuid.UUID
    ) -> Neo4jConnectionResponse:
        """Activate a connection for the lab"""
        # Check permissions - admin only
        user_role = await self._get_user_role_in_lab(user_id, lab_id)
        if not LabPermissions.is_admin_role(user_role):
            raise AuthorizationError("Only lab admins can activate connections")

        # Get connection and verify it belongs to the lab
        connection = self.db.query(Neo4jConnection).filter(
            and_(Neo4jConnection.id == connection_id, Neo4jConnection.lab_id == lab_id)
        ).first()
        if not connection:
            raise NotFoundError("Connection not found or doesn't belong to this lab")

        # Get lab
        lab = await self._get_lab_or_raise(lab_id)

        # Check if any index/sync jobs are running
        running_jobs = self.db.query(ProcessingJob).filter(
            and_(
                ProcessingJob.lab_id == lab_id,
                ProcessingJob.job_type.in_(["index_rebuild", "sync"]),
                ProcessingJob.status.in_(["queued", "running"])
            )
        ).count()
        if running_jobs > 0:
            raise ConflictError("Cannot activate connection while index/sync jobs are running")

        # Transaction: deactivate others, activate this one, update lab
        self.db.query(Neo4jConnection).filter(
            and_(Neo4jConnection.lab_id == lab_id, Neo4jConnection.is_active == True)
        ).update({"is_active": False})

        connection.is_active = True
        lab.active_connection_id = connection_id
        lab.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(connection)

        return Neo4jConnectionResponse.from_orm(connection)

    async def test_connection(
        self,
        user_id: uuid.UUID,
        connection_id: uuid.UUID,
        request: Neo4jConnectionTestRequest
    ) -> Neo4jConnectionTestResponse:
        """Test Neo4j connection"""
        connection = self.db.query(Neo4jConnection).filter(Neo4jConnection.id == connection_id).first()
        if not connection:
            raise NotFoundError("Connection not found")

        # Check permissions - admin can test
        user_role = await self._get_user_role_in_lab(user_id, connection.lab_id)
        if not LabPermissions.is_admin_role(user_role):
            raise AuthorizationError("Only lab admins can test connections")

        # TODO: Implement actual Neo4j connection testing
        # This would involve:
        # 1. Retrieving secret from secure storage using secret_id
        # 2. Creating Neo4j driver connection
        # 3. Testing read/write/procedure permissions
        # 4. Measuring latency
        
        # Mock implementation for now
        return Neo4jConnectionTestResponse(
            success=True,
            connection_status="connected",
            read_test={"status": "passed", "latency_ms": 25.5} if request.test_read else None,
            write_test={"status": "passed", "latency_ms": 45.2} if request.test_write else None,
            procedure_test={"status": "passed", "procedures_found": 15} if request.test_procedures else None,
            latency_ms=35.0
        )

    async def get_connection_health(
        self,
        user_id: uuid.UUID,
        connection_id: uuid.UUID
    ) -> Neo4jConnectionHealthResponse:
        """Get connection health status"""
        connection = self.db.query(Neo4jConnection).filter(Neo4jConnection.id == connection_id).first()
        if not connection:
            raise NotFoundError("Connection not found")

        # Check lab access
        if not await self._user_has_lab_access(user_id, connection.lab_id):
            raise AuthorizationError("Access denied")

        # TODO: Implement actual health checking
        # This would involve periodic health checks stored in database or cache
        
        # Mock implementation for now
        return Neo4jConnectionHealthResponse(
            status="healthy",
            last_check=datetime.now(timezone.utc),
            latency_ms=28.5,
            neo4j_version="5.12.0",
            database_status="online",
            recent_errors=[]
        )

    async def sync_connection(
        self,
        user_id: uuid.UUID,
        connection_id: uuid.UUID,
        request: Neo4jConnectionSyncRequest
    ) -> Neo4jConnectionSyncResponse:
        """Sync connection with schema"""
        connection = self.db.query(Neo4jConnection).filter(Neo4jConnection.id == connection_id).first()
        if not connection:
            raise NotFoundError("Connection not found")

        # Check permissions - admin or editor with run_jobs permission
        user_role = await self._get_user_role_in_lab(user_id, connection.lab_id)
        if not (LabPermissions.is_admin_role(user_role) or LabPermissions.can_run_jobs(user_role)):
            raise AuthorizationError("Insufficient permissions to run sync jobs")

        # Determine sync type
        sync_type = "sync"
        if request.force_rebuild:
            sync_type = "index_rebuild"

        # Create processing job
        job = ProcessingJob(
            lab_id=connection.lab_id,
            job_type=sync_type,
            status="queued",
            input_config={
                "connection_id": str(connection_id),
                "sync_schema": request.sync_schema,
                "sync_indexes": request.sync_indexes,
                "sync_constraints": request.sync_constraints,
                "force_rebuild": request.force_rebuild,
                "user_id": str(user_id)
            }
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        # Update last sync time
        connection.last_sync_at = datetime.now(timezone.utc)
        self.db.commit()

        return Neo4jConnectionSyncResponse(
            job_id=job.id,
            sync_type=sync_type,
            estimated_duration="2-5 minutes"
        )

    async def rebuild_indexes(
        self,
        user_id: uuid.UUID,
        connection_id: uuid.UUID
    ) -> Neo4jConnectionSyncResponse:
        """Rebuild indexes for connection"""
        connection = self.db.query(Neo4jConnection).filter(Neo4jConnection.id == connection_id).first()
        if not connection:
            raise NotFoundError("Connection not found")

        # Check permissions - admin or editor with run_jobs permission
        user_role = await self._get_user_role_in_lab(user_id, connection.lab_id)
        if not (LabPermissions.is_admin_role(user_role) or LabPermissions.can_run_jobs(user_role)):
            raise AuthorizationError("Insufficient permissions to run index rebuild jobs")

        # Create processing job
        job = ProcessingJob(
            lab_id=connection.lab_id,
            job_type="index_rebuild",
            status="queued",
            input_config={
                "connection_id": str(connection_id),
                "rebuild_type": "full",
                "user_id": str(user_id)
            }
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        return Neo4jConnectionSyncResponse(
            job_id=job.id,
            sync_type="index_rebuild",
            estimated_duration="5-15 minutes"
        )

    async def rotate_secret(
        self,
        user_id: uuid.UUID,
        connection_id: uuid.UUID,
        request: Neo4jConnectionRotateSecretRequest
    ) -> Neo4jConnectionRotateSecretResponse:
        """Rotate connection secret"""
        connection = self.db.query(Neo4jConnection).filter(Neo4jConnection.id == connection_id).first()
        if not connection:
            raise NotFoundError("Connection not found")

        # Check permissions - admin only
        user_role = await self._get_user_role_in_lab(user_id, connection.lab_id)
        if not LabPermissions.is_admin_role(user_role):
            raise AuthorizationError("Only lab admins can rotate connection secrets")

        # TODO: Implement actual secret rotation
        # This would involve:
        # 1. Testing new credentials if requested
        # 2. Updating secret in secure storage
        # 3. Updating connection record
        # 4. Testing connection with new credentials
        
        # Mock implementation for now
        test_results = None
        if request.test_before_rotation:
            test_results = {
                "connection_test": "passed",
                "auth_test": "passed",
                "latency_ms": 32.1
            }

        # Update connection with new secret
        connection.secret_id = request.new_secret_id
        connection.updated_at = datetime.now(timezone.utc)
        self.db.commit()

        return Neo4jConnectionRotateSecretResponse(
            success=True,
            message="Secret rotated successfully",
            test_results=test_results
        )

    async def get_active_connection(
        self,
        user_id: uuid.UUID,
        lab_id: uuid.UUID
    ) -> Optional[Neo4jConnectionResponse]:
        """Get active connection for lab"""
        # Check lab access
        if not await self._user_has_lab_access(user_id, lab_id):
            raise AuthorizationError("Access denied")

        connection = self.db.query(Neo4jConnection).filter(
            and_(Neo4jConnection.lab_id == lab_id, Neo4jConnection.is_active == True)
        ).first()

        if not connection:
            return None

        return Neo4jConnectionResponse.from_orm(connection)

    # Private helper methods
    async def _get_lab_or_raise(self, lab_id: uuid.UUID) -> Lab:
        """Get lab or raise NotFoundError"""
        lab = self.db.query(Lab).filter(
            and_(Lab.id == lab_id, Lab.deleted_at.is_(None))
        ).first()
        if not lab:
            raise NotFoundError("Lab not found")
        return lab

    async def _user_has_lab_access(self, user_id: uuid.UUID, lab_id: uuid.UUID) -> bool:
        """Check if user has access to lab"""
        lab = self.db.query(Lab).filter(Lab.id == lab_id).first()
        if not lab:
            return False

        # Check if owner
        if lab.owner_id == user_id:
            return True

        # Check if member
        member = self.db.query(LabMember).filter(
            and_(LabMember.lab_id == lab_id, LabMember.user_id == user_id, LabMember.left_at.is_(None))
        ).first()
        
        return member is not None

    async def _get_user_role_in_lab(self, user_id: uuid.UUID, lab_id: uuid.UUID) -> str:
        """Get user's role in lab"""
        lab = self.db.query(Lab).filter(Lab.id == lab_id).first()
        if not lab:
            raise NotFoundError("Lab not found")

        # Check if owner
        if lab.owner_id == user_id:
            return "owner"

        # Check member role
        member = self.db.query(LabMember).filter(
            and_(LabMember.lab_id == lab_id, LabMember.user_id == user_id, LabMember.left_at.is_(None))
        ).first()
        
        if member:
            return member.role
        
        raise AuthorizationError("User is not a member of this lab")
