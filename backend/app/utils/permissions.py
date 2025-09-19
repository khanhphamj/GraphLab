"""Permission utilities for role-based access control"""

from typing import List, Dict, Any


class LabPermissions:
    """Lab role-based permissions"""
    
    # Define permissions for each role
    ROLE_PERMISSIONS: Dict[str, Dict[str, bool]] = {
        'owner': {
            'manage_lab': True,
            'delete_lab': True,
            'transfer_ownership': True,
            'manage_members': True,
            'manage_settings': True,
            'manage_schemas': True,
            'manage_connections': True,
            'run_jobs': True,
            'delete_data': True,
            'create_brainstorm': True,
            'view_data': True,
            'participate_conversations': True,
        },
        'admin': {
            'manage_lab': False,
            'delete_lab': False,
            'transfer_ownership': False,
            'manage_members': True,
            'manage_settings': True,
            'manage_schemas': True,
            'manage_connections': True,
            'run_jobs': True,
            'delete_data': True,
            'create_brainstorm': True,
            'view_data': True,
            'participate_conversations': True,
        },
        'viewer': {
            'manage_lab': False,
            'delete_lab': False,
            'transfer_ownership': False,
            'manage_members': False,
            'manage_settings': False,
            'manage_schemas': False,
            'manage_connections': False,
            'run_jobs': False,
            'delete_data': False,
            'create_brainstorm': False,
            'view_data': True,
            'participate_conversations': True,  # Read/comment only
        }
    }

    @classmethod
    def can_perform(cls, role: str, permission: str) -> bool:
        """Check if role can perform specific permission"""
        if role not in cls.ROLE_PERMISSIONS:
            return False
        return cls.ROLE_PERMISSIONS[role].get(permission, False)

    @classmethod
    def get_role_permissions(cls, role: str) -> Dict[str, bool]:
        """Get all permissions for a role"""
        return cls.ROLE_PERMISSIONS.get(role, {})

    @classmethod
    def can_manage_members(cls, role: str) -> bool:
        """Check if role can manage lab members"""
        return cls.can_perform(role, 'manage_members')

    @classmethod
    def can_manage_lab(cls, role: str) -> bool:
        """Check if role can manage lab settings"""
        return cls.can_perform(role, 'manage_lab') or cls.can_perform(role, 'manage_settings')

    @classmethod
    def can_delete_lab(cls, role: str) -> bool:
        """Check if role can delete lab"""
        return cls.can_perform(role, 'delete_lab')

    @classmethod
    def can_run_jobs(cls, role: str) -> bool:
        """Check if role can run processing jobs"""
        return cls.can_perform(role, 'run_jobs')

    @classmethod
    def can_manage_schemas(cls, role: str) -> bool:
        """Check if role can manage schemas"""
        return cls.can_perform(role, 'manage_schemas')

    @classmethod
    def can_delete_data(cls, role: str) -> bool:
        """Check if role can delete data"""
        return cls.can_perform(role, 'delete_data')

    @classmethod
    def get_available_roles(cls) -> List[str]:
        """Get list of available roles"""
        return list(cls.ROLE_PERMISSIONS.keys())

    @classmethod
    def is_admin_role(cls, role: str) -> bool:
        """Check if role has admin privileges"""
        return role in ['owner', 'admin']

    @classmethod
    def is_management_role(cls, role: str) -> bool:
        """Check if role can manage other members"""
        return cls.can_manage_members(role)


# Role hierarchy for comparison
ROLE_HIERARCHY = {
    'owner': 3,
    'admin': 2,
    'viewer': 1
}


def get_role_level(role: str) -> int:
    """Get numeric level for role comparison"""
    return ROLE_HIERARCHY.get(role, 0)


def can_manage_role(current_role: str, target_role: str) -> bool:
    """Check if current role can manage target role"""
    if current_role == 'owner':
        return target_role != 'owner'  # Owner can manage all except other owners
    elif current_role == 'admin':
        return target_role in ['viewer']  # Admin can manage viewer
    else:
        return False  # Viewer cannot manage others


def get_role_description(role: str) -> str:
    """Get human-readable description for role"""
    descriptions = {
        'owner': 'Lab Owner - Full control of lab',
        'admin': 'Administrator - Manage members and settings',
        'viewer': 'Viewer/Observer - Read-only access'
    }
    return descriptions.get(role, 'Unknown role')
