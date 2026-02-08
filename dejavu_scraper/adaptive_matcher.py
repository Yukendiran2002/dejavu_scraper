"""
Adaptive Matcher Module for Intelligent Scraper

This module implements similarity-based element matching algorithms inspired by Scrapling.
It can relocate elements even after website structure changes by calculating similarity
scores across multiple element properties.
"""

from difflib import SequenceMatcher
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict


class AdaptiveMatcher:
    """
    Intelligent element matcher that uses similarity algorithms to find elements
    even when website structure changes.
    
    This is the core of the adaptive extraction feature, inspired by Scrapling's
    approach to element relocation.
    """
    
    # Weights for different property comparisons
    DEFAULT_WEIGHTS = {
        'tag_name': 0.15,
        'attributes': 0.20,
        'text': 0.15,
        'path': 0.10,
        'parent': 0.15,
        'grandparent': 0.10,
        'children': 0.10,
        'special_attrs': 0.05,  # class, id, href, src
    }
    
    def __init__(self, min_similarity: float = 0.5, weights: Dict[str, float] = None):
        """
        Initialize the adaptive matcher.
        
        Parameters
        ----------
        min_similarity : float
            Minimum similarity score (0-1) required to consider a match.
            Default is 0.5 (50% similarity).
        weights : dict, optional
            Custom weights for different property comparisons.
        """
        self.min_similarity = min_similarity
        self.weights = weights or self.DEFAULT_WEIGHTS
    
    def calculate_similarity(
        self, 
        stored_props: Dict[str, Any], 
        candidate_props: Dict[str, Any]
    ) -> float:
        """
        Calculate similarity score between stored element properties and a candidate element.
        
        Parameters
        ----------
        stored_props : dict
            The stored properties of the original element.
        candidate_props : dict
            Properties extracted from a candidate element on the page.
            
        Returns
        -------
        float
            Similarity score between 0 and 1.
        """
        scores = []
        total_weight = 0
        
        # 1. Tag name comparison (exact match required for high score)
        tag_score = 1.0 if stored_props.get('tag_name') == candidate_props.get('tag_name') else 0.0
        scores.append(('tag_name', tag_score, self.weights['tag_name']))
        total_weight += self.weights['tag_name']
        
        # 2. Attributes comparison
        attr_score = self._compare_attributes(
            stored_props.get('attributes', {}),
            candidate_props.get('attributes', {})
        )
        scores.append(('attributes', attr_score, self.weights['attributes']))
        total_weight += self.weights['attributes']
        
        # 3. Text content comparison
        text_score = self._compare_text(
            stored_props.get('text', ''),
            candidate_props.get('text', '')
        )
        scores.append(('text', text_score, self.weights['text']))
        total_weight += self.weights['text']
        
        # 4. DOM path comparison
        path_score = self._compare_paths(
            stored_props.get('path', ''),
            candidate_props.get('path', '')
        )
        scores.append(('path', path_score, self.weights['path']))
        total_weight += self.weights['path']
        
        # 5. Parent comparison
        parent_score = self._compare_parent(stored_props, candidate_props)
        scores.append(('parent', parent_score, self.weights['parent']))
        total_weight += self.weights['parent']
        
        # 6. Grandparent comparison
        grandparent_score = self._compare_grandparent(stored_props, candidate_props)
        scores.append(('grandparent', grandparent_score, self.weights['grandparent']))
        total_weight += self.weights['grandparent']
        
        # 7. Children structure comparison
        children_score = self._compare_children(stored_props, candidate_props)
        scores.append(('children', children_score, self.weights['children']))
        total_weight += self.weights['children']
        
        # 8. Special attributes (class, id, href, src)
        special_score = self._compare_special_attributes(
            stored_props.get('attributes', {}),
            candidate_props.get('attributes', {})
        )
        scores.append(('special_attrs', special_score, self.weights['special_attrs']))
        total_weight += self.weights['special_attrs']
        
        # Calculate weighted average
        if total_weight == 0:
            return 0.0
        
        weighted_sum = sum(score * weight for _, score, weight in scores)
        final_score = weighted_sum / total_weight
        
        return round(final_score, 4)
    
    def _compare_text(self, text1: str, text2: str) -> float:
        """Compare two text strings using sequence matching."""
        if not text1 and not text2:
            return 1.0  # Both empty is a match
        if not text1 or not text2:
            return 0.0
        
        # Normalize texts
        text1 = ' '.join(text1.lower().split())
        text2 = ' '.join(text2.lower().split())
        
        return SequenceMatcher(None, text1, text2).ratio()
    
    def _compare_paths(self, path1: str, path2: str) -> float:
        """Compare DOM paths."""
        if not path1 and not path2:
            return 1.0
        if not path1 or not path2:
            return 0.0
        
        # Split paths and compare
        parts1 = path1.split('/')
        parts2 = path2.split('/')
        
        # Check suffix match (more important than prefix)
        suffix_match = 0
        min_len = min(len(parts1), len(parts2))
        
        for i in range(1, min_len + 1):
            if parts1[-i] == parts2[-i]:
                suffix_match += 1
            else:
                break
        
        # Also do sequence matching for overall similarity
        seq_ratio = SequenceMatcher(None, parts1, parts2).ratio()
        suffix_ratio = suffix_match / min_len if min_len > 0 else 0
        
        # Weight suffix matching higher
        return (seq_ratio * 0.4) + (suffix_ratio * 0.6)
    
    def _compare_attributes(self, attrs1: Dict, attrs2: Dict) -> float:
        """Compare attribute dictionaries."""
        if not attrs1 and not attrs2:
            return 1.0  # Both empty is a match
        if not attrs1 or not attrs2:
            return 0.3  # Partial match
        
        all_keys = set(attrs1.keys()) | set(attrs2.keys())
        if not all_keys:
            return 1.0
        
        score = 0
        for key in all_keys:
            val1 = self._normalize_attr_value(attrs1.get(key, ''))
            val2 = self._normalize_attr_value(attrs2.get(key, ''))
            
            if val1 == val2:
                score += 1.0
            elif val1 and val2:
                score += SequenceMatcher(None, val1, val2).ratio()
        
        return score / len(all_keys)
    
    def _compare_special_attributes(self, attrs1: Dict, attrs2: Dict) -> float:
        """Compare special attributes that are more important for identification."""
        special_attrs = ['class', 'id', 'href', 'src', 'data-id', 'name']
        
        scores = []
        for attr in special_attrs:
            val1 = self._normalize_attr_value(attrs1.get(attr, ''))
            val2 = self._normalize_attr_value(attrs2.get(attr, ''))
            
            if val1 or val2:  # Only compare if at least one has the attribute
                if val1 == val2:
                    scores.append(1.0)
                elif val1 and val2:
                    scores.append(SequenceMatcher(None, val1, val2).ratio())
                else:
                    scores.append(0.0)
        
        return sum(scores) / len(scores) if scores else 1.0
    
    def _compare_parent(self, props1: Dict, props2: Dict) -> float:
        """Compare parent element properties."""
        parent1_name = props1.get('parent_name')
        parent2_name = props2.get('parent_name')
        
        if not parent1_name and not parent2_name:
            return 1.0
        if not parent1_name or not parent2_name:
            return 0.3
        
        scores = []
        
        # Tag name match
        scores.append(1.0 if parent1_name == parent2_name else 0.0)
        
        # Attributes match
        parent1_attrs = props1.get('parent_attribs', {})
        parent2_attrs = props2.get('parent_attribs', {})
        scores.append(self._compare_attributes(parent1_attrs, parent2_attrs))
        
        # Parent text match
        parent1_text = props1.get('parent_text', '')
        parent2_text = props2.get('parent_text', '')
        if parent1_text or parent2_text:
            scores.append(self._compare_text(parent1_text, parent2_text))
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _compare_grandparent(self, props1: Dict, props2: Dict) -> float:
        """Compare grandparent element properties."""
        gp1_name = props1.get('grandparent_name')
        gp2_name = props2.get('grandparent_name')
        
        if not gp1_name and not gp2_name:
            return 1.0
        if not gp1_name or not gp2_name:
            return 0.3
        
        scores = []
        
        # Tag name match
        scores.append(1.0 if gp1_name == gp2_name else 0.0)
        
        # Attributes match
        gp1_attrs = props1.get('grandparent_attribs', {})
        gp2_attrs = props2.get('grandparent_attribs', {})
        scores.append(self._compare_attributes(gp1_attrs, gp2_attrs))
        
        return sum(scores) / len(scores) if scores else 0.0
    
    def _compare_children(self, props1: Dict, props2: Dict) -> float:
        """Compare children structure."""
        children1 = props1.get('children_tags', [])
        children2 = props2.get('children_tags', [])
        
        if not children1 and not children2:
            return 1.0
        if not children1 or not children2:
            return 0.3
        
        # Compare children tag sequences
        return SequenceMatcher(None, children1, children2).ratio()
    
    @staticmethod
    def _normalize_attr_value(value) -> str:
        """Normalize attribute value to string for comparison."""
        if isinstance(value, list):
            return ' '.join(sorted(str(v) for v in value))
        return str(value) if value else ''
    
    def find_best_match(
        self,
        stored_props: Dict[str, Any],
        candidates: List[Any],
        extract_props_func,
        url: str = ""
    ) -> Tuple[Optional[Any], float, List[Tuple[Any, float]]]:
        """
        Find the best matching element from a list of candidates.
        
        Parameters
        ----------
        stored_props : dict
            The stored properties of the original element.
        candidates : list
            List of candidate BeautifulSoup elements.
        extract_props_func : callable
            Function to extract properties from a candidate element.
        url : str, optional
            The page URL for context.
            
        Returns
        -------
        tuple
            (best_match_element, best_score, all_matches_with_scores)
            Returns (None, 0, []) if no match found above minimum similarity.
        """
        matches = []
        
        for candidate in candidates:
            try:
                candidate_props = extract_props_func(candidate, url)
                score = self.calculate_similarity(stored_props, candidate_props)
                
                if score >= self.min_similarity:
                    matches.append((candidate, score))
            except Exception:
                continue
        
        # Sort by score descending
        matches.sort(key=lambda x: x[1], reverse=True)
        
        if matches:
            return matches[0][0], matches[0][1], matches
        
        return None, 0.0, []
    
    def find_similar_elements(
        self,
        reference_element,
        all_elements: List[Any],
        extract_props_func,
        url: str = "",
        similarity_threshold: float = 0.6
    ) -> List[Tuple[Any, float]]:
        """
        Find elements similar to a reference element (like AutoScraper's wanted_list feature).
        
        Parameters
        ----------
        reference_element : bs4.element.Tag
            The reference element to find similar elements for.
        all_elements : list
            List of all candidate elements to search through.
        extract_props_func : callable
            Function to extract properties from an element.
        url : str, optional
            The page URL for context.
        similarity_threshold : float
            Minimum similarity score to include in results.
            
        Returns
        -------
        list
            List of (element, similarity_score) tuples, sorted by score descending.
        """
        ref_props = extract_props_func(reference_element, url)
        
        similar = []
        for element in all_elements:
            if element == reference_element:
                continue
            
            try:
                elem_props = extract_props_func(element, url)
                
                # Quick filter: same tag name required
                if elem_props.get('tag_name') != ref_props.get('tag_name'):
                    continue
                
                # Quick filter: same depth (or close)
                depth_diff = abs(elem_props.get('depth', 0) - ref_props.get('depth', 0))
                if depth_diff > 2:
                    continue
                
                score = self.calculate_similarity(ref_props, elem_props)
                
                if score >= similarity_threshold:
                    similar.append((element, score))
            except Exception:
                continue
        
        # Sort by score descending
        similar.sort(key=lambda x: x[1], reverse=True)
        
        return similar


