import hashlib
import math
from typing import List, Set, Optional, Callable

class BloomFilter:
    """
    Bloom filter implementation for efficient keyword lookups.
    Provides probabilistic set membership testing with no false negatives.
    """
    
    def __init__(self, expected_elements: int, false_positive_rate: float = 0.01):
        """
        Initialize a Bloom filter.
        
        Args:
            expected_elements: Expected number of elements to be inserted
            false_positive_rate: Desired false positive rate (default: 0.01 or 1%)
        """
        # Calculate optimal size and hash functions
        self.size = self._calculate_optimal_size(expected_elements, false_positive_rate)
        self.hash_count = self._calculate_optimal_hash_count(self.size, expected_elements)
        
        # Initialize bit array
        self.bit_array = [0] * self.size
        self.element_count = 0
    
    def _calculate_optimal_size(self, n: int, p: float) -> int:
        """Calculate optimal size of bit array based on expected elements and FP rate"""
        size = -n * math.log(p) / (math.log(2) ** 2)
        return max(int(size), 1024)  # Ensure minimum size
    
    def _calculate_optimal_hash_count(self, m: int, n: int) -> int:
        """Calculate optimal number of hash functions"""
        k = m / n * math.log(2)
        return max(int(k), 2)  # Ensure minimum hash functions
    
    def _get_hash_values(self, item: str) -> List[int]:
        """Generate multiple hash values for an item"""
        hash_values = []
        
        # Use different seeds to generate multiple hash values
        for i in range(self.hash_count):
            # Combine item with seed for each hash function
            seed = f"{item}_{i}"
            hash_obj = hashlib.md5(seed.encode('utf-8'))
            hash_val = int(hash_obj.hexdigest(), 16) % self.size
            hash_values.append(hash_val)
        
        return hash_values
    
    def add(self, item: str) -> None:
        """Add an item to the Bloom filter"""
        for index in self._get_hash_values(item):
            self.bit_array[index] = 1
        
        self.element_count += 1
    
    def add_all(self, items: List[str]) -> None:
        """Add multiple items to the Bloom filter"""
        for item in items:
            self.add(item)
    
    def might_contain(self, item: str) -> bool:
        """
        Check if an item might be in the set.
        False positives are possible, but false negatives are not.
        """
        for index in self._get_hash_values(item):
            if self.bit_array[index] == 0:
                return False
        return True
    
    def estimate_false_positive_rate(self) -> float:
        """Estimate the current false positive rate based on elements added"""
        if self.element_count == 0:
            return 0.0
        
        # Calculate probability of false positive
        # p = (1 - e^(-k*n/m))^k
        k = self.hash_count
        n = self.element_count
        m = self.size
        
        return (1 - math.exp(-k * n / m)) ** k

class KeywordBloomFilter:
    """Document keyword Bloom filter manager"""
    
    def __init__(self, expected_docs: int = 1000):
        # Create Bloom filter for all keywords across documents
        self.global_filter = BloomFilter(expected_docs * 20)  # Assume avg 20 keywords per doc
        
        # Document-specific filters
        self.doc_filters = {}
    
    def add_document_keywords(self, doc_id: str, keywords: List[str]) -> None:
        """Add keywords for a specific document"""
        # Create document-specific filter
        doc_filter = BloomFilter(len(keywords) * 2)  # *2 for margin
        doc_filter.add_all(keywords)
        self.doc_filters[doc_id] = doc_filter
        
        # Add to global filter
        self.global_filter.add_all(keywords)
    
    def document_might_contain(self, doc_id: str, keyword: str) -> bool:
        """Check if a document might contain a keyword"""
        if doc_id not in self.doc_filters:
            return False
        return self.doc_filters[doc_id].might_contain(keyword)
    
    def any_document_might_contain(self, keyword: str) -> bool:
        """Check if any document might contain a keyword"""
        return self.global_filter.might_contain(keyword)

# Create singleton instance for application use
keyword_filter = KeywordBloomFilter()
