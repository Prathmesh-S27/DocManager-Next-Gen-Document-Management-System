import re
from typing import List, Set, Dict, Any
import string

def extract_keywords(text: str, min_length: int = 3, max_length: int = 30) -> List[str]:
    """
    Extract meaningful keywords from text:
    - Split by spaces and punctuation
    - Remove short words (< min_length)
    - Remove very long words (> max_length)
    - Remove stop words
    - Remove duplicates
    """
    if not text:
        return []

    # Common English stop words to filter out
    stop_words = {
        'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
        'when', 'where', 'how', 'which', 'who', 'whom', 'this', 'that', 'these',
        'those', 'then', 'just', 'so', 'than', 'such', 'both', 'through', 'about',
        'for', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
        'had', 'having', 'do', 'does', 'did', 'doing', 'to', 'from', 'by', 'with',
        'against', 'into', 'during', 'before', 'after', 'above', 'below', 'over',
        'under', 'again', 'further', 'then', 'once', 'here', 'there', 'all', 'any',
        'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
        'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 'can', 'will',
        'in', 'on', 'at', 'of', 'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 
        'ourselves', 'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him',
        'his', 'himself', 'she', 'her', 'hers', 'herself', 'it', 'its', 'itself',
        'they', 'them', 'their', 'theirs', 'themselves', 'one', 'two', 'three',
        'could', 'would', 'should', 'shall', 'may', 'might', 'must', 'also'
    }

    # Split text into words and clean
    words = re.findall(r'\b[a-zA-Z0-9]+\b', text.lower())
    
    # Filter words
    keywords = [
        word for word in words
        if min_length <= len(word) <= max_length and word not in stop_words
    ]
    
    # Remove duplicates while preserving order
    unique_keywords = []
    seen = set()
    for keyword in keywords:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)
    
    return unique_keywords[:100]  # Limit to 100 keywords max

def clean_text(text: str) -> str:
    """Clean text by removing extra spaces and normalizing whitespace"""
    if not text:
        return ""
    
    # Replace multiple spaces/newlines with a single space
    cleaned = re.sub(r'\s+', ' ', text)
    # Trim leading/trailing whitespace
    cleaned = cleaned.strip()
    return cleaned
