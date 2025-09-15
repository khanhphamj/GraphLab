from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, asc
import uuid
import json

from app.models import Lab, LabMember, User, KgSchema, Neo4jConnection, ProcessingJob
from app.schemas.kg_schema import (
    KgSchemaCreate, KgSchemaUpdate, KgSchemaResponse, KgSchemaListResponse,
    KgSchemaValidationRequest, KgSchemaValidationResponse,
    KgSchemaDiffRequest, KgSchemaDiffResponse,
    KgSchemaMigrateRequest, KgSchemaMigrateResponse,
    KgSchemaCloneRequest, KgSchemaImportRequest,
    KgSchemaUsageResponse
)
from app.utils.exceptions import NotFoundError, ConflictError, AuthorizationError, ValidationError
from app.utils.permissions import LabPermissions


class KgSchemaService:
    def __init__(self, db: Session):
        self.db = db

    async def create_schema(self, user_id: uuid.UUID, lab_id: uuid.UUID, request: KgSchemaCreate) -> KgSchemaResponse:
        """Create a new KG schema version"""
        # Check lab access and permissions
        if not await self._user_can_manage_schemas(user_id, lab_id):
            raise AuthorizationError("Insufficient permissions to create schema")

        # Get lab to verify it exists
        lab = await self._get_lab_or_raise(lab_id)

        # Determine version number
        if request.version is None:
            # Auto-increment version
            max_version = self.db.query(func.max(KgSchema.version)).filter(
                KgSchema.lab_id == lab_id
            ).scalar()
            version = (max_version or 0) + 1
        else:
            # Check if version already exists
            existing = self.db.query(KgSchema).filter(
                and_(KgSchema.lab_id == lab_id, KgSchema.version == request.version)
            ).first()
            if existing:
                raise ConflictError(f"Schema version {request.version} already exists")
            version = request.version

        # Validate schema definition if provided
        if request.schema_definition:
            validation_result = await self._validate_schema_definition(request.schema_definition)
            if not validation_result["is_valid"]:
                raise ValidationError(f"Invalid schema definition: {', '.join(validation_result['errors'])}")

        # Handle activation logic
        if request.is_active:
            # Deactivate other schemas in the lab
            self.db.query(KgSchema).filter(
                and_(KgSchema.lab_id == lab_id, KgSchema.is_active == True)
            ).update({"is_active": False})

        # Create schema
        schema = KgSchema(
            lab_id=lab_id,
            version=version,
            schema_definition=request.schema_definition,
            description=request.description,
            is_active=request.is_active,
            created_by=user_id
        )
        
        self.db.add(schema)
        self.db.commit()
        self.db.refresh(schema)

        # Update lab's active schema if this is active
        if request.is_active:
            lab.active_schema_id = schema.id
            lab.updated_at = datetime.now(timezone.utc)
            self.db.commit()

        return KgSchemaResponse.from_orm(schema)

    async def get_lab_schemas(
        self,
        user_id: uuid.UUID,
        lab_id: uuid.UUID,
        is_active: Optional[bool] = None,
        q: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
        sort: str = "created_at",
        order: str = "desc"
    ) -> KgSchemaListResponse:
        """Get schemas for a lab"""
        # Check lab access
        if not await self._user_has_lab_access(user_id, lab_id):
            raise AuthorizationError("Access denied")

        # Build query
        query = self.db.query(KgSchema).filter(KgSchema.lab_id == lab_id)

        # Apply filters
        if is_active is not None:
            query = query.filter(KgSchema.is_active == is_active)

        if q:
            search_filter = or_(
                KgSchema.description.ilike(f"%{q}%"),
                func.cast(KgSchema.version, str).ilike(f"%{q}%")
            )
            query = query.filter(search_filter)

        # Apply sorting
        sort_column = getattr(KgSchema, sort, KgSchema.created_at)
        if order.lower() == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * limit
        schemas = query.offset(offset).limit(limit).all()

        # Calculate pagination info
        has_next = offset + limit < total
        has_prev = page > 1

        return KgSchemaListResponse(
            schemas=[KgSchemaResponse.from_orm(schema) for schema in schemas],
            total=total,
            page=page,
            limit=limit,
            has_next=has_next,
            has_prev=has_prev
        )

    async def get_schema_by_id(
        self,
        user_id: uuid.UUID,
        schema_id: uuid.UUID,
        expand: Optional[List[str]] = None
    ) -> KgSchemaResponse:
        """Get schema by ID with optional expansions"""
        schema = self.db.query(KgSchema).filter(KgSchema.id == schema_id).first()
        if not schema:
            raise NotFoundError("Schema not found")

        # Check lab access
        if not await self._user_has_lab_access(user_id, schema.lab_id):
            raise AuthorizationError("Access denied")

        response = KgSchemaResponse.from_orm(schema)

        # Handle expansions
        if expand:
            if "usage" in expand:
                usage = await self._get_schema_usage(schema_id)
                response.usage = usage

        return response

    async def update_schema(
        self,
        user_id: uuid.UUID,
        schema_id: uuid.UUID,
        request: KgSchemaUpdate
    ) -> KgSchemaResponse:
        """Update schema description/definition"""
        schema = self.db.query(KgSchema).filter(KgSchema.id == schema_id).first()
        if not schema:
            raise NotFoundError("Schema not found")

        # Check permissions
        if not await self._user_can_manage_schemas(user_id, schema.lab_id):
            raise AuthorizationError("Insufficient permissions to update schema")

        # Validate schema definition if provided
        if request.schema_definition:
            validation_result = await self._validate_schema_definition(request.schema_definition)
            if not validation_result["is_valid"]:
                raise ValidationError(f"Invalid schema definition: {', '.join(validation_result['errors'])}")

        # Update fields
        if request.description is not None:
            schema.description = request.description
        if request.schema_definition is not None:
            schema.schema_definition = request.schema_definition

        self.db.commit()
        self.db.refresh(schema)

        return KgSchemaResponse.from_orm(schema)

    async def delete_schema(
        self,
        user_id: uuid.UUID,
        schema_id: uuid.UUID,
        force: bool = False
    ) -> None:
        """Delete schema"""
        schema = self.db.query(KgSchema).filter(KgSchema.id == schema_id).first()
        if not schema:
            raise NotFoundError("Schema not found")

        # Check permissions - only admin can delete
        user_role = await self._get_user_role_in_lab(user_id, schema.lab_id)
        if not LabPermissions.is_admin_role(user_role):
            raise AuthorizationError("Only lab admins can delete schemas")

        # Check if schema is active or being used
        if not force:
            if schema.is_active:
                raise ConflictError("Cannot delete active schema. Deactivate first or use force=true")
            
            # Check if any connections reference this schema
            connections_count = self.db.query(func.count(Neo4jConnection.id)).filter(
                Neo4jConnection.schema_id == schema_id
            ).scalar()
            if connections_count > 0:
                raise ConflictError("Schema is referenced by Neo4j connections. Remove references first or use force=true")

        # If force delete, update lab's active schema if needed
        if force and schema.is_active:
            lab = self.db.query(Lab).filter(Lab.id == schema.lab_id).first()
            if lab and lab.active_schema_id == schema_id:
                lab.active_schema_id = None
                lab.updated_at = datetime.now(timezone.utc)

        self.db.delete(schema)
        self.db.commit()

    async def activate_schema(
        self,
        user_id: uuid.UUID,
        lab_id: uuid.UUID,
        schema_id: uuid.UUID
    ) -> KgSchemaResponse:
        """Activate a schema for the lab"""
        # Check permissions - admin only
        user_role = await self._get_user_role_in_lab(user_id, lab_id)
        if not LabPermissions.is_admin_role(user_role):
            raise AuthorizationError("Only lab admins can activate schemas")

        # Get schema and verify it belongs to the lab
        schema = self.db.query(KgSchema).filter(
            and_(KgSchema.id == schema_id, KgSchema.lab_id == lab_id)
        ).first()
        if not schema:
            raise NotFoundError("Schema not found or doesn't belong to this lab")

        # Get lab
        lab = await self._get_lab_or_raise(lab_id)

        # Check if any migration jobs are running
        running_jobs = self.db.query(ProcessingJob).filter(
            and_(
                ProcessingJob.lab_id == lab_id,
                ProcessingJob.job_type == "schema_migrate",
                ProcessingJob.status.in_(["queued", "running"])
            )
        ).count()
        if running_jobs > 0:
            raise ConflictError("Cannot activate schema while migration jobs are running")

        # Transaction: deactivate others, activate this one, update lab
        self.db.query(KgSchema).filter(
            and_(KgSchema.lab_id == lab_id, KgSchema.is_active == True)
        ).update({"is_active": False})

        schema.is_active = True
        lab.active_schema_id = schema_id
        lab.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(schema)

        return KgSchemaResponse.from_orm(schema)

    async def validate_schema(
        self,
        user_id: uuid.UUID,
        schema_id: uuid.UUID,
        request: KgSchemaValidationRequest
    ) -> KgSchemaValidationResponse:
        """Validate schema definition"""
        schema = self.db.query(KgSchema).filter(KgSchema.id == schema_id).first()
        if not schema:
            raise NotFoundError("Schema not found")

        # Check permissions
        if not await self._user_can_manage_schemas(user_id, schema.lab_id):
            raise AuthorizationError("Insufficient permissions")

        return await self._validate_schema_definition(request.schema_definition)

    async def get_schema_diff(
        self,
        user_id: uuid.UUID,
        schema_id: uuid.UUID,
        request: KgSchemaDiffRequest
    ) -> KgSchemaDiffResponse:
        """Compare schemas"""
        schema = self.db.query(KgSchema).filter(KgSchema.id == schema_id).first()
        if not schema:
            raise NotFoundError("Schema not found")

        # Check permissions
        if not await self._user_can_manage_schemas(user_id, schema.lab_id):
            raise AuthorizationError("Insufficient permissions")

        # Get target schema for comparison
        if request.against.isdigit():
            # Compare against version
            target_schema = self.db.query(KgSchema).filter(
                and_(KgSchema.lab_id == schema.lab_id, KgSchema.version == int(request.against))
            ).first()
        else:
            # Compare against schema ID
            try:
                target_id = uuid.UUID(request.against)
                target_schema = self.db.query(KgSchema).filter(KgSchema.id == target_id).first()
            except ValueError:
                raise ValidationError("Invalid schema ID format")

        if not target_schema:
            raise NotFoundError("Target schema not found")

        return await self._compare_schemas(schema.schema_definition, target_schema.schema_definition)

    async def migrate_schema(
        self,
        user_id: uuid.UUID,
        schema_id: uuid.UUID,
        request: KgSchemaMigrateRequest
    ) -> KgSchemaMigrateResponse:
        """Create migration job for schema"""
        schema = self.db.query(KgSchema).filter(KgSchema.id == schema_id).first()
        if not schema:
            raise NotFoundError("Schema not found")

        # Check permissions - admin or editor with run_jobs permission
        user_role = await self._get_user_role_in_lab(user_id, schema.lab_id)
        if not (LabPermissions.is_admin_role(user_role) or LabPermissions.can_run_jobs(user_role)):
            raise AuthorizationError("Insufficient permissions to run migration jobs")

        # Create processing job
        job = ProcessingJob(
            lab_id=schema.lab_id,
            job_type="schema_migrate",
            status="queued",
            input_config={
                "schema_id": str(schema_id),
                "dry_run": request.dry_run,
                "user_id": str(user_id)
            }
        )
        
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        return KgSchemaMigrateResponse(
            job_id=job.id,
            dry_run=request.dry_run,
            estimated_changes={}  # Would be populated by job processor
        )

    async def get_active_schema(
        self,
        user_id: uuid.UUID,
        lab_id: uuid.UUID
    ) -> Optional[KgSchemaResponse]:
        """Get active schema for lab"""
        # Check lab access
        if not await self._user_has_lab_access(user_id, lab_id):
            raise AuthorizationError("Access denied")

        schema = self.db.query(KgSchema).filter(
            and_(KgSchema.lab_id == lab_id, KgSchema.is_active == True)
        ).first()

        if not schema:
            return None

        return KgSchemaResponse.from_orm(schema)

    async def clone_schema(
        self,
        user_id: uuid.UUID,
        schema_id: uuid.UUID,
        request: KgSchemaCloneRequest
    ) -> KgSchemaResponse:
        """Clone schema to new version"""
        schema = self.db.query(KgSchema).filter(KgSchema.id == schema_id).first()
        if not schema:
            raise NotFoundError("Schema not found")

        # Check permissions
        if not await self._user_can_manage_schemas(user_id, schema.lab_id):
            raise AuthorizationError("Insufficient permissions")

        # Get next version number
        max_version = self.db.query(func.max(KgSchema.version)).filter(
            KgSchema.lab_id == schema.lab_id
        ).scalar()
        new_version = (max_version or 0) + 1

        # Create cloned schema
        cloned_schema = KgSchema(
            lab_id=schema.lab_id,
            version=new_version,
            schema_definition=schema.schema_definition,
            description=request.description or f"Cloned from version {schema.version}",
            is_active=False,  # Cloned schemas are never active by default
            created_by=user_id
        )
        
        self.db.add(cloned_schema)
        self.db.commit()
        self.db.refresh(cloned_schema)

        return KgSchemaResponse.from_orm(cloned_schema)

    async def import_schema(
        self,
        user_id: uuid.UUID,
        lab_id: uuid.UUID,
        request: KgSchemaImportRequest
    ) -> KgSchemaResponse:
        """Import schema from JSON data"""
        # Check permissions
        if not await self._user_can_manage_schemas(user_id, lab_id):
            raise AuthorizationError("Insufficient permissions")

        # Validate imported schema
        validation_result = await self._validate_schema_definition(request.schema_data)
        if not validation_result["is_valid"]:
            raise ValidationError(f"Invalid schema data: {', '.join(validation_result['errors'])}")

        # Determine version
        if request.version:
            # Check if version exists
            existing = self.db.query(KgSchema).filter(
                and_(KgSchema.lab_id == lab_id, KgSchema.version == request.version)
            ).first()
            if existing:
                raise ConflictError(f"Schema version {request.version} already exists")
            version = request.version
        else:
            # Auto-increment
            max_version = self.db.query(func.max(KgSchema.version)).filter(
                KgSchema.lab_id == lab_id
            ).scalar()
            version = (max_version or 0) + 1

        # Create imported schema
        imported_schema = KgSchema(
            lab_id=lab_id,
            version=version,
            schema_definition=request.schema_data,
            description=request.description or f"Imported schema version {version}",
            is_active=False,
            created_by=user_id
        )
        
        self.db.add(imported_schema)
        self.db.commit()
        self.db.refresh(imported_schema)

        return KgSchemaResponse.from_orm(imported_schema)

    async def export_schema(
        self,
        user_id: uuid.UUID,
        schema_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Export schema as JSON"""
        schema = self.db.query(KgSchema).filter(KgSchema.id == schema_id).first()
        if not schema:
            raise NotFoundError("Schema not found")

        # Check permissions
        if not await self._user_has_lab_access(user_id, schema.lab_id):
            raise AuthorizationError("Access denied")

        return {
            "version": schema.version,
            "description": schema.description,
            "schema_definition": schema.schema_definition,
            "created_at": schema.created_at.isoformat(),
            "export_metadata": {
                "exported_by": str(user_id),
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "lab_id": str(schema.lab_id)
            }
        }

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

    async def _user_can_manage_schemas(self, user_id: uuid.UUID, lab_id: uuid.UUID) -> bool:
        """Check if user can manage schemas"""
        try:
            role = await self._get_user_role_in_lab(user_id, lab_id)
            return LabPermissions.can_manage_schemas(role)
        except (NotFoundError, AuthorizationError):
            return False

    async def _validate_schema_definition(self, schema_def: Dict[str, Any]) -> Dict[str, Any]:
        """Validate schema definition structure"""
        errors = []
        warnings = []
        
        # Basic structure validation
        if not isinstance(schema_def, dict):
            errors.append("Schema definition must be a JSON object")
            return {"is_valid": False, "errors": errors, "warnings": warnings, "summary": {}}

        # Check for required sections
        required_sections = ["nodes", "relationships"]
        for section in required_sections:
            if section not in schema_def:
                errors.append(f"Missing required section: {section}")

        # Validate nodes
        nodes = schema_def.get("nodes", {})
        if not isinstance(nodes, dict):
            errors.append("Nodes section must be an object")
        else:
            for node_name, node_def in nodes.items():
                if not isinstance(node_def, dict):
                    errors.append(f"Node '{node_name}' definition must be an object")
                    continue
                
                # Check for required properties
                if "properties" not in node_def:
                    warnings.append(f"Node '{node_name}' has no properties defined")

        # Validate relationships
        relationships = schema_def.get("relationships", {})
        if not isinstance(relationships, dict):
            errors.append("Relationships section must be an object")
        else:
            for rel_name, rel_def in relationships.items():
                if not isinstance(rel_def, dict):
                    errors.append(f"Relationship '{rel_name}' definition must be an object")
                    continue

        summary = {
            "node_count": len(nodes) if isinstance(nodes, dict) else 0,
            "relationship_count": len(relationships) if isinstance(relationships, dict) else 0
        }

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "summary": summary
        }

    async def _compare_schemas(self, schema1: Dict[str, Any], schema2: Dict[str, Any]) -> KgSchemaDiffResponse:
        """Compare two schema definitions"""
        # Simple diff implementation - can be enhanced
        schema1 = schema1 or {}
        schema2 = schema2 or {}
        
        nodes1 = set((schema1.get("nodes", {})).keys())
        nodes2 = set((schema2.get("nodes", {})).keys())
        
        rels1 = set((schema1.get("relationships", {})).keys())
        rels2 = set((schema2.get("relationships", {})).keys())
        
        return KgSchemaDiffResponse(
            added_nodes=list(nodes1 - nodes2),
            removed_nodes=list(nodes2 - nodes1),
            modified_nodes=[],  # Would need deeper comparison
            added_relationships=list(rels1 - rels2),
            removed_relationships=list(rels2 - rels1),
            modified_relationships=[],  # Would need deeper comparison
            breaking_changes=[]  # Would need analysis of property changes
        )

    async def _get_schema_usage(self, schema_id: uuid.UUID) -> KgSchemaUsageResponse:
        """Get schema usage information"""
        # Get connections using this schema
        connections = self.db.query(Neo4jConnection).filter(
            Neo4jConnection.schema_id == schema_id
        ).all()

        # Get related migration jobs
        migration_jobs = self.db.query(ProcessingJob).filter(
            and_(
                ProcessingJob.job_type == "schema_migrate",
                ProcessingJob.input_config.contains({"schema_id": str(schema_id)})
            )
        ).all()

        return KgSchemaUsageResponse(
            active_connections=[{
                "id": str(conn.id),
                "name": conn.connection_name,
                "is_active": conn.is_active
            } for conn in connections],
            migration_jobs=[{
                "id": str(job.id),
                "status": job.status,
                "created_at": job.created_at.isoformat()
            } for job in migration_jobs],
            usage_stats={
                "connection_count": len(connections),
                "active_connection_count": len([c for c in connections if c.is_active]),
                "migration_count": len(migration_jobs)
            }
        )
