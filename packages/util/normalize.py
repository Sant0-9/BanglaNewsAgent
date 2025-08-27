import re
import hashlib
from typing import Optional

def normalize_text(text: Optional[str]) -> str:
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove extra whitespace and normalize line breaks
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]', '', text)
    
    return text

def clean_title(title: Optional[str]) -> str:
    if not title:
        return ""
    
    # Normalize text first
    title = normalize_text(title)
    
    # Remove common RSS artifacts
    title = re.sub(r'\s*-\s*[^-]+$', '', title)  # Remove " - Source Name" at end
    title = re.sub(r'^\[[^\]]+\]\s*', '', title)  # Remove "[Category] " at start
    
    return title.strip()

def extract_domain(url: Optional[str]) -> str:
    if not url:
        return ""
    
    # Extract domain from URL
    match = re.search(r'https?://(?:www\.)?([^/]+)', url)
    if match:
        return match.group(1)
    return url

def truncate_text(text: str, max_length: int = 500) -> str:
    if len(text) <= max_length:
        return text
    
    # Try to truncate at word boundary
    truncated = text[:max_length]
    last_space = truncated.rfind(' ')
    
    if last_space > max_length * 0.8:  # If we can find a space in the last 20%
        truncated = truncated[:last_space]
    
    return truncated + "..."

def clean_text(s: str) -> str:
    """Strip whitespace and collapse multiple whitespace into single spaces"""
    if not s:
        return ""
    # Strip leading/trailing whitespace and collapse multiple whitespace
    return re.sub(r'\s+', ' ', s.strip())

def fingerprint(text: str) -> str:
    """Generate SHA1 hash of lowercased alphanumeric-only 200-char slice"""
    if not text:
        return ""
    
    # Keep only alphanumeric characters and convert to lowercase
    alnum_only = re.sub(r'[^a-zA-Z0-9]', '', text.lower())
    
    # Take first 200 characters
    slice_200 = alnum_only[:200]
    
    # Generate SHA1 hash
    return hashlib.sha1(slice_200.encode('utf-8')).hexdigest()