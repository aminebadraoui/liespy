from urllib.parse import urlparse, urlunparse

def normalize_url(url: str) -> str:
    """
    Normalizes a URL for consistent storage and retrieval.
    - Strips trailing slashes from path
    - Lowercases the scheme and netloc
    - Preserves query parameters (for now, as some pages differ by query)
    - Removes fragments
    """
    if not url:
        return url
        
    try:
        parsed = urlparse(url)
        
        # Lowercase scheme and netloc
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        
        # Strip trailing slash from path
        path = parsed.path
        if path.endswith('/') and len(path) > 1:
            path = path.rstrip('/')
            
        # Reconstruct
        # scheme, netloc, url, params, query, fragment
        cleaned = urlunparse((scheme, netloc, path, parsed.params, parsed.query, ''))
        
        return cleaned
    except Exception:
        # Fallback if parsing fails
        return url.rstrip('/')
