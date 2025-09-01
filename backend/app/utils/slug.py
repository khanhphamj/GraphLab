def name_to_slug(name: str) -> str:
    """
    Convert a human-readable name to URL-friendly slug.
    
    Examples:
    - "My Research Lab!" → "my-research-lab"
    - "AI & ML Projects" → "ai-ml-projects"
    - "Deep Learning 2024" → "deep-learning-2024"
    
    Args:
        name: Human-readable name to convert
        
    Returns:
        URL-friendly slug
        
    Raises:
        ValueError: If name is None or empty
    """
    if not name or not isinstance(name, str):
        raise ValueError("Name must be a non-empty string")
    
    # Remove special characters and convert to lowercase
    slug = re.sub(r'[^\w\s-]', '', name).strip().lower()
    # Replace spaces and underscores with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    
    return slug


def slug_to_name(slug: str) -> str:
    """
    Convert slug back to readable name.
    
    Examples:
    - "my-research-lab" → "My Research Lab"
    - "ai-ml-projects" → "Ai Ml Projects"
    
    Args:
        slug: URL-friendly slug to convert
        
    Returns:
        Human-readable name
        
    Raises:
        ValueError: If slug is None or empty
    """
    if not slug or not isinstance(slug, str):
        raise ValueError("Slug must be a non-empty string")
    
    # Convert hyphens to spaces and capitalize words
    name = slug.replace('-', ' ').title()
    return name


def is_valid_slug(slug: str) -> bool:
    """
    Validate if a string is a valid slug format.
    
    Args:
        slug: String to validate
        
    Returns:
        True if valid slug format, False otherwise
    """
    if not slug or not isinstance(slug, str):
        return False
    
    # Slug should only contain lowercase letters, numbers, and hyphens
    pattern = r'^[a-z0-9-]+$'  # No leading/trailing hyphens allowed
    return bool(re.match(pattern, slug))


def sanitize_slug(slug: str) -> Optional[str]:
    """
    Sanitize and validate a slug, return None if invalid.
    
    Args:
        slug: Slug to sanitize
        
    Returns:
        Sanitized slug or None if invalid
    """
    if not is_valid_slug(slug):
        return None
    
    # Ensure no leading/trailing hyphens
    return slug.strip('-')