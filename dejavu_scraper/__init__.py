__version__ = "2.0.0"

from dejavu_scraper.dejavu_scraper import DejavuScraper

# Adaptive extraction components
from dejavu_scraper.adaptive_storage import (
    AdaptiveStorage,
    extract_element_properties,
)
from dejavu_scraper.adaptive_matcher import (
    AdaptiveMatcher,
    FuzzyTextMatcher,
)

# Advanced extractors
from dejavu_scraper.extractors import (
    SmartExtractor,
    PatternDetector,
    TableParser,
    StructuredDataExtractor,
    PaginationDetector,
    RegexExtractor,
    TextCleaner,
)

# Backward compatibility alias
AutoScraper = DejavuScraper

__all__ = [
    '__version__',
    'DejavuScraper',
    'AutoScraper',  # Backward compatibility
    'AdaptiveStorage',
    'AdaptiveMatcher',
    'FuzzyTextMatcher',
    'extract_element_properties',
    # Advanced extractors
    'SmartExtractor',
    'PatternDetector',
    'TableParser',
    'StructuredDataExtractor',
    'PaginationDetector',
    'RegexExtractor',
    'TextCleaner',
]