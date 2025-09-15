from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


class KgSchemaCreate(BaseModel):
    version: Optional[int] = Field(None, gt=0, description="Schema version number (auto-incremented if not provided)")
    schema_definition: Optional[Dict[str, Any]] = Field(None, description="JSON schema definition")
    description: Optional[str] = Field(None, max_length=2000, description="Schema description")
    is_active: bool = Field(False, description="Whether this schema should be active")


class KgSchemaUpdate(BaseModel):
    description: Optional[str] = Field(None, max_length=2000, description="Schema description")
    schema_definition: Optional[Dict[str, Any]] = Field(None, description="JSON schema definition")


class KgSchemaResponse(BaseModel):
    id: uuid.UUID
    lab_id: uuid.UUID
    version: int
    schema_definition: Optional[Dict[str, Any]]
    description: Optional[str]
    is_active: bool
    created_by: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class KgSchemaListResponse(BaseModel):
    schemas: List[KgSchemaResponse]
    total: int
    page: int
    limit: int
    has_next: bool
    has_prev: bool


class KgSchemaValidationRequest(BaseModel):
    schema_definition: Dict[str, Any] = Field(..., description="Schema definition to validate")


class KgSchemaValidationResponse(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    summary: Dict[str, Any] = Field(default_factory=dict)


class KgSchemaDiffRequest(BaseModel):
    against: str = Field(..., description="Version number or schema ID to compare against")


class KgSchemaDiffResponse(BaseModel):
    added_nodes: List[str] = Field(default_factory=list)
    removed_nodes: List[str] = Field(default_factory=list)
    modified_nodes: List[str] = Field(default_factory=list)
    added_relationships: List[str] = Field(default_factory=list)
    removed_relationships: List[str] = Field(default_factory=list)
    modified_relationships: List[str] = Field(default_factory=list)
    breaking_changes: List[str] = Field(default_factory=list)


class KgSchemaMigrateRequest(BaseModel):
    dry_run: bool = Field(True, description="Whether to perform a dry run")


class KgSchemaMigrateResponse(BaseModel):
    job_id: uuid.UUID
    dry_run: bool
    estimated_changes: Dict[str, Any] = Field(default_factory=dict)


class KgSchemaCloneRequest(BaseModel):
    description: Optional[str] = Field(None, max_length=2000, description="Description for the cloned schema")


class KgSchemaImportRequest(BaseModel):
    schema_data: Dict[str, Any] = Field(..., description="Schema data to import")
    description: Optional[str] = Field(None, max_length=2000, description="Description for the imported schema")
    version: Optional[int] = Field(None, gt=0, description="Version number for the imported schema")


class KgSchemaUsageResponse(BaseModel):
    active_connections: List[Dict[str, Any]] = Field(default_factory=list)
    migration_jobs: List[Dict[str, Any]] = Field(default_factory=list)
    usage_stats: Dict[str, Any] = Field(default_factory=dict)
