# GraphLab Database Schema Documentation

## Overview

GraphLab is a research lab management platform that integrates traditional relational data with Neo4j graph databases for knowledge graph management. The system supports collaborative research workflows, paper analysis, and graph-based data exploration.

The database uses PostgreSQL with SQLAlchemy ORM and includes 20 main tables organized around user management, lab collaboration, research content, and system infrastructure.

## Core Architecture

- **Database**: PostgreSQL with UUID primary keys
- **ORM**: SQLAlchemy with type annotations
- **Key Features**:
  - Multi-tenant lab structure
  - Neo4j integration for knowledge graphs
  - Asynchronous job processing
  - Comprehensive audit logging
  - OAuth integration

---

## 1. User Management Tables

### Users Table (`users`)
**Purpose**: Core user accounts for the platform

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | Primary Key | Unique user identifier |
| `name` | String | Not Null | User's display name |
| `email` | String | Not Null, Unique, Indexed | User's email address |
| `hashed_password` | String | Not Null | Bcrypt-hashed password |
| `profile` | JSON | Optional | User profile data |
| `preferences` | JSON | Optional | User preferences/settings |
| `email_verified_at` | DateTime | Optional | Email verification timestamp |
| `created_at` | DateTime | Not Null, Default UTC | Account creation time |
| `updated_at` | DateTime | Not Null, Auto-update | Last update time |
| `deleted_at` | DateTime | Optional | Soft delete timestamp |

**Relationships**:
- One-to-many: labs (as owner), lab_memberships, brainstorm_sessions, kg_schemas, conversations, messages, user_sessions, user_verifications, oauth_accounts, api_keys, audit_logs

### Lab Members Table (`lab_members`)
**Purpose**: Junction table for user-lab memberships with roles

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | Primary Key | Membership identifier |
| `lab_id` | UUID | Foreign Key (labs), Not Null | Reference to lab |
| `user_id` | UUID | Foreign Key (users), Not Null | Reference to user |
| `role` | Enum | Not Null | Member role: owner, admin, editor, viewer |
| `joined_at` | DateTime | Not Null, Default UTC | Membership start time |
| `left_at` | DateTime | Optional | Membership end time |

**Constraints**:
- Unique constraint on (lab_id, user_id)

---

## 2. Lab Management Tables

### Labs Table (`labs`)
**Purpose**: Research lab entities with Neo4j integration

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | Primary Key | Lab identifier |
| `name` | String | Not Null | Lab name |
| `description` | Text | Optional | Lab description |
| `research_domain` | String | Optional | Research focus area |
| `settings` | JSON | Optional | Lab-specific settings |
| `owner_id` | UUID | Foreign Key (users), Not Null | Lab owner |
| `active_connection_id` | UUID | Foreign Key (neo4j_connections) | Current Neo4j connection |
| `active_schema_id` | UUID | Foreign Key (kg_schemas) | Current KG schema |
| `status` | Enum | Not Null, Default 'active' | Lab status: active, archived, suspended |
| `created_at` | DateTime | Not Null, Default UTC | Creation timestamp |
| `updated_at` | DateTime | Not Null, Auto-update | Last update timestamp |
| `deleted_at` | DateTime | Optional | Soft delete timestamp |

**Relationships**:
- Many-to-one: owner (User)
- One-to-many: members, brainstorm_sessions, kg_schemas, neo4j_connections, processing_jobs, research_papers, conversations, audit_logs

### Neo4j Connections Table (`neo4j_connections`)
**Purpose**: Connection configurations for Neo4j databases

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | Primary Key | Connection identifier |
| `lab_id` | UUID | Foreign Key (labs), Not Null | Associated lab |
| `connection_name` | String | Not Null | Human-readable name |
| `uri` | String | Not Null | Neo4j connection URI |
| `database_name` | String | Not Null | Neo4j database name |
| `username` | String | Not Null | Neo4j username |
| `secret_id` | String | Not Null | Reference to stored password |
| `schema_id` | UUID | Foreign Key (kg_schemas), Not Null | Associated KG schema |
| `is_active` | Boolean | Not Null, Default True | Connection active status |
| `last_sync_at` | DateTime | Optional | Last synchronization time |
| `created_at` | DateTime | Not Null, Default UTC | Creation timestamp |
| `updated_at` | DateTime | Not Null, Auto-update | Last update timestamp |

**Constraints**:
- Unique constraint on (lab_id, connection_name)

