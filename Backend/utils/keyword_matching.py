import threading
import re
from typing import List, Dict, Any, Optional, Set

# Try to import pyahocorasick, but provide a fallback if not available
try:
    import pyahocorasick
    PYAHOCORASICK_AVAILABLE = True
except ImportError:
    print("Warning: pyahocorasick module not found. Using fallback implementation.")
    print("For better performance, install with: pip install pyahocorasick")
    PYAHOCORASICK_AVAILABLE = False

class KeywordMatcher:
    """Efficient keyword matching using Aho-Corasick algorithm or fallback"""
    
    def __init__(self):
        """Initialize an empty automaton or fallback structure"""
        self.keywords = set()  # Keep track of all keywords
        self.lock = threading.Lock()  # Thread safety lock
        
        if PYAHOCORASICK_AVAILABLE:
            self.automaton = pyahocorasick.Automaton()
            self.is_built = False  # Flag to track if automaton is built
        else:
            # Fallback implementation using Python built-ins
            self.is_built = True  # Always marked as built for fallback
    
    def add_keywords(self, keywords: List[str]) -> None:
        """
        Add keywords to the matcher
        Will rebuild the automaton if it was already built
        """
        with self.lock:
            # Filter out empty keywords
            valid_keywords = [k.lower() for k in keywords if k and len(k.strip()) > 0]
            
            if not valid_keywords:
                return
            
            if PYAHOCORASICK_AVAILABLE:
                # Check if we need to rebuild
                needs_rebuild = self.is_built
                new_keywords = False
                
                if needs_rebuild:
                    # Create a new automaton instance
                    self.automaton = pyahocorasick.Automaton()
                    self.is_built = False
                    
                    # Re-add all existing keywords
                    for keyword in self.keywords:
                        self.automaton.add_str(keyword)
                        
                # Add new keywords
                for keyword in valid_keywords:
                    if keyword not in self.keywords:
                        self.keywords.add(keyword)
                        self.automaton.add_str(keyword)
                        new_keywords = True
                
                # Build the automaton if we added new keywords or had to rebuild
                if (new_keywords or needs_rebuild) and not self.is_built:
                    self.automaton.make_automaton()
                    self.is_built = True
            else:
                # Fallback implementation just adds to the set
                self.keywords.update(valid_keywords)
            
    def match_keywords(self, text: str) -> List[str]:
        """
        Find all keywords in text
        Returns list of found keywords
        """
        with self.lock:
            if not text:
                return []
                
            text = text.lower()
            found_keywords = set()
            
            try:
                if PYAHOCORASICK_AVAILABLE:
                    if not self.is_built:
                        return []
                    
                    # Use Aho-Corasick algorithm
                    for match in self.automaton.iter(text):
                        end_index, _ = match
                        found_keyword = text[end_index - len(self.automaton.get_output(match)) + 1:end_index + 1]
                        found_keywords.add(found_keyword)
                else:
                    # Fallback implementation using simple string matching
                    # This is much slower but works without the module
                    for keyword in self.keywords:
                        if keyword in text:
                            found_keywords.add(keyword)
            except Exception as e:
                print(f"Error during keyword matching: {e}")
            
            return list(found_keywords)
    
    def count_keyword_occurrences(self, text: str) -> Dict[str, int]:
        """
        Count occurrences of each keyword in text
        Returns dict with keyword:count pairs
        """
        with self.lock:
            if not text:
                return {}
                
            text = text.lower()
            occurrences = {}
            
            try:
                if PYAHOCORASICK_AVAILABLE:
                    if not self.is_built:
                        return {}
                    
                    # Use Aho-Corasick algorithm
                    for match in self.automaton.iter(text):
                        end_index, _ = match
                        keyword = text[end_index - len(self.automaton.get_output(match)) + 1:end_index + 1]
                        
                        if keyword in occurrences:
                            occurrences[keyword] += 1
                        else:
                            occurrences[keyword] = 1
                else:
                    # Fallback implementation
                    for keyword in self.keywords:
                        count = 0
                        start = 0
                        while True:
                            start = text.find(keyword, start)
                            if start == -1:
                                break
                            count += 1
                            start += len(keyword)
                        
                        if count > 0:
                            occurrences[keyword] = count
            except Exception as e:
                print(f"Error counting keyword occurrences: {e}")
            
            return occurrences
    
    def get_all_keywords(self) -> List[str]:
        """Get all keywords in the matcher"""
        with self.lock:
            return list(self.keywords)
    
    def clear(self) -> None:
        """Remove all keywords from the matcher"""
        with self.lock:
            self.keywords = set()
            if PYAHOCORASICK_AVAILABLE:
                self.automaton = pyahocorasick.Automaton()
                self.is_built = False

# Create a singleton instance
keyword_matcher = KeywordMatcher()