class FuzzyTextMatcher:
    """
    Enhanced fuzzy text matching for finding elements by text content.
    """
    
    def __init__(self, ratio_limit: float = 0.8):
        """
        Initialize the fuzzy text matcher.
        
        Parameters
        ----------
        ratio_limit : float
            Minimum similarity ratio (0-1) for text matching.
        """
        self.ratio_limit = ratio_limit
    
    def match(self, pattern: str, text: str) -> bool:
        """
        Check if text matches the pattern with fuzzy matching.
        
        Parameters
        ----------
        pattern : str
            The pattern to match against.
        text : str
            The text to check.
            
        Returns
        -------
        bool
            True if the text matches the pattern within the ratio limit.
        """
        if not pattern or not text:
            return False
        
        # Normalize both strings
        pattern = ' '.join(pattern.lower().split())
        text = ' '.join(text.lower().split())
        
        # Exact match
        if pattern == text:
            return True
        
        # Check if pattern is contained in text
        if pattern in text or text in pattern:
            return True
        
        # Fuzzy match
        return SequenceMatcher(None, pattern, text).ratio() >= self.ratio_limit
    
    def find_ratio(self, pattern: str, text: str) -> float:
        """
        Get the similarity ratio between pattern and text.
        
        Parameters
        ----------
        pattern : str
            The pattern to match against.
        text : str
            The text to check.
            
        Returns
        -------
        float
            Similarity ratio between 0 and 1.
        """
        if not pattern or not text:
            return 0.0
        
        pattern = ' '.join(pattern.lower().split())
        text = ' '.join(text.lower().split())
        
        if pattern == text:
            return 1.0
        
        return SequenceMatcher(None, pattern, text).ratio()