### KG Schemas Table (`kg_schemas`)
**Purpose**: Knowledge graph schema definitions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | Primary Key | Schema identifier |
| `lab_id` | UUID | Foreign Key (labs), Not Null | Associated lab |
| `version` | Integer | Not Null | Schema version number |
| `schema_definition` | JSON | Optional | Schema structure definition |
| `description` | Text | Optional | Schema description |
| `is_active` | Boolean | Not Null, Default False | Schema active status |
| `created_by` | UUID | Foreign Key (users), Not Null | Schema creator |
| `created_at` | DateTime | Not Null, Default UTC | Creation timestamp |

**Constraints**:
- Unique constraint on (lab_id, version)
- Check constraint: version > 0

---

## 3. Research Content Tables

### Research Papers Table (`research_papers`)
**Purpose**: Academic papers with metadata and processing status

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | Primary Key | Paper identifier |
| `lab_id` | UUID | Foreign Key (labs), Not Null | Associated lab |
| `arxiv_id` | String | Optional | ArXiv identifier |
| `doi` | String | Optional | Digital Object Identifier |
| `title` | Text | Not Null | Paper title |
| `authors` | Array(String) | Optional | List of authors |
| `abstract` | Text | Not Null | Paper abstract |
| `pdf_url` | Text | Optional | PDF download URL |
| `neo4j_uuid` | UUID | Optional | Neo4j node identifier |
| `processing_status` | Enum | Not Null, Default 'pending' | Processing status |
| `keywords_matched` | Array(String) | Optional | Matched research keywords |
| `published_date` | Date | Optional | Publication date |
| `crawled_at` | DateTime | Optional | Crawling timestamp |
| `processed_at` | DateTime | Optional | Processing completion time |

**Constraints**:
- Unique constraint on (lab_id, arxiv_id)
- Unique constraint on (lab_id, doi)

### Paper Analysis Table (`paper_analysis`)
**Purpose**: Analysis results for research papers

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | Primary Key | Analysis identifier |
| `paper_id` | UUID | Foreign Key (research_papers), Not Null | Associated paper |
| `analysis_type` | Enum | Not Null | Type of analysis performed |
| `result_data` | JSON | Optional | Analysis results |
| `confidence_score` | Numeric | Optional | Analysis confidence score |
| `model_used` | String | Optional | ML model identifier |
| `created_at` | DateTime | Not Null, Default UTC | Analysis timestamp |

**Analysis Types**: entity_extraction, relation_extraction, topic_modeling, citation_analysis

---

## 4. Collaboration Tables

### Conversations Table (`conversations`)
**Purpose**: Chat conversations within labs

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | Primary Key | Conversation identifier |
| `lab_id` | UUID | Foreign Key (labs), Not Null | Associated lab |
| `owner_id` | UUID | Foreign Key (users), Not Null | Conversation owner |
| `title` | String | Not Null | Conversation title |
| `conversation_type` | Enum | Not Null | Type of conversation |
| `active_filters` | JSON | Optional | Active data filters |
| `query_history` | JSON | Optional | Query history |
| `created_at` | DateTime | Not Null, Default UTC | Creation timestamp |
| `updated_at` | DateTime | Not Null, Auto-update | Last update timestamp |
| `deleted_at` | DateTime | Optional | Soft delete timestamp |

**Conversation Types**: research_chat, schema_design, data_exploration

### Messages Table (`messages`)
**Purpose**: Individual messages within conversations

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | Primary Key | Message identifier |
| `conversation_id` | UUID | Foreign Key (conversations), Not Null | Parent conversation |
| `sender_id` | UUID | Foreign Key (users), Not Null | Message sender |
| `role` | Enum | Not Null | Sender role: system, user, assistant, tool |
| `content` | Text | Not Null | Message content |
| `message_type` | Enum | Not Null | Message type |
| `tool_calls` | JSON | Optional | Tool call information |
| `neo4j_refs` | JSON | Optional | Neo4j reference data |
| `parent_message_id` | UUID | Foreign Key (messages) | Parent message for threading |
| `thread_position` | Integer | Not Null, Default 0 | Position in thread |
| `seq` | BigInteger | Not Null | Sequence number |
| `created_at` | DateTime | Not Null, Default UTC | Creation timestamp |
| `updated_at` | DateTime | Not Null, Auto-update | Last update timestamp |

**Message Types**: text, query_result, schema_suggestion, error

### Brainstorm Sessions Table (`brainstorm_sessions`)
**Purpose**: Collaborative brainstorming sessions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | Primary Key | Session identifier |
| `lab_id` | UUID | Foreign Key (labs), Not Null | Associated lab |
| `created_by` | UUID | Foreign Key (users), Not Null | Session creator |
| `title` | String | Not Null | Session title |
| `description` | Text | Optional | Session description |
| `status` | Enum | Not Null, Default 'active' | Session status |
| `session_data` | JSON | Optional | Session data and state |
| `created_at` | DateTime | Not Null, Default UTC | Creation timestamp |
| `updated_at` | DateTime | Not Null, Auto-update | Last update timestamp |
| `deleted_at` | DateTime | Optional | Soft delete timestamp |

