"""
Adaptive Storage Module for Intelligent Scraper

This module handles storing and retrieving element properties for adaptive extraction.
When website structures change, the stored properties are used to relocate elements
using similarity matching algorithms.
"""

import json
import hashlib
import logging
import threading
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
from datetime import datetime

logger = logging.getLogger(__name__)


class AdaptiveStorage:
    """
    In-memory storage for element properties used in adaptive extraction.
    
    Stores unique properties of elements so they can be relocated even after
    website structure changes. All data is saved to the same JSON file as
    the stack_list when save() is called.
    
    Thread-safe: All read/write operations are protected by a reentrant lock.
    """
    
    def __init__(self):
        """
        Initialize the adaptive storage with in-memory dictionary.
        """
        # In-memory storage: {domain: {identifier: properties}}
        self._data: Dict[str, Dict[str, Dict[str, Any]]] = {}
        self._lock = threading.RLock()
    
    @staticmethod
    def extract_domain(url: str) -> str:
        """
        Extract domain from URL for storage isolation.
        
        Parameters
        ----------
        url : str
            The URL to extract domain from.
            
        Returns
        -------
        str
            The extracted domain or 'default' if URL is invalid.
        """
        if not url:
            return "default"
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path.split('/')[0]
            # Remove www. prefix and port
            domain = domain.replace('www.', '').split(':')[0]
            return domain or "default"
        except Exception:
            return "default"
    
    def save(self, domain: str, identifier: str, properties: Dict[str, Any]) -> bool:
        """
        Save element properties for later retrieval.
        
        Parameters
        ----------
        domain : str
            The domain/website identifier.
        identifier : str
            Unique identifier for this element (e.g., CSS selector or custom name).
        properties : dict
            Dictionary containing element's unique properties.
            
        Returns
        -------
        bool
            True if save was successful.
        """
        try:
            with self._lock:
                if domain not in self._data:
                    self._data[domain] = {}
                
                self._data[domain][identifier] = properties
            return True
        except Exception as e:
            logger.error(f"Error saving element properties: {e}")
            return False
    
    def retrieve(self, domain: str, identifier: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve stored element properties.
        
        Parameters
        ----------
        domain : str
            The domain/website identifier.
        identifier : str
            Unique identifier for the element.
            
        Returns
        -------
        dict or None
            The stored properties dictionary, or None if not found.
        """
        try:
            with self._lock:
                return self._data.get(domain, {}).get(identifier)
        except Exception as e:
            logger.error(f"Error retrieving element properties: {e}")
            return None
    
    def delete(self, domain: str, identifier: str) -> bool:
        """
        Delete stored element properties.
        
        Parameters
        ----------
        domain : str
            The domain/website identifier.
        identifier : str
            Unique identifier for the element.
            
        Returns
        -------
        bool
            True if deletion was successful.
        """
        try:
            with self._lock:
                if domain in self._data and identifier in self._data[domain]:
                    del self._data[domain][identifier]
                    # Clean up empty domain dict
                    if not self._data[domain]:
                        del self._data[domain]
            return True
        except Exception as e:
            logger.error(f"Error deleting element properties: {e}")
            return False
    
    def list_identifiers(self, domain: str) -> List[str]:
        """
        List all stored identifiers for a domain.
        
        Parameters
        ----------
        domain : str
            The domain/website identifier.
            
        Returns
        -------
        list
            List of identifier strings.
        """
        with self._lock:
            return list(self._data.get(domain, {}).keys())
    
    def clear_domain(self, domain: str) -> bool:
        """
        Clear all stored properties for a domain.
        
        Parameters
        ----------
        domain : str
            The domain/website identifier.
            
        Returns
        -------
        bool
            True if clearing was successful.
        """
        try:
            with self._lock:
                if domain in self._data:
                    del self._data[domain]
            return True
        except Exception:
            return False
    
    def export_all(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Export all adaptive data for saving to JSON.
        
        Returns
        -------
        dict
            All stored adaptive data.
        """
        with self._lock:
            import copy
            return copy.deepcopy(self._data)
    
    def import_all(self, data: Dict[str, Dict[str, Dict[str, Any]]]) -> None:
        """
        Import adaptive data from JSON.
        
        Parameters
        ----------
        data : dict
            Adaptive data to import.
        """
        with self._lock:
            if data:
                import copy
                self._data = copy.deepcopy(data)
    
    def clear_all(self) -> None:
        """Clear all stored data."""
        with self._lock:
            self._data = {}


def extract_element_properties(element, url: str = "") -> Dict[str, Any]:
    """
    Extract unique properties from a BeautifulSoup element for adaptive matching.
    
    This function captures all the relevant properties that can be used to
    identify and relocate an element even after website structure changes.
    
    Parameters
    ----------
    element : bs4.element.Tag
        The BeautifulSoup element to extract properties from.
    url : str, optional
        The page URL for context.
        
    Returns
    -------
    dict
        Dictionary containing the element's unique properties.
    """
    properties = {
        # Basic element info
        "tag_name": element.name,
        "attributes": dict(element.attrs) if hasattr(element, 'attrs') else {},
        "text": (element.get_text(strip=True) or "")[:500],  # Limit text length
        "direct_text": _get_direct_text(element)[:200],
        
        # Structural info
        "path": _get_element_path(element),
        "depth": _get_element_depth(element),
        "sibling_index": _get_sibling_index(element),
        
        # Parent info
        "parent_name": None,
        "parent_attribs": {},
        "parent_text": "",
        
        # Grandparent info  
        "grandparent_name": None,
        "grandparent_attribs": {},
        
        # Children info
        "children_tags": [],
        "children_count": 0,
        
        # Metadata
        "url": url,
        "timestamp": datetime.now().isoformat(),
    }
    
    # Extract parent info
    parent = element.parent
    if parent and parent.name != '[document]':
        properties["parent_name"] = parent.name
        properties["parent_attribs"] = dict(parent.attrs) if hasattr(parent, 'attrs') else {}
        properties["parent_text"] = _get_direct_text(parent)[:100]
        
        # Extract grandparent info
        grandparent = parent.parent
        if grandparent and grandparent.name != '[document]':
            properties["grandparent_name"] = grandparent.name
            properties["grandparent_attribs"] = dict(grandparent.attrs) if hasattr(grandparent, 'attrs') else {}
    
    # Extract children info
    if hasattr(element, 'children'):
        children = [c for c in element.children if hasattr(c, 'name') and c.name]
        properties["children_tags"] = [c.name for c in children[:10]]  # Limit to first 10
        properties["children_count"] = len(children)
    
    # Generate unique hash for quick comparison
    hash_content = f"{properties['tag_name']}:{properties['path']}:{properties.get('text', '')[:100]}"
    properties["hash"] = hashlib.sha256(hash_content.encode()).hexdigest()[:16]
    
    return properties


def _get_direct_text(element) -> str:
    """Get only the direct text content of an element, not from children."""
    if not hasattr(element, 'children'):
        return ""
    
    texts = []
    for child in element.children:
        if isinstance(child, str):
            text = child.strip()
            if text:
                texts.append(text)
        elif hasattr(child, 'name') and child.name is None:  # NavigableString
            text = str(child).strip()
            if text:
                texts.append(text)
    
    return ' '.join(texts)


def _get_element_path(element) -> str:
    """Get the DOM path of an element (tag names from root to element)."""
    path_parts = []
    current = element
    
    while current and hasattr(current, 'name') and current.name and current.name != '[document]':
        path_parts.insert(0, current.name)
        current = current.parent
    
    return '/'.join(path_parts)


def _get_element_depth(element) -> int:
    """Get the depth of an element in the DOM tree."""
    depth = 0
    current = element
    
    while current and hasattr(current, 'parent') and current.parent:
        if hasattr(current.parent, 'name') and current.parent.name == '[document]':
            break
        depth += 1
        current = current.parent
    
    return depth


def _get_sibling_index(element) -> int:
    """Get the index of this element among its siblings with the same tag."""
    if not element.parent:
        return 0
    
    index = 0
    for sibling in element.parent.children:
        if hasattr(sibling, 'name') and sibling.name == element.name:
            if sibling == element:
                return index
            index += 1
    
    return index
