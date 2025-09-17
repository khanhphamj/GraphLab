from .user import User
from .lab import Lab
from .lab_member import LabMember
from .brainstorm_session import BrainstormSession
from .research_keyword import ResearchKeyword
from .kg_schema import KgSchema
from .neo4j_connection import Neo4jConnection
from .processing_job import ProcessingJob
from .job_step import JobStep
from .research_paper import ResearchPaper
from .paper_analysis import PaperAnalysis
from .conversation import Conversation
from .message import Message
from .user_session import UserSession
from .user_verification import UserVerification
from .user_oauth_account import UserOauthAccount
from .api_key import ApiKey
from .audit_log import AuditLog

# Keep legacy imports for backward compatibility
Paper = ResearchPaper  # Alias for backward compatibility