**Session Status**: active, completed, archived

### Research Keywords Table (`research_keywords`)
**Purpose**: Keywords associated with research sessions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | Primary Key | Keyword identifier |
| `session_id` | UUID | Foreign Key (brainstorm_sessions), Not Null | Associated session |
| `term` | String | Not Null | Keyword term |
| `weight` | Numeric | Optional | Keyword importance weight |
| `source` | Enum | Not Null | Keyword source |
| `rationale` | Text | Optional | Keyword rationale |
| `is_primary` | Boolean | Not Null, Default False | Primary keyword flag |
| `created_at` | DateTime | Not Null, Default UTC | Creation timestamp |

**Sources**: user, ai, imported

---

## 5. Processing Infrastructure Tables

### Processing Jobs Table (`processing_jobs`)
**Purpose**: Background job processing system

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | Primary Key | Job identifier |
| `lab_id` | UUID | Foreign Key (labs), Not Null | Associated lab |
| `job_type` | Enum | Not Null | Type of processing job |
| `status` | Enum | Not Null, Default 'queued' | Job status |
| `priority` | Integer | Not Null, Default 0 | Job priority |
| `attempts` | Integer | Not Null, Default 0 | Number of attempts |
| `max_attempts` | Integer | Not Null, Default 3 | Maximum retry attempts |
| `queue` | String | Optional | Job queue name |
| `worker_id` | String | Optional | Worker processing the job |
| `input_config` | JSON | Optional | Job input configuration |
| `output_result` | JSON | Optional | Job output results |
| `error_details` | JSON | Optional | Error information |
| `progress_percent` | Integer | Optional | Progress percentage |
| `processed_items` | Integer | Not Null, Default 0 | Items processed |
| `total_items` | Integer | Optional | Total items to process |
| `retry_at` | DateTime | Optional | Next retry time |
| `started_at` | DateTime | Optional | Job start time |
| `completed_at` | DateTime | Optional | Job completion time |
| `created_at` | DateTime | Not Null, Default UTC | Creation timestamp |
| `updated_at` | DateTime | Not Null, Auto-update | Last update timestamp |

**Job Types**: paper_crawl, paper_process, entity_extract, vector_embed, kg_upsert, schema_migrate, index_rebuild, data_export
**Job Status**: queued, running, completed, failed, cancelled

### Job Steps Table (`job_steps`)
**Purpose**: Individual steps within processing jobs

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | Primary Key | Step identifier |
| `job_id` | UUID | Foreign Key (processing_jobs), Not Null | Parent job |
| `step_name` | String | Not Null | Step name |
| `step_order` | Integer | Not Null | Execution order |
| `status` | Enum | Not Null, Default 'pending' | Step status |
| `input_data` | JSON | Optional | Step input data |
| `output_data` | JSON | Optional | Step output data |
| `error_message` | Text | Optional | Error message |
| `started_at` | DateTime | Optional | Step start time |
| `completed_at` | DateTime | Optional | Step completion time |

**Constraints**:
- Unique constraint on (job_id, step_order)
- Check constraint: step_order > 0
**Step Status**: pending, running, completed, failed, skipped

---

## 6. Authentication & Security Tables

### User Sessions Table (`user_sessions`)
**Purpose**: User authentication sessions

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | Primary Key | Session identifier |
| `user_id` | UUID | Foreign Key (users), Not Null | Associated user |
| `session_token_hash` | String | Not Null, Unique | Hashed session token |
| `refresh_token_hash` | String | Optional | Hashed refresh token |
| `expires_at` | DateTime | Not Null | Session expiration time |
| `last_active_at` | DateTime | Optional | Last activity time |
| `ip_address` | INET | Optional | Client IP address |
| `user_agent` | Text | Optional | Client user agent |
| `is_active` | Boolean | Not Null, Default True | Session active status |
| `revoked_at` | DateTime | Optional | Revocation timestamp |
| `created_at` | DateTime | Not Null, Default UTC | Creation timestamp |

### User Verifications Table (`user_verifications`)
**Purpose**: Email verification and password reset tokens

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | Primary Key | Verification identifier |
| `user_id` | UUID | Foreign Key (users), Not Null | Associated user |
| `verification_type` | Enum | Not Null | Type of verification |
| `token_hash` | String | Not Null, Unique | Hashed verification token |
| `expires_at` | DateTime | Not Null | Token expiration time |
| `used_at` | DateTime | Optional | Token usage time |
| `created_at` | DateTime | Not Null, Default UTC | Creation timestamp |

