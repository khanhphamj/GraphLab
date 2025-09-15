from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import uuid


class Neo4jConnectionCreate(BaseModel):
    connection_name: str = Field(..., min_length=1, max_length=255, description="Human-readable connection name")
    uri: str = Field(..., description="Neo4j connection URI (e.g., bolt://localhost:7687)")
    database_name: str = Field(..., min_length=1, max_length=255, description="Neo4j database name")
    username: str = Field(..., min_length=1, max_length=255, description="Neo4j username")
    secret_id: str = Field(..., description="Reference to stored password/secret")
    namespace: Optional[str] = Field("default", max_length=255, description="Neo4j namespace")
    schema_id: Optional[uuid.UUID] = Field(None, description="Associated KG schema ID (uses active schema if not provided)")


class Neo4jConnectionUpdate(BaseModel):
    connection_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Human-readable connection name")
    uri: Optional[str] = Field(None, description="Neo4j connection URI")
    database_name: Optional[str] = Field(None, min_length=1, max_length=255, description="Neo4j database name")
    username: Optional[str] = Field(None, min_length=1, max_length=255, description="Neo4j username")
    secret_id: Optional[str] = Field(None, description="Reference to stored password/secret")
    namespace: Optional[str] = Field(None, max_length=255, description="Neo4j namespace")
    schema_id: Optional[uuid.UUID] = Field(None, description="Associated KG schema ID")


class Neo4jConnectionResponse(BaseModel):
    id: uuid.UUID
    lab_id: uuid.UUID
    connection_name: str
    uri: str
    database_name: str
    username: str
    namespace: str
    schema_id: uuid.UUID
    is_active: bool
    last_sync_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # Note: secret_id is intentionally excluded for security

    class Config:
        from_attributes = True


class Neo4jConnectionListResponse(BaseModel):
    connections: List[Neo4jConnectionResponse]
    total: int
    page: int
    limit: int
    has_next: bool
    has_prev: bool


class Neo4jConnectionTestRequest(BaseModel):
    test_read: bool = Field(True, description="Test read permissions")
    test_write: bool = Field(True, description="Test write permissions")
    test_procedures: bool = Field(True, description="Test procedure execution")


class Neo4jConnectionTestResponse(BaseModel):
    success: bool
    connection_status: str
    read_test: Optional[Dict[str, Any]] = None
    write_test: Optional[Dict[str, Any]] = None
    procedure_test: Optional[Dict[str, Any]] = None
    error_details: Optional[str] = None
    latency_ms: Optional[float] = None


class Neo4jConnectionHealthResponse(BaseModel):
    status: str  # healthy, degraded, unhealthy
    last_check: datetime
    latency_ms: Optional[float] = None
    neo4j_version: Optional[str] = None
    database_status: Optional[str] = None
    recent_errors: List[str] = Field(default_factory=list)


class Neo4jConnectionSyncRequest(BaseModel):
    force_rebuild: bool = Field(False, description="Force rebuild indexes and constraints")
    sync_schema: bool = Field(True, description="Sync schema definitions")
    sync_indexes: bool = Field(True, description="Sync indexes")
    sync_constraints: bool = Field(True, description="Sync constraints")


class Neo4jConnectionSyncResponse(BaseModel):
    job_id: uuid.UUID
    sync_type: str
    estimated_duration: Optional[str] = None


class Neo4jConnectionRotateSecretRequest(BaseModel):
    new_secret_id: str = Field(..., description="New secret ID reference")
    test_before_rotation: bool = Field(True, description="Test new credentials before rotation")


class Neo4jConnectionRotateSecretResponse(BaseModel):
    success: bool
    message: str
    test_results: Optional[Dict[str, Any]] = None
