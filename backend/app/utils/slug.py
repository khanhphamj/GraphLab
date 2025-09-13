"""Slug utility functions for converting names to URL-friendly strings"""

import re
import unicodedata
from typing import Optional


def name_to_slug(name: str) -> str:
    """Convert a name to a URL-friendly slug"""
    if not name:
        return ""
    
    # Convert to lowercase and remove accents
    slug = unicodedata.normalize('NFKD', name.lower())
    slug = slug.encode('ascii', 'ignore').decode('ascii')
    
    # Replace spaces and special characters with hyphens
    slug = re.sub(r'[^a-z0-9\-_]', '-', slug)
    
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    
    # Remove leading and trailing hyphens
    slug = slug.strip('-')
    
    return slug


def slug_to_name(slug: str) -> str:
    """Convert a slug back to a readable name"""
    if not slug:
        return ""
    
    # Replace hyphens and underscores with spaces
    name = slug.replace('-', ' ').replace('_', ' ')
    
    # Capitalize each word
    name = ' '.join(word.capitalize() for word in name.split())
    
    return name


def is_valid_slug(slug: str) -> bool:
    """Check if a string is a valid slug"""
    if not slug:
        return False
    
    # Check if slug contains only allowed characters
    return bool(re.match(r'^[a-z0-9\-_]+$', slug))


def sanitize_slug(slug: str, max_length: Optional[int] = 50) -> str:
    """Sanitize and validate a slug"""
    if not slug:
        return ""
    
    # Convert to slug format
    sanitized = name_to_slug(slug)
    
    # Truncate if too long
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length].rstrip('-')
    
    # Ensure it's not empty after sanitization
    if not sanitized:
        return "untitled"
    
    return sanitized