**Verification Types**: email_verify, password_reset, two_factor

### User OAuth Accounts Table (`user_oauth_accounts`)
**Purpose**: OAuth provider integrations

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | Primary Key | OAuth account identifier |
| `user_id` | UUID | Foreign Key (users), Not Null | Associated user |
| `provider` | Enum | Not Null | OAuth provider |
| `provider_user_id` | String | Not Null | Provider's user ID |
| `provider_email` | String | Optional | Email from provider |
| `access_token_id` | String | Optional | Stored access token reference |
| `refresh_token_id` | String | Optional | Stored refresh token reference |
| `expires_at` | DateTime | Optional | Token expiration time |
| `created_at` | DateTime | Not Null, Default UTC | Creation timestamp |
| `updated_at` | DateTime | Not Null, Auto-update | Last update timestamp |

**Constraints**:
- Unique constraint on (provider, provider_user_id)
**Providers**: google, github, microsoft, facebook

### API Keys Table (`api_keys`)
**Purpose**: API key management for programmatic access

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | Primary Key | API key identifier |
| `user_id` | UUID | Foreign Key (users), Not Null | Associated user |
| `name` | String | Not Null | API key name |
| `key_hash` | String | Not Null, Unique | Hashed API key |
| `can_read` | Boolean | Not Null, Default True | Read permission |
| `can_write` | Boolean | Not Null, Default False | Write permission |
| `can_admin` | Boolean | Not Null, Default False | Admin permission |
| `lab_access` | JSON | Optional | Lab-specific access controls |
| `last_used_at` | DateTime | Optional | Last usage time |
| `expires_at` | DateTime | Optional | Expiration time |
| `is_active` | Boolean | Not Null, Default True | API key active status |
| `revoked_at` | DateTime | Optional | Revocation timestamp |
| `created_at` | DateTime | Not Null, Default UTC | Creation timestamp |

---

## 7. Audit & Logging Tables

### Audit Logs Table (`audit_logs`)
**Purpose**: Comprehensive audit trail for security and compliance

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | Primary Key | Audit log identifier |
| `user_id` | UUID | Foreign Key (users), SET NULL | Associated user |
| `lab_id` | UUID | Foreign Key (labs), SET NULL | Associated lab |
| `action` | Enum | Not Null | Action performed |
| `resource_type` | String | Optional | Type of resource affected |
| `resource_id` | String | Optional | Specific resource identifier |
| `ip_address` | INET | Optional | Client IP address |
| `user_agent` | Text | Optional | Client user agent |
| `json_metadata` | JSON | Optional | Additional audit data |
| `created_at` | DateTime | Not Null, Default UTC | Log timestamp |

**Audit Actions**: login, logout, register, password_change, lab_create, lab_delete, api_key_create, data_export, schema_change

---

## Key Design Patterns

### 1. **Soft Deletes**
Most tables include `deleted_at` fields for soft deletion rather than hard deletes.

### 2. **UUID Primary Keys**
All primary keys use UUIDs for global uniqueness and security.

### 3. **Audit Trail**
Comprehensive audit logging tracks all significant user actions.

### 4. **Multi-tenancy**
Lab-based multi-tenancy with proper access controls.

### 5. **Asynchronous Processing**
Job queue system for handling long-running tasks.

### 6. **Neo4j Integration**
Dual database architecture with PostgreSQL for transactional data and Neo4j for graph operations.

### 7. **Flexible Configuration**
JSON fields for extensible configuration and metadata storage.

---

## Database Relationships Overview

```
User (1) ──── (M) Lab Member (M) ──── (1) Lab
  │                                      │
  ├── (1) ──── (M) User Session          ├── (1) ──── (M) Brainstorm Session
  ├── (1) ──── (M) API Key               ├── (1) ──── (M) Research Paper
  ├── (1) ──── (M) OAuth Account         ├── (1) ──── (M) Conversation
  ├── (1) ──── (M) User Verification     ├── (1) ──── (M) Neo4j Connection
  └── (1) ──── (M) Audit Log             ├── (1) ──── (M) KG Schema
                                         └── (1) ──── (M) Processing Job

Research Paper (1) ──── (M) Paper Analysis
Conversation (1) ──── (M) Message
Brainstorm Session (1) ──── (M) Research Keyword
Processing Job (1) ──── (M) Job Step
```

This schema supports a comprehensive research lab management system with collaboration features, knowledge graph integration, and robust security controls.
