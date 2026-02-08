import hashlib
import json
import logging
import re
import sqlite3
import os
import time
import copy
import tempfile
import shutil
import warnings
from collections import defaultdict
from html import unescape
from urllib.parse import urljoin, urlparse

import requests
from requests.adapters import HTTPAdapter
try:
    from urllib3.util.retry import Retry
except ImportError:
    from requests.packages.urllib3.util.retry import Retry

from .beautifulsoup4.bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

from dejavu_scraper.utils import (
    FuzzyText,
    ResultItem,
    get_non_rec_text,
    normalize,
    text_match,
    unique_hashable,
    unique_stack_list,
)

# Import adaptive extraction modules
from dejavu_scraper.adaptive_storage import (
    AdaptiveStorage,
    extract_element_properties,
)
from dejavu_scraper.adaptive_matcher import (
    AdaptiveMatcher,
    FuzzyTextMatcher,
)

# Import advanced extractors
from dejavu_scraper.extractors import (
    SmartExtractor,
    PatternDetector,
    TableParser,
    StructuredDataExtractor,
    PaginationDetector,
    RegexExtractor,
    TextCleaner,
)


# Pre-compiled date regex pattern for _calculate_field_similarity (avoids re.compile in hot loop)
_DATE_MONTH_NAMES = [
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december',
    'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'
]
_DATE_REGEX = re.compile(
    r'\b(?:' + '|'.join(_DATE_MONTH_NAMES) + r')\b'
    r'|\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b'
    r'|\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b',
    re.IGNORECASE
)

# Maximum response size (10 MB) to prevent memory exhaustion
_MAX_RESPONSE_SIZE = 10 * 1024 * 1024

# Pre-compiled regexes for content type detection (avoids re.compile in hot loops)
_CONTENT_PRICE_RE = re.compile(
    r'[$\u20ac\u00a3\u00a5\u20b9]\s*[\d,]+\.?\d*|[\d,]+\.?\d*\s*[$\u20ac\u00a3\u00a5\u20b9]'
)
_CONTENT_RATING_RE = re.compile(r'\d+\.?\d*\s*/\s*\d+')
_CONTENT_URL_RE = re.compile(r'https?://')


class DejavuScraper:
    """
    DejavuScraper : A Smart, Automatic, Fast and Lightweight Web Scraper for Python.
    DejavuScraper automatically learns a set of rules required to extract the needed content
        from a web page. So the programmer doesn't need to explicitly construct the rules.

    Now enhanced with ADAPTIVE EXTRACTION capabilities:
        - Elements can be relocated even after website structure changes
        - Similarity-based matching algorithms find elements by their properties
        - Automatic saving and retrieval of element fingerprints

    Attributes
    ----------
    stack_list: list
        List of rules learned by DejavuScraper
    adaptive: bool
        Enable/disable adaptive extraction mode
    adaptive_storage: AdaptiveStorage
        Storage backend for element properties

    Methods
    -------
    build() - Learns a set of rules represented as stack_list based on the wanted_list,
        which can be reused for scraping similar elements from other web pages in the future.
    get_result_similar() - Gets similar results based on the previously learned rules.
    get_result_exact() - Gets exact results based on the previously learned rules.
    get_results() - Gets exact and similar results based on the previously learned rules.
    save() - Serializes the stack_list as JSON and saves it to disk.
    load() - De-serializes the JSON representation of the stack_list and loads it back.
    remove_rules() - Removes one or more learned rule[s] from the stack_list.
    keep_rules() - Keeps only the specified learned rules in the stack_list and removes the others.
    
    NEW Adaptive Methods:
    ---------------------
    adaptive_save() - Save element properties for later adaptive matching.
    adaptive_find() - Find elements using adaptive matching even after structure changes.
    find_similar_elements() - Find elements similar to a reference element.
    """

    request_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    def __init__(self, stack_list=None, adaptive=False, min_similarity=0.5,
                 rate_limit=0, max_retries=3, retry_backoff=1.0):
        """
        Initialize DejavuScraper.
        
        Parameters
        ----------
        stack_list : list, optional
            Pre-existing rules to use.
        adaptive : bool, optional
            Enable adaptive extraction mode. Default is False.
        min_similarity : float, optional
            Minimum similarity score (0-1) for adaptive matching. Default is 0.5.
        rate_limit : float, optional
            Minimum seconds between requests to the same domain. 0 = no limit.
        max_retries : int, optional
            Number of retries on transient HTTP errors (5xx, timeouts). Default is 3.
        retry_backoff : float, optional
            Backoff factor for retries (seconds). Default is 1.0.
        """
        self.stack_list = stack_list or []
        self.group_rules = []
        self.adaptive = adaptive
        self.min_similarity = min_similarity
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        
        # Request session with connection pooling and retry logic
        self._session = None
        
        # Rate limiting state: {domain: last_request_timestamp}
        self._last_request_time = {}
        
        # Initialize adaptive components
        self._adaptive_storage = None
        self._adaptive_matcher = None
        
        # Content fingerprints for flexible cross-site extraction
        self._content_fingerprints = {}
        
        if adaptive:
            self._init_adaptive()

    def close(self):
        """Close the underlying requests.Session and free resources."""
        if self._session is not None:
            self._session.close()
            self._session = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False

    def __del__(self):
        self.close()
    
    def _get_session(self):
        """Get or create a requests.Session with retry logic and connection pooling."""
        if self._session is None:
            self._session = requests.Session()
            self._session.headers.update(self.request_headers)
            
            # Configure retry strategy
            retry_strategy = Retry(
                total=self.max_retries,
                backoff_factor=self.retry_backoff,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET", "HEAD"],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy, pool_maxsize=10)
            self._session.mount("http://", adapter)
            self._session.mount("https://", adapter)
        return self._session
    
    def _apply_rate_limit(self, url):
        """Apply rate limiting per domain."""
        if self.rate_limit <= 0:
            return
        
        domain = urlparse(url).netloc
        now = time.monotonic()
        last_time = self._last_request_time.get(domain, 0)
        elapsed = now - last_time
        
        if elapsed < self.rate_limit:
            sleep_time = self.rate_limit - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s for {domain}")
            time.sleep(sleep_time)
        
        self._last_request_time[domain] = time.monotonic()
    
    
    def _init_adaptive(self):
        """Initialize adaptive extraction components."""
        if self._adaptive_storage is None:
            self._adaptive_storage = AdaptiveStorage()
        if self._adaptive_matcher is None:
            self._adaptive_matcher = AdaptiveMatcher(min_similarity=self.min_similarity)
    
    @property
    def adaptive_storage(self):
        """Get the adaptive storage instance, initializing if needed."""
        if self._adaptive_storage is None:
            self._init_adaptive()
        return self._adaptive_storage

    # ==================== CONTENT FINGERPRINTING ====================

    @staticmethod
    def _build_content_fingerprint(texts):
        """Build a content fingerprint from sample texts for flexible cross-site extraction.

        A content fingerprint captures the *shape* of data (length, word count,
        digit ratio, content type like price/name/description) rather than the
        HTML structure.  This allows get_result_flexible() to find matching
        content on pages with completely different tag hierarchies.
        """
        if not texts:
            return None

        lengths = [len(t) for t in texts]
        word_counts = [len(t.split()) for t in texts]

        digit_ratios = []
        alpha_ratios = []
        for t in texts:
            tlen = max(len(t), 1)
            digit_ratios.append(sum(c.isdigit() for c in t) / tlen)
            alpha_ratios.append(sum(c.isalpha() for c in t) / tlen)

        has_currency = any(any(c in '$\u20ac\u00a3\u00a5\u20b9' for c in t) for t in texts)

        content_type = DejavuScraper._detect_content_type_static(texts)
        avg_len = sum(lengths) / len(lengths)

        return {
            'sample_texts': texts[:10],
            'count': len(texts),
            'avg_length': avg_len,
            'min_length': min(lengths),
            'max_length': max(lengths),
            'std_length': (sum((l - avg_len) ** 2 for l in lengths) / len(lengths)) ** 0.5,
            'avg_word_count': sum(word_counts) / len(word_counts),
            'min_word_count': min(word_counts),
            'max_word_count': max(word_counts),
            'content_type': content_type,
            'has_currency': has_currency,
            'avg_digit_ratio': sum(digit_ratios) / len(digit_ratios),
            'avg_alpha_ratio': sum(alpha_ratios) / len(alpha_ratios),
        }

    @staticmethod
    def _detect_content_type_static(texts):
        """Classify what type of content a list of texts represents."""
        n = len(texts)
        if n == 0:
            return 'unknown'

        if sum(1 for t in texts if _CONTENT_PRICE_RE.search(t)) > n * 0.5:
            return 'price'
        if sum(1 for t in texts if _CONTENT_RATING_RE.search(t)) > n * 0.5:
            return 'rating'
        if sum(1 for t in texts if _CONTENT_URL_RE.search(t)) > n * 0.5:
            return 'url'

        avg_len = sum(len(t) for t in texts) / n
        avg_digit = sum(sum(c.isdigit() for c in t) / max(len(t), 1) for t in texts) / n
        if avg_digit > 0.5:
            return 'number'
        if avg_len > 100:
            return 'description'
        if avg_len < 15:
            return 'short_text'
        return 'text'

    def _score_text_against_fingerprint(self, text, fingerprint):
        """Score how well a candidate text matches a learned content fingerprint (0-1)."""
        text_len = len(text)
        text_wc = len(text.split())
        text_max = max(text_len, 1)
        text_digit_ratio = sum(c.isdigit() for c in text) / text_max
        text_alpha_ratio = sum(c.isalpha() for c in text) / text_max
        text_has_currency = any(c in '$\u20ac\u00a3\u00a5\u20b9' for c in text)

        score = 0.0

        # 1. Length similarity (15%)
        if fingerprint['min_length'] <= text_len <= fingerprint['max_length']:
            len_score = 1.0
        else:
            half_min = fingerprint['min_length'] * 0.5
            double_max = fingerprint['max_length'] * 2.0
            if half_min <= text_len <= double_max:
                if text_len < fingerprint['min_length']:
                    len_score = text_len / max(fingerprint['min_length'], 1)
                else:
                    len_score = fingerprint['max_length'] / max(text_len, 1)
            else:
                len_score = 0.0
        score += len_score * 0.15

        # 2. Word count similarity (15%)
        if fingerprint['min_word_count'] <= text_wc <= fingerprint['max_word_count']:
            wc_score = 1.0
        elif text_wc < fingerprint['min_word_count']:
            wc_score = max(0, text_wc / max(fingerprint['min_word_count'], 1))
        else:
            wc_score = max(0, fingerprint['max_word_count'] / max(text_wc, 1))
        score += wc_score * 0.15

        # 3. Content type match (30%) — strongest signal
        text_type = self._detect_content_type_static([text])
        fp_type = fingerprint['content_type']
        if fp_type == text_type:
            type_score = 1.0
        elif fp_type in ('text', 'short_text') and text_type in ('text', 'short_text'):
            type_score = 0.7
        elif fp_type == 'price' and text_has_currency:
            type_score = 0.9
        else:
            type_score = 0.0
        score += type_score * 0.30

        # 4. Digit ratio similarity (15%)
        digit_diff = abs(text_digit_ratio - fingerprint.get('avg_digit_ratio', 0))
        score += max(0, 1 - digit_diff * 3) * 0.15

        # 5. Currency / symbol match (15%)
        fp_currency = fingerprint.get('has_currency', False)
        if fp_currency == text_has_currency:
            currency_score = 1.0
        elif fp_currency and not text_has_currency:
            currency_score = 0.0
        else:
            currency_score = 0.3
        score += currency_score * 0.15

        # 6. Alpha ratio similarity (10%)
        alpha_diff = abs(text_alpha_ratio - fingerprint.get('avg_alpha_ratio', 0.5))
        score += max(0, 1 - alpha_diff * 2) * 0.10

        return score

    def _flexible_extract_with_fingerprint(self, soup, fingerprint, min_score=0.4):
        """Extract texts from *soup* that match a specific content fingerprint."""
        skip_tags = frozenset({
            'html', 'head', 'body', 'script', 'style', 'meta', 'link',
            'br', 'hr', 'noscript', 'iframe', 'svg', 'path',
        })

        # Collect candidate (element, text) pairs — prefer leaf / near-leaf nodes
        candidates = []
        for elem in soup.find_all():
            if elem.name in skip_tags:
                continue
            text = elem.get_text(strip=True)
            if not text:
                continue

            child_tags = [c for c in elem.children
                          if hasattr(c, 'name') and c.name]
            # Pure wrapper (single child owns all the text) — skip
            if len(child_tags) == 1 and child_tags[0].get_text(strip=True) == text:
                continue
            # Large container — skip
            if len(child_tags) > 3:
                continue

            candidates.append((elem, text))

        # Score every candidate
        scored = []
        for elem, text in candidates:
            s = self._score_text_against_fingerprint(text, fingerprint)
            if s >= min_score:
                scored.append((elem, text, s))

        if not scored:
            return []

        # Group by structural position (grandparent_tag, parent_tag, parent_class, elem_tag)
        parent_groups = defaultdict(list)
        for elem, text, s in scored:
            parent = elem.parent
            if parent and hasattr(parent, 'name'):
                pcls = parent.get('class', [])
                pcls = ' '.join(pcls) if isinstance(pcls, list) else str(pcls)
                gp = parent.parent
                gp_name = gp.name if gp and hasattr(gp, 'name') else ''
                key = (gp_name, parent.name, pcls, elem.name)
            else:
                key = ('', '', '', elem.name)
            parent_groups[key].append((elem, text, s))

        # Pick the best group — highest (avg_score * 0.6  +  count_match * 0.4)
        expected = fingerprint.get('count', 1)
        best_group = None
        best_score = 0
        for _key, group in parent_groups.items():
            if len(group) < 2 and expected > 1:
                continue
            avg = sum(x[2] for x in group) / len(group)
            cnt_ratio = min(len(group), expected) / max(len(group), expected)
            gs = avg * 0.6 + cnt_ratio * 0.4
            if gs > best_score:
                best_score = gs
                best_group = group

        if not best_group:
            # Fallback: top-scoring individual candidates
            scored.sort(key=lambda x: x[2], reverse=True)
            best_group = scored[:max(expected, 1)]

        best_group.sort(key=lambda x: x[2], reverse=True)
        return [text for _, text, _ in best_group]

    def get_result_flexible(
        self,
        url=None,
        html=None,
        soup=None,
        request_args=None,
        grouped=False,
        group_by_alias=False,
        unique=None,
        min_content_score=0.4,
    ):
        """Content-aware extraction that works across different HTML structures.

        Unlike ``get_result_similar`` (which matches by tag + attrs + DOM path),
        this method matches by **content patterns** learned during ``build()``.
        If you learned product names from Site A, it can extract all product
        names from Site B even when every HTML tag is different.

        Use this when:
        - The same data appears on pages with different templates / CMS versions.
        - A site redesigns but the textual content stays the same shape.
        - You want to avoid training a separate model per template.

        Parameters
        ----------
        url, html, soup, request_args
            Page to extract from (same semantics as ``get_result_similar``).
        grouped, group_by_alias, unique
            Output formatting options (same semantics as ``get_result_similar``).
        min_content_score : float, optional
            Minimum fingerprint-match score for a candidate element (0-1).
            Lower values are more permissive.  Default is 0.4.

        Returns
        -------
        list or dict
            Extracted texts matching the learned content patterns.

        Example
        -------
        >>> scraper = DejavuScraper()
        >>> scraper.build(html=site_a_html, wanted_list=['Some Product Name'])
        >>> names = scraper.get_result_flexible(html=site_b_html)
        """
        if not self._content_fingerprints:
            return self.get_result_similar(
                url=url, html=html, soup=soup, request_args=request_args,
            )

        if soup is None:
            soup = self._get_soup(url=url, html=html, request_args=request_args)

        all_results = []
        grouped_results = defaultdict(list)

        for fp_key, fingerprint in self._content_fingerprints.items():
            matches = self._flexible_extract_with_fingerprint(
                soup, fingerprint, min_content_score,
            )
            alias = fingerprint.get('alias', fp_key)
            if grouped or group_by_alias:
                key = alias if group_by_alias else fp_key
                grouped_results[key].extend(matches)
            else:
                all_results.extend(matches)

        if grouped or group_by_alias:
            for key in grouped_results:
                if unique is None or unique:
                    grouped_results[key] = unique_hashable(grouped_results[key])
            return dict(grouped_results)

        if unique is None or unique:
            all_results = unique_hashable(all_results)
        return all_results

    # ==================== END CONTENT FINGERPRINTING ====================
    
    @property
    def adaptive_matcher(self):
        """Get the adaptive matcher instance, initializing if needed."""
        if self._adaptive_matcher is None:
            self._init_adaptive()
        return self._adaptive_matcher

    def save(self, file_path, format='auto', include_adaptive=True):
        """
        Serializes the stack_list, group_rules, and adaptive data and saves it to disk.
        
        Supports both JSON and SQLite database formats.

        Parameters
        ----------
        file_path: str
            Path of the output file (.json or .db)
        format: str, optional
            'json' - Save as JSON file
            'db' or 'sqlite' - Save as SQLite database
            'auto' - Detect from file extension (default)
        include_adaptive: bool, optional
            If True, also saves adaptive element properties. Default is True.

        Returns
        -------
        None
        
        Examples
        --------
        >>> scraper.save('model.json')  # Save as JSON
        >>> scraper.save('model.db')    # Save as SQLite
        >>> scraper.save('model.db', format='db')  # Explicit SQLite
        """
        # Determine format
        if format == 'auto':
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.db', '.sqlite', '.sqlite3']:
                format = 'db'
            else:
                format = 'json'
        
        if format in ['db', 'sqlite']:
            self._save_to_db(file_path, include_adaptive)
        else:
            self._save_to_json(file_path, include_adaptive)
    
    def _save_to_json(self, file_path, include_adaptive=True):
        """Save to JSON file with atomic write (temp file + rename)."""
        data = dict(stack_list=self.stack_list)
        
        # Include group rules if present
        if self.group_rules:
            data["group_rules"] = self.group_rules
        
        # Include adaptive data if enabled
        if include_adaptive and self._adaptive_storage is not None:
            adaptive_data = self._adaptive_storage.export_all()
            if adaptive_data:
                data["adaptive_data"] = adaptive_data

        # Include content fingerprints for flexible extraction
        if self._content_fingerprints:
            data["content_fingerprints"] = self._content_fingerprints

        # Atomic write: tmp file then rename (consistent with _save_to_db)
        dir_name = os.path.dirname(os.path.abspath(file_path)) or '.'
        fd, tmp_path = tempfile.mkstemp(suffix='.json', dir=dir_name)
        try:
            with os.fdopen(fd, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, file_path)
        except Exception:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise
    
    def _save_to_db(self, file_path, include_adaptive=True):
        """Save to SQLite database with atomic write (temp file + rename)."""
        # Write to a temp file first, then atomically replace
        dir_name = os.path.dirname(os.path.abspath(file_path))
        fd, tmp_path = tempfile.mkstemp(suffix='.db', dir=dir_name)
        os.close(fd)
        
        conn = None
        try:
            conn = sqlite3.connect(tmp_path)
            cursor = conn.cursor()
            
            # Create tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stack_list (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    stack_id TEXT,
                    alias TEXT,
                    group_index INTEGER,
                    attr_index INTEGER,
                    data TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS group_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id TEXT,
                    data TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS adaptive_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    domain TEXT,
                    identifier TEXT,
                    properties TEXT
                )
            ''')
            
            # Save stack_list
            for stack in self.stack_list:
                cursor.execute('''
                    INSERT INTO stack_list (stack_id, alias, group_index, attr_index, data)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    stack.get('stack_id', ''),
                    stack.get('alias', ''),
                    stack.get('group_index'),
                    stack.get('attr_index'),
                    json.dumps(stack)
                ))
            
            # Save group_rules
            if self.group_rules:
                for rule in self.group_rules:
                    cursor.execute('''
                        INSERT INTO group_rules (group_id, data)
                        VALUES (?, ?)
                    ''', (rule.get('group_id', ''), json.dumps(rule)))
            
            # Save adaptive data
            if include_adaptive and self._adaptive_storage is not None:
                adaptive_data = self._adaptive_storage.export_all()
                for domain, identifiers in adaptive_data.items():
                    for identifier, properties in identifiers.items():
                        cursor.execute('''
                            INSERT INTO adaptive_data (domain, identifier, properties)
                            VALUES (?, ?, ?)
                        ''', (domain, identifier, json.dumps(properties)))
            
            # Save content fingerprints
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS content_fingerprints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fp_key TEXT,
                    data TEXT
                )
            ''')
            for fp_key, fp_data in self._content_fingerprints.items():
                cursor.execute(
                    'INSERT INTO content_fingerprints (fp_key, data) VALUES (?, ?)',
                    (fp_key, json.dumps(fp_data)),
                )

            # Save metadata
            cursor.execute('INSERT INTO metadata (key, value) VALUES (?, ?)',
                          ('version', '1.0'))
            cursor.execute('INSERT INTO metadata (key, value) VALUES (?, ?)',
                          ('adaptive_enabled', str(self.adaptive)))
            
            conn.commit()
            conn.close()
            conn = None
            
            # Atomic replace (os.replace works on Windows even if target exists)
            os.replace(tmp_path, file_path)
            logger.debug(f"Saved model to {file_path}")
            
        except Exception:
            # Clean up temp file on failure
            if conn:
                conn.close()
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            raise

    def load(self, file_path, format='auto', include_adaptive=True):
        """
        Loads the stack_list and adaptive data from a file.
        
        Supports both JSON and SQLite database formats.

        Parameters
        ----------
        file_path: str
            Path of the file to load from (.json or .db)
        format: str, optional
            'json' - Load from JSON file
            'db' or 'sqlite' - Load from SQLite database
            'auto' - Detect from file extension (default)
        include_adaptive: bool, optional
            If True, also loads adaptive element properties. Default is True.

        Returns
        -------
        None
        
        Examples
        --------
        >>> scraper.load('model.json')  # Load from JSON
        >>> scraper.load('model.db')    # Load from SQLite
        """
        # Determine format
        if format == 'auto':
            ext = os.path.splitext(file_path)[1].lower()
            if ext in ['.db', '.sqlite', '.sqlite3']:
                format = 'db'
            else:
                format = 'json'
        
        if format in ['db', 'sqlite']:
            self._load_from_db(file_path, include_adaptive)
        else:
            self._load_from_json(file_path, include_adaptive)
    
    def _load_from_json(self, file_path, include_adaptive=True):
        """Load from JSON file."""
        with open(file_path, "r") as f:
            data = json.load(f)

        # for backward compatibility
        if isinstance(data, list):
            self.stack_list = data
            return 

        self.stack_list = data.get("stack_list", [])
        
        # Load group rules if present
        if "group_rules" in data:
            self.group_rules = data["group_rules"]
        
        # Load adaptive data if present and enabled
        if include_adaptive and "adaptive_data" in data:
            self._init_adaptive()
            self._adaptive_storage.import_all(data["adaptive_data"])

        # Load content fingerprints
        if "content_fingerprints" in data:
            self._content_fingerprints = data["content_fingerprints"]

    def _load_from_db(self, file_path, include_adaptive=True):
        """Load from SQLite database."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Database file not found: {file_path}")
        
        conn = sqlite3.connect(file_path)
        try:
            cursor = conn.cursor()
            
            # Load stack_list (with safety for missing tables)
            try:
                cursor.execute('SELECT data FROM stack_list')
                self.stack_list = [json.loads(row[0]) for row in cursor.fetchall()]
            except sqlite3.OperationalError:
                self.stack_list = []
            
            # Load group_rules
            try:
                cursor.execute('SELECT data FROM group_rules')
                rows = cursor.fetchall()
                if rows:
                    self.group_rules = [json.loads(row[0]) for row in rows]
            except sqlite3.OperationalError:
                pass  # table may not exist in older databases
            
            # Load adaptive data
            if include_adaptive:
                try:
                    cursor.execute('SELECT domain, identifier, properties FROM adaptive_data')
                    rows = cursor.fetchall()
                    if rows:
                        self._init_adaptive()
                        adaptive_data = defaultdict(dict)
                        for domain, identifier, properties in rows:
                            adaptive_data[domain][identifier] = json.loads(properties)
                        self._adaptive_storage.import_all(dict(adaptive_data))
                except sqlite3.OperationalError:
                    pass  # table may not exist in older databases

            # Load content fingerprints
            try:
                cursor.execute('SELECT fp_key, data FROM content_fingerprints')
                for fp_key, data in cursor.fetchall():
                    self._content_fingerprints[fp_key] = json.loads(data)
            except sqlite3.OperationalError:
                pass  # table may not exist in older databases
        finally:
            conn.close()

    # ==================== ADAPTIVE EXTRACTION METHODS ====================
    
    def adaptive_save(self, element, identifier, url=None):
        """
        Save element properties for later adaptive matching.
        
        This allows the element to be found again even if the website structure changes.
        
        Parameters
        ----------
        element : bs4.element.Tag
            The BeautifulSoup element to save properties for.
        identifier : str
            Unique identifier for this element (e.g., 'product_title', 'price').
        url : str, optional
            The page URL. Used to isolate data per domain.
            
        Returns
        -------
        bool
            True if save was successful.
            
        Example
        -------
        >>> scraper = AutoScraper(adaptive=True)
        >>> soup = scraper._get_soup(url='https://example.com')
        >>> title = soup.select_one('h1.product-title')
        >>> scraper.adaptive_save(title, 'product_title', url='https://example.com')
        """
        self._init_adaptive()
        
        domain = AdaptiveStorage.extract_domain(url or "")
        properties = extract_element_properties(element, url or "")
        
        return self.adaptive_storage.save(domain, identifier, properties)
    
    def adaptive_find(
        self, 
        identifier, 
        url=None, 
        html=None, 
        soup=None,
        request_args=None,
        selector=None,
        min_similarity=None
    ):
        """
        Find elements using adaptive matching - works even after website structure changes.
        
        This method retrieves previously saved element properties and finds the best
        matching element(s) on the current page using similarity algorithms.
        
        Parameters
        ----------
        identifier : str
            The identifier used when saving the element with adaptive_save().
        url : str, optional
            URL of the page to search. Either url, html, or soup must be provided.
        html : str, optional
            HTML string to search.
        soup : BeautifulSoup, optional
            Pre-parsed BeautifulSoup object.
        request_args : dict, optional
            Additional request parameters for fetching URL.
        selector : str, optional
            CSS selector to narrow down candidates. If None, searches all elements.
        min_similarity : float, optional
            Override the default minimum similarity score.
            
        Returns
        -------
        tuple
            (best_match_element, similarity_score, all_matches)
            Returns (None, 0, []) if no match found.
            
        Example
        -------
        >>> # First time: save the element
        >>> scraper = AutoScraper(adaptive=True)
        >>> soup = scraper._get_soup(url='https://example.com')
        >>> title = soup.select_one('h1.product-title')
        >>> scraper.adaptive_save(title, 'product_title', url='https://example.com')
        >>>
        >>> # Later, even if structure changes:
        >>> element, score, matches = scraper.adaptive_find(
        ...     'product_title', 
        ...     url='https://example.com'
        ... )
        >>> if element:
        ...     print(f"Found with {score*100:.1f}% confidence: {element.text}")
        """
        self._init_adaptive()
        
        domain = AdaptiveStorage.extract_domain(url or "")
        
        # Retrieve stored properties
        stored_props = self.adaptive_storage.retrieve(domain, identifier)
        if not stored_props:
            return None, 0.0, []
        
        # Get soup if not provided
        if soup is None:
            soup = self._get_soup(url=url, html=html, request_args=request_args)
        
        # Get candidate elements
        if selector:
            candidates = soup.select(selector)
        else:
            # Search through all elements with the same tag
            tag_name = stored_props.get('tag_name', 'div')
            candidates = soup.find_all(tag_name)
        
        # Update matcher min_similarity if provided
        if min_similarity is not None:
            original_min = self.adaptive_matcher.min_similarity
            self.adaptive_matcher.min_similarity = min_similarity
        
        # Find best match
        best_match, score, all_matches = self.adaptive_matcher.find_best_match(
            stored_props,
            candidates,
            extract_element_properties,
            url or ""
        )
        
        # Restore original min_similarity
        if min_similarity is not None:
            self.adaptive_matcher.min_similarity = original_min
        
        return best_match, score, all_matches
    
    def adaptive_build(
        self,
        url=None,
        wanted_list=None,
        wanted_dict=None,
        html=None,
        request_args=None,
        auto_save=True,
        text_fuzz_ratio=1.0,
    ):
        """
        Build rules AND save element properties for adaptive extraction.
        
        This is an enhanced version of build() that also saves element fingerprints
        for future adaptive matching.
        
        Parameters
        ----------
        url : str, optional
            URL of the target web page.
        wanted_list : list, optional
            List of needed contents to be scraped.
        wanted_dict : dict, optional
            Dict of needed contents with aliases as keys.
        html : str, optional
            HTML string instead of URL.
        request_args : dict, optional
            Additional request parameters.
        auto_save : bool, optional
            If True, automatically save element properties for adaptive matching.
        text_fuzz_ratio : float, optional
            Fuzziness ratio threshold for text matching.
            
        Returns
        -------
        list
            List of similar results found.
        """
        self._init_adaptive()
        
        # Call original build
        result = self.build(
            url=url,
            wanted_list=wanted_list,
            wanted_dict=wanted_dict,
            html=html,
            request_args=request_args,
            update=False,
            text_fuzz_ratio=text_fuzz_ratio,
        )
        
        if auto_save and self.stack_list:
            # Reuse cached HTML from build() to avoid double network fetch
            cached_html = getattr(self, '_last_html', None)
            if cached_html:
                soup = BeautifulSoup(cached_html, "html.parser")
            else:
                soup = self._get_soup(url=url, html=html, request_args=request_args)
            
            domain = AdaptiveStorage.extract_domain(url or "")
            
            # Save properties for each learned rule
            for stack in self.stack_list:
                # Find the element using this stack
                elements = self._get_result_with_stack(stack, soup, url, 1.0)
                if elements:
                    element = elements[0]
                    # Get the actual BeautifulSoup element
                    if hasattr(element, 'text'):
                        # Find the element in soup that matches this text
                        for el in soup.find_all():
                            if el.get_text(strip=True) == element.text:
                                identifier = stack.get('alias') or stack.get('stack_id')
                                self.adaptive_storage.save(
                                    domain, 
                                    identifier,
                                    extract_element_properties(el, url or "")
                                )
                                break
        
        return result
    
    def find_similar_elements(
        self,
        reference_element,
        url=None,
        html=None,
        soup=None,
        request_args=None,
        similarity_threshold=0.6
    ):
        """
        Find elements similar to a reference element on the page.
        
        This is useful for finding all products in a list when you have one product,
        or finding all items in a table when you have one row.
        
        Parameters
        ----------
        reference_element : bs4.element.Tag
            The reference element to find similar elements for.
        url : str, optional
            URL of the page to search.
        html : str, optional
            HTML string to search.
        soup : BeautifulSoup, optional
            Pre-parsed BeautifulSoup object.
        request_args : dict, optional
            Additional request parameters.
        similarity_threshold : float, optional
            Minimum similarity score to include in results. Default is 0.6.
            
        Returns
        -------
        list
            List of (element, similarity_score) tuples, sorted by score descending.
            
        Example
        -------
        >>> scraper = AutoScraper(adaptive=True)
        >>> soup = scraper._get_soup(url='https://example.com/products')
        >>> first_product = soup.select_one('.product-item')
        >>> similar = scraper.find_similar_elements(first_product, soup=soup)
        >>> print(f"Found {len(similar)} similar products")
        """
        self._init_adaptive()
        
        if soup is None:
            soup = self._get_soup(url=url, html=html, request_args=request_args)
        
        # Get all elements in the soup
        all_elements = list(soup.find_all())
        
        return self.adaptive_matcher.find_similar_elements(
            reference_element,
            all_elements,
            extract_element_properties,
            url or "",
            similarity_threshold
        )
    
    def get_result_adaptive(
        self,
        url=None,
        html=None,
        request_args=None,
        identifiers=None,
        min_similarity=None,
        grouped=False,
        group_by_alias=False,
        group_by_identifier=False,
    ):
        """
        Get results using adaptive matching for multiple saved identifiers.
        
        Parameters
        ----------
        url : str, optional
            URL of the page to search.
        html : str, optional
            HTML string to search.
        request_args : dict, optional
            Additional request parameters.
        identifiers : list, optional
            List of identifiers to search for. If None, searches all saved identifiers.
        min_similarity : float, optional
            Override the default minimum similarity score.
        grouped : bool, optional
            If True, returns a dict grouped by identifier (for compatibility).
        group_by_alias : bool, optional
            If True, returns a dict grouped by alias (for compatibility).
        group_by_identifier : bool, optional
            If True, returns a dict grouped by identifier.
            
        Returns
        -------
        list or dict
            List of text values, or dict if grouped.
        """
        self._init_adaptive()
        
        domain = AdaptiveStorage.extract_domain(url or "")
        soup = self._get_soup(url=url, html=html, request_args=request_args)
        
        if identifiers is None:
            identifiers = self.adaptive_storage.list_identifiers(domain)
        
        results = []
        grouped_results = defaultdict(list)
        
        # Use grouped or group_by_alias or group_by_identifier
        should_group = grouped or group_by_alias or group_by_identifier
        
        for identifier in identifiers:
            element, score, _ = self.adaptive_find(
                identifier,
                soup=soup,
                url=url,
                min_similarity=min_similarity
            )
            
            if element:
                text = element.get_text(strip=True) if hasattr(element, 'get_text') else str(element)
                if text:
                    if should_group:
                        grouped_results[identifier].append(text)
                    else:
                        results.append(text)
        
        return dict(grouped_results) if should_group else results

    # ==================== END ADAPTIVE EXTRACTION METHODS ====================
    
    # ==================== GROUPED EXTRACTION METHODS ====================
    
    def _find_common_container(self, elements):
        """
        Find the common parent container for a list of elements.
        
        Parameters
        ----------
        elements : list
            List of BeautifulSoup elements
            
        Returns
        -------
        bs4.element.Tag or None
            The common parent container
        """
        if not elements:
            return None
        
        if len(elements) == 1:
            return elements[0].parent
        
        # Get all ancestors of first element
        ancestors = []
        parent = elements[0].parent
        while parent:
            ancestors.append(parent)
            parent = parent.parent
        
        # Find common ancestor with all other elements
        for ancestor in ancestors:
            is_common = True
            for elem in elements[1:]:
                if not ancestor in elem.parents:
                    is_common = False
                    break
            if is_common:
                return ancestor
        
        return None
    
    def _find_similar_containers(self, soup, container):
        """
        Find containers similar to the given container (siblings with same structure).
        
        Parameters
        ----------
        soup : BeautifulSoup
            The parsed HTML
        container : bs4.element.Tag
            The reference container
            
        Returns
        -------
        list
            List of similar containers
        """
        if not container:
            return []
        
        parent = container.parent
        if not parent:
            return [container]
        
        # Find siblings with same tag and similar attributes
        similar = parent.find_all(
            container.name,
            attrs=self._get_valid_attrs(container),
            recursive=False
        )
        
        return similar if similar else [container]
    
    def build_grouped(
        self,
        url=None,
        wanted_list=None,
        html=None,
        request_args=None,
        update=False,
        text_fuzz_ratio=1.0,
    ):
        """
        Build rules for grouped extraction where each inner list represents one item's attributes.
        
        This method learns to extract items as groups - for example, extracting
        product name, price, and link together as a single unit.
        
        Parameters
        ----------
        url : str, optional
            URL of the target web page.
        wanted_list : list of lists, required
            A list of lists where each inner list contains attributes that belong together.
            Example: [['iPhone 15 Pro', '$999', 'https://apple.com'], ['Galaxy S24', '$899', 'https://samsung.com']]
        html : str, optional
            HTML string to parse.
        request_args : dict, optional
            Request parameters for fetching the URL.
        update : bool, optional
            If True, add to existing rules. Default is False.
        text_fuzz_ratio : float, optional
            Fuzzy matching ratio. Default is 1.0.
            
        Returns
        -------
        list of lists
            Grouped results extracted from the page
        """
        if not wanted_list:
            raise ValueError("wanted_list is required for grouped extraction")
        
        # Validate wanted_list format
        if not all(isinstance(item, (list, tuple)) for item in wanted_list):
            raise ValueError("wanted_list must be a list of lists/tuples for grouped extraction")
        
        soup = self._get_soup(url=url, html=html, request_args=request_args)
        
        if not update:
            self.stack_list = []
            if self.adaptive and self._adaptive_storage is not None:
                domain = AdaptiveStorage.extract_domain(url or "")
                self._adaptive_storage.clear_domain(domain)
        
        # Store group rules
        group_rules = []
        all_results = []
        
        # Process each group in wanted_list
        for group_idx, wanted_group in enumerate(wanted_list):
            group_elements = []
            group_stacks = []
            
            for attr_idx, wanted in enumerate(wanted_group):
                wanted = normalize(wanted)
                children = self._get_children(soup, wanted, url, text_fuzz_ratio)
                
                if children:
                    child = children[0]  # Take the first matching element
                    result, stack = self._get_result_for_child(child, soup, url)
                    stack["alias"] = f"group_{group_idx}_attr_{attr_idx}"
                    stack["group_index"] = group_idx
                    stack["attr_index"] = attr_idx
                    self.stack_list.append(stack)
                    group_elements.append(child)
                    group_stacks.append(stack)
            
            if group_elements:
                # Find common container for this group
                container = self._find_common_container(group_elements)
                
                group_rule = {
                    "group_id": f"group_{group_idx}",
                    "container_tag": container.name if container else None,
                    "container_attrs": self._get_valid_attrs(container) if container else {},
                    "attr_count": len(wanted_group),
                    "stack_ids": [s.get("stack_id") for s in group_stacks]
                }
                group_rules.append(group_rule)
                
                # Store for adaptive if enabled
                if self.adaptive:
                    self._init_adaptive()
                    domain = AdaptiveStorage.extract_domain(url or "")
                    
                    for idx, (elem, stack) in enumerate(zip(group_elements, group_stacks)):
                        identifier = f"group_{group_idx}_attr_{idx}"
                        props = extract_element_properties(elem, url or "")
                        props["group_id"] = group_idx
                        props["attr_index"] = idx
                        self._adaptive_storage.save(domain, identifier, props)
        
        # Store group rules in a special attribute
        if not hasattr(self, 'group_rules'):
            self.group_rules = []
        self.group_rules = group_rules
        
        # Get grouped results
        all_results = self.get_result_grouped(html=html, url=url)
        
        self.stack_list = unique_stack_list(self.stack_list)
        
        return all_results
    
    def get_result_grouped(
        self,
        url=None,
        html=None,
        soup=None,
        request_args=None,
        attr_fuzz_ratio=1.0,
        output_format="list",
    ):
        """
        Get results as grouped items (list of lists or list of tuples).
        
        Parameters
        ----------
        url : str, optional
            URL of the target web page.
        html : str, optional
            HTML string to parse.
        soup : BeautifulSoup, optional
            Pre-parsed soup object.
        request_args : dict, optional
            Request parameters.
        attr_fuzz_ratio : float, optional
            Fuzzy matching ratio for attributes.
        output_format : str, optional
            'list' for list of lists, 'tuple' for list of tuples. Default is 'list'.
            
        Returns
        -------
        list
            List of lists or list of tuples, where each inner list/tuple represents one item
        """
        if not soup:
            soup = self._get_soup(url=url, html=html, request_args=request_args)
        
        # Group stacks by their group_index
        grouped_stacks = defaultdict(list)
        ungrouped_stacks = []
        
        for stack in self.stack_list:
            if "group_index" in stack:
                grouped_stacks[stack["group_index"]].append(stack)
            else:
                ungrouped_stacks.append(stack)
        
        results = []
        seen_results = set()  # Track unique results to avoid duplicates
        
        if grouped_stacks:
            # Get attribute count
            attr_count = 0
            for stacks in grouped_stacks.values():
                for stack in stacks:
                    attr_count = max(attr_count, stack.get("attr_index", 0) + 1)
            
            # Build a signature for each attribute position (tag, class pattern)
            attr_signatures = {}
            for stacks in grouped_stacks.values():
                for stack in stacks:
                    attr_idx = stack.get("attr_index", 0)
                    if attr_idx not in attr_signatures:
                        # Stack has 'content' key which contains the tag/attr hierarchy
                        content = stack.get('content', [])
                        last_item = content[-1] if content else None
                        
                        attr_signatures[attr_idx] = {
                            'full_stack': stack,  # Keep the full stack for extraction
                            'wanted_attr': stack.get('wanted_attr', ''),
                            'tag': last_item[0] if last_item else '',
                            'attrs': last_item[1] if last_item and len(last_item) > 1 else {},
                        }
            
            # IMPROVED APPROACH: Find containers and extract from each
            # Step 1: Find all elements matching each attribute pattern
            attr_elements = defaultdict(list)  # attr_idx -> list of (container_id, value, element)
            
            for attr_idx, sig in attr_signatures.items():
                # Use the full stack for extraction
                found = self._get_result_with_stack(sig['full_stack'], soup, url or "", attr_fuzz_ratio, contain_sibling_leaves=True)
                
                for item in found:
                    if item.text:
                        # Find the container for this element (go up to find a repeating pattern)
                        elem = getattr(item, 'element', None)
                        container_id = self._find_item_container_id(elem, soup) if elem else hash(item.text)
                        attr_elements[attr_idx].append((container_id, item.text, elem))
            
            # Step 2: Group by container_id
            containers = defaultdict(lambda: {i: "" for i in range(attr_count)})
            
            for attr_idx, items in attr_elements.items():
                for container_id, text, elem in items:
                    if container_id and not containers[container_id][attr_idx]:
                        containers[container_id][attr_idx] = text
            
            # Step 3: Build results, maintaining order
            # Sort containers by their first appearance in document
            sorted_containers = sorted(containers.items(), key=lambda x: x[0] if isinstance(x[0], int) else 0)
            
            for container_id, attr_values in sorted_containers:
                item = [attr_values[i] for i in range(attr_count)]
                
                if any(item):  # Only add if at least one value exists
                    item_key = tuple(item)
                    if item_key not in seen_results:
                        seen_results.add(item_key)
                        if output_format == "tuple":
                            results.append(tuple(item))
                        else:
                            results.append(item)
        else:
            # Fallback to regular extraction if no grouped stacks
            for stack in self.stack_list:
                found = self._get_result_with_stack(stack, soup, url or "", attr_fuzz_ratio)
                for item in found:
                    if item.text:
                        if output_format == "tuple":
                            results.append((item.text,))
                        else:
                            results.append([item.text])
        
        # If adaptive mode enabled and no results, try adaptive matching
        if self.adaptive and not results:
            results = self._get_result_grouped_adaptive(url, html, soup, output_format)
        
        return results
    
    def _find_item_container_id(self, element, soup):
        """
        Find the container ID for an element by walking up to a repeating parent structure.
        
        This is used to group elements that belong to the same item (e.g., product card).
        Returns a unique ID for the container.
        """
        if not element or not hasattr(element, 'parent'):
            return id(element)
        
        # Walk up the DOM tree looking for a good container
        current = element
        container_levels = 3  # How many levels to go up
        
        for _ in range(container_levels):
            parent = current.parent if hasattr(current, 'parent') else None
            if not parent:
                break
            
            # Check if this parent has siblings with similar structure
            # (indicating it's an item in a list)
            siblings_with_same_tag = []
            grandparent = parent.parent if hasattr(parent, 'parent') else None
            
            if grandparent:
                for sibling in grandparent.children:
                    if hasattr(sibling, 'name') and sibling.name == parent.name:
                        siblings_with_same_tag.append(sibling)
            
            # If there are multiple siblings with same tag, this is likely our container
            if len(siblings_with_same_tag) >= 2:
                return id(parent)
            
            current = parent
        
        # Fallback: use the element's immediate parent
        return id(element.parent) if hasattr(element, 'parent') and element.parent else id(element)

    def _get_result_grouped_adaptive(self, url, html, soup, output_format="list"):
        """
        Get grouped results using adaptive matching with PROPER FIELD ALIGNMENT.
        
        This method finds repeating container structures and extracts attributes from within,
        matching fields by similarity to handle missing/optional fields correctly.
        
        Parameters
        ----------
        url : str
            URL for domain extraction
        html : str
            HTML content
        soup : BeautifulSoup
            Parsed soup
        output_format : str
            'list' or 'tuple'
            
        Returns
        -------
        list
            Grouped results with properly aligned fields (empty string for missing)
        """
        self._init_adaptive()
        
        # Get domain - use "default" if no URL provided (same as during training)
        domain = AdaptiveStorage.extract_domain(url or "")
        if not soup:
            soup = self._get_soup(url=url, html=html)
        
        identifiers = self._adaptive_storage.list_identifiers(domain)
        
        # If no identifiers for this domain, try "default" domain
        if not identifiers and domain != "default":
            identifiers = self._adaptive_storage.list_identifiers("default")
            domain = "default"
        
        # Group identifiers by attribute position and collect ALL stored properties
        attr_props = {}  # attr_idx -> list of stored properties
        
        for identifier in identifiers:
            if identifier.startswith("group_"):
                parts = identifier.split("_")
                if len(parts) >= 4:
                    attr_idx = int(parts[3])
                    stored = self._adaptive_storage.retrieve(domain, identifier)
                    if stored:
                        if attr_idx not in attr_props:
                            attr_props[attr_idx] = []
                        attr_props[attr_idx].append(stored)
        
        if not attr_props:
            return []
        
        attr_count = max(attr_props.keys()) + 1
        
        # Strategy: Find repeating item containers and match each field by similarity
        containers = self._find_item_containers(soup)
        
        results = []
        seen = set()
        
        for container in containers:
            # Get all candidate elements within this container
            candidates = self._extract_candidates_from_container(container, url)
            
            # Match each attribute position to best matching candidate
            item = []
            used_candidates = set()
            
            for attr_idx in range(attr_count):
                props_list = attr_props.get(attr_idx, [])
                found_value = ""
                best_score = 0
                best_candidate_idx = -1
                
                # Find the best matching candidate for this attribute position
                for candidate_idx, (elem, text, href, cand_props) in enumerate(candidates):
                    if candidate_idx in used_candidates:
                        continue
                    
                    # Calculate similarity with all stored properties for this attr_idx
                    for stored in props_list:
                        score = self._calculate_field_similarity(stored, cand_props, text, href)
                        if score > best_score and score >= 0.3:  # Lower threshold for field matching
                            best_score = score
                            best_candidate_idx = candidate_idx
                            
                            # Determine what value to use
                            wanted_attr = stored.get('wanted_attr', '')
                            if wanted_attr == 'href':
                                found_value = href or ""
                            else:
                                found_value = text or ""
                
                # Mark the best candidate as used
                if best_candidate_idx >= 0:
                    used_candidates.add(best_candidate_idx)
                
                item.append(found_value)
            
            if any(item):  # Only add if at least one value exists
                item_key = tuple(item)
                if item_key not in seen:
                    seen.add(item_key)
                    if output_format == "tuple":
                        results.append(tuple(item))
                    else:
                        results.append(item)
        
        return results
    
    def _find_item_containers(self, soup):
        """
        Find repeating item containers (product cards, article items, etc.)
        
        Returns a list of container elements that likely contain grouped items.
        """
        # Strategy: Find elements that repeat with similar structure
        # Look for common patterns like: article, div.item, li, tr, etc.
        
        container_patterns = defaultdict(list)
        
        for elem in soup.find_all(['article', 'div', 'li', 'tr', 'section']):
            # Skip if no meaningful content
            text = elem.get_text(strip=True)
            if not text or len(text) < 10:
                continue
            
            # Create a signature based on structure
            classes = ' '.join(sorted(elem.get('class', []))) if elem.get('class') else ''
            tag = elem.name
            
            # Count direct children types (filter out None names)
            child_tags = tuple(sorted(c.name for c in elem.children if hasattr(c, 'name') and c.name is not None))
            
            signature = (tag, classes, child_tags)
            container_patterns[signature].append(elem)
        
        # Find the pattern with most repetitions (likely our item containers)
        best_pattern = None
        best_count = 0
        
        for sig, containers in container_patterns.items():
            if len(containers) > best_count and len(containers) >= 2:
                best_count = len(containers)
                best_pattern = sig
        
        if best_pattern:
            return container_patterns[best_pattern]
        
        # Fallback: Look for any repeating parent structure
        parent_groups = defaultdict(list)
        
        for elem in soup.find_all():
            text = elem.get_text(strip=True)
            if text and 10 < len(text) < 500:  # Reasonable content size
                parent = elem.parent
                if parent:
                    parent_key = (parent.name, id(parent))
                    parent_groups[parent_key].append(elem)
        
        # Return largest group
        best_group = []
        for key, elems in parent_groups.items():
            if len(elems) > len(best_group):
                best_group = elems
        
        return best_group if len(best_group) >= 2 else []
    
    def _extract_candidates_from_container(self, container, url):
        """
        Extract all candidate elements from a container with their properties.
        
        Returns list of (element, text, href, properties) tuples.
        """
        candidates = []
        
        for elem in container.find_all():
            # Get text - only direct text content (not from children)
            direct_text = ''.join(elem.find_all(string=True, recursive=False)).strip()
            if not direct_text:
                continue
            
            # Get href if it's a link
            href = elem.get('href', '')
            
            # Extract properties for similarity matching
            props = self._extract_candidate_props(elem, url)
            
            candidates.append((elem, direct_text, href, props))
        
        return candidates
    
    def _extract_candidate_props(self, elem, url):
        """Extract properties from a candidate element for similarity matching."""
        props = {
            'tag_name': elem.name or '',
            'text': elem.get_text(strip=True)[:100] if hasattr(elem, 'get_text') else '',
            'classes': elem.get('class', []),
            'id': elem.get('id', ''),
            'href': elem.get('href', ''),
        }
        
        # Parent info
        if elem.parent:
            props['parent_tag'] = elem.parent.name
            props['parent_classes'] = elem.parent.get('class', [])
        
        return props
    
    def _calculate_field_similarity(self, stored, candidate_props, text, href):
        """
        Calculate similarity between stored field properties and candidate.
        
        This focuses on SEMANTIC/PATTERN similarity for cross-site extraction,
        not just structural similarity.
        """
        score = 0.0
        total_weight = 0.0
        
        stored_text = stored.get('text', '')
        wanted_attr = stored.get('wanted_attr', '')
        stored_tag = stored.get('tag_name', '')
        cand_tag = candidate_props.get('tag_name', '')
        
        # 1. Is this looking for a link/href?
        if wanted_attr == 'href':
            if href:
                score += 0.5  # Strong match if we have an href
            else:
                score += 0.0  # No match but no negative score
            total_weight += 0.5
            return max(0.0, score / total_weight) if total_weight > 0 else 0.0
        
        # 2. Check for heading-like elements (titles)
        heading_tags = {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}
        if stored_tag in heading_tags:
            if cand_tag in heading_tags:
                score += 0.4
            elif text and len(text) < 100:  # Short text could be title
                score += 0.1
            total_weight += 0.4
        
        # 3. Check for date-like patterns (uses pre-compiled _DATE_REGEX)
        stored_has_date = bool(_DATE_REGEX.search(stored_text))
        text_has_date = bool(_DATE_REGEX.search(text)) if text else False
        
        if stored_has_date:
            if text_has_date:
                score += 0.4  # Both have date patterns
            else:
                score += 0.0  # No penalty to avoid negative scores
            total_weight += 0.4
        
        # 4. Check for author-like patterns (By ...)
        stored_has_by = stored_text.lower().startswith('by ')
        text_has_by = text.lower().startswith('by ') if text else False
        
        if stored_has_by:
            if text_has_by:
                score += 0.5  # Both have "By " pattern
            else:
                score += 0.0  # No penalty to avoid negative scores
            total_weight += 0.5
        
        # 5. Check for paragraph/description (longer text)
        if stored_tag == 'p' or len(stored_text) > 50:
            if cand_tag == 'p' or (text and len(text) > 30):
                score += 0.3
            total_weight += 0.3
        
        # 6. Tag similarity bonus
        if stored_tag == cand_tag:
            score += 0.2
        elif stored_tag and cand_tag:
            # Some tags are similar
            similar_groups = [
                {'span', 'time', 'date'},
                {'p', 'div', 'section'},
                {'h1', 'h2', 'h3', 'h4', 'h5', 'h6'},
                {'cite', 'span', 'em', 'strong'}
            ]
            for group in similar_groups:
                if stored_tag in group and cand_tag in group:
                    score += 0.1
                    break
        total_weight += 0.2
        
        # 7. Text length similarity
        if stored_text and text:
            len_ratio = min(len(text), len(stored_text)) / max(len(text), len(stored_text))
            if len_ratio > 0.3:
                score += 0.1 * len_ratio
            total_weight += 0.1
        
        return max(0.0, score / total_weight) if total_weight > 0 else 0.0
    
    # ==================== END GROUPED EXTRACTION METHODS ====================

    def _fetch_html(self, url, request_args=None):
        """Fetch HTML from a URL with session reuse, rate limiting, and validation."""
        if not url:
            raise ValueError("URL is required for fetching HTML")
        
        # Validate URL scheme
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https'):
            raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Only http/https are supported.")
        
        # Don't mutate the caller's dict
        request_args = copy.copy(request_args) if request_args else {}
        
        # Apply rate limiting
        self._apply_rate_limit(url)
        
        # Build headers
        headers = {"Host": parsed.netloc}
        user_headers = request_args.pop("headers", {})
        headers.update(user_headers)
        
        timeout = request_args.pop('timeout', 30)
        
        res = None
        try:
            session = self._get_session()
            logger.debug(f"Fetching {url}")
            res = session.get(url, headers=headers, timeout=timeout, 
                             stream=True, **request_args)
            res.raise_for_status()
            
            # Check response size before reading full body
            content_length = res.headers.get('Content-Length')
            if content_length and int(content_length) > _MAX_RESPONSE_SIZE:
                res.close()
                raise ValueError(f"Response too large ({int(content_length)} bytes). Max: {_MAX_RESPONSE_SIZE}")
            
            # Stream with size limit — avoid loading entire body into RAM
            chunks = []
            bytes_read = 0
            for chunk in res.iter_content(chunk_size=65536):
                bytes_read += len(chunk)
                if bytes_read > _MAX_RESPONSE_SIZE:
                    res.close()
                    raise ValueError(
                        f"Response exceeded {_MAX_RESPONSE_SIZE} bytes during streaming."
                    )
                chunks.append(chunk)
            content = b''.join(chunks)
            
        except requests.exceptions.ConnectionError:
            raise ConnectionError(f"Failed to connect to {url}")
        except requests.exceptions.Timeout:
            raise TimeoutError(f"Request to {url} timed out")
        except requests.exceptions.HTTPError as e:
            status = res.status_code if res is not None else 'unknown'
            raise RuntimeError(f"HTTP error {status} for {url}: {e}")
        
        # Detect encoding
        if res.encoding == "ISO-8859-1" and "ISO-8859-1" not in res.headers.get(
            "Content-Type", ""
        ):
            res.encoding = res.apparent_encoding
        
        html = content.decode(res.encoding or 'utf-8', errors='replace')
        return html

    def _get_soup(self, url=None, html=None, request_args=None):
        """
        Parse HTML using BeautifulSoup.
        Caches the last fetched HTML to avoid redundant network requests.
        """
        if html:
            html = normalize(unescape(html))
        else:
            html = self._fetch_html(url, request_args)
            html = normalize(unescape(html))
        
        # Cache for reuse by adaptive_build etc.
        self._last_html = html
        
        return BeautifulSoup(html, "html.parser")

    @staticmethod
    def _get_valid_attrs(item):
        key_attrs = {"class", "style"}
        attrs = {
            k: v if v != [] else "" for k, v in item.attrs.items() if k in key_attrs
        }

        for attr in key_attrs:
            if attr not in attrs:
                attrs[attr] = ""
        return attrs

    @staticmethod
    def _child_has_text(child, text, url, text_fuzz_ratio):
        child_text = child.getText().strip()

        if text_match(text, child_text, text_fuzz_ratio):
            parent_text = child.parent.getText().strip()
            if child_text == parent_text and child.parent.parent:
                return False

            child.wanted_attr = None
            return True

        if text_match(text, get_non_rec_text(child), text_fuzz_ratio):
            child.is_non_rec_text = True
            child.wanted_attr = None
            return True

        for key, value in child.attrs.items():
            if not isinstance(value, str):
                continue

            value = value.strip()
            if text_match(text, value, text_fuzz_ratio):
                child.wanted_attr = key
                return True

            if key in {"href", "src"}:
                full_url = urljoin(url, value)
                if text_match(text, full_url, text_fuzz_ratio):
                    child.wanted_attr = key
                    child.is_full_url = True
                    return True

        return False

    def _get_children(self, soup, text, url, text_fuzz_ratio):
        children = reversed(soup.findChildren())
        children = [
            x for x in children if self._child_has_text(x, text, url, text_fuzz_ratio)
        ]
        return children

    def build(
        self,
        url=None,
        wanted_list=None,
        wanted_dict=None,
        html=None,
        request_args=None,
        update=False,
        text_fuzz_ratio=1.0,
    ):
        """
        Automatically constructs a set of rules to scrape the specified target[s] from a web page.
            The rules are represented as stack_list.
            
        When adaptive=True is set on the scraper, this method also automatically saves
        element properties for adaptive matching, so elements can be found even after
        website structure changes.

        Parameters:
        ----------
        url: str, optional
            URL of the target web page. You should either pass url or html or both.

        wanted_list: list of strings or compiled regular expressions, optional
            A list of needed contents to be scraped.
                AutoScraper learns a set of rules to scrape these targets. If specified,
                wanted_dict will be ignored.

        wanted_dict: dict, optional
            A dict of needed contents to be scraped. Keys are aliases and values are list of target texts
                or compiled regular expressions.
                AutoScraper learns a set of rules to scrape these targets and sets its aliases.

        html: str, optional
            An HTML string can also be passed instead of URL.
                You should either pass url or html or both.

        request_args: dict, optional
            A dictionary used to specify a set of additional request parameters used by requests
                module. You can specify proxy URLs, custom headers etc.

        update: bool, optional, defaults to False
            If True, new learned rules will be added to the previous ones.
            If False, all previously learned rules will be removed.

        text_fuzz_ratio: float in range [0, 1], optional, defaults to 1.0
            The fuzziness ratio threshold for matching the wanted contents.

        Returns:
        --------
        List of similar results
        """

        if not wanted_list and not (wanted_dict and any(wanted_dict.values())):
            raise ValueError("No targets were supplied")

        soup = self._get_soup(url=url, html=html, request_args=request_args)

        result_list = []
        
        # Store elements for adaptive saving
        adaptive_elements = []

        if update is False:
            self.stack_list = []
            # Clear adaptive data for this domain if not updating
            if self.adaptive and self._adaptive_storage is not None:
                domain = AdaptiveStorage.extract_domain(url or "")
                self._adaptive_storage.clear_domain(domain)

        if wanted_list:
            wanted_dict = {"": wanted_list}

        wanted_list = []

        for alias, wanted_items in wanted_dict.items():
            wanted_items = [normalize(w) for w in wanted_items]
            wanted_list += wanted_items

            for wanted in wanted_items:
                children = self._get_children(soup, wanted, url, text_fuzz_ratio)

                for child in children:
                    result, stack = self._get_result_for_child(child, soup, url)
                    stack["alias"] = alias
                    result_list += result
                    self.stack_list.append(stack)
                    
                    # Store child element for adaptive saving
                    if self.adaptive:
                        adaptive_elements.append((child, stack))

        result_list = [item.text for item in result_list]
        result_list = unique_hashable(result_list)

        self.stack_list = unique_stack_list(self.stack_list)

        # Build content fingerprints for flexible cross-site extraction
        if result_list:
            if not update:
                self._content_fingerprints = {}
            fp = self._build_content_fingerprint(result_list)
            if fp:
                # Use a deterministic key so repeated builds produce the same key
                fp_key = hashlib.sha256(
                    str(sorted(result_list[:5])).encode()
                ).hexdigest()[:8]
                fp['alias'] = ''  # default alias for wanted_list
                self._content_fingerprints[fp_key] = fp

        # Auto-save adaptive data when adaptive mode is enabled
        if self.adaptive and adaptive_elements:
            self._init_adaptive()
            domain = AdaptiveStorage.extract_domain(url or "")
            
            # Save unique elements (by stack_id)
            # Use stack_id as the storage key to avoid alias collisions
            # (multiple elements can share the same alias)
            saved_ids = set()
            for child, stack in adaptive_elements:
                stack_id = stack.get('stack_id')
                if stack_id and stack_id not in saved_ids:
                    # Use stack_id as identifier to avoid overwriting
                    # when multiple elements share the same alias
                    self._adaptive_storage.save(
                        domain,
                        stack_id,
                        {
                            **extract_element_properties(child, url or ""),
                            'alias': stack.get('alias', ''),
                        }
                    )
                    saved_ids.add(stack_id)
        
        return result_list

    @classmethod
    def _build_stack(cls, child, url):
        content = [(child.name, cls._get_valid_attrs(child))]

        parent = child
        while True:
            grand_parent = parent.findParent()
            if not grand_parent:
                break

            children = grand_parent.findAll(
                parent.name, cls._get_valid_attrs(parent), recursive=False
            )
            for i, c in enumerate(children):
                if c == parent:
                    content.insert(
                        0, (grand_parent.name, cls._get_valid_attrs(grand_parent), i)
                    )
                    break

            if not grand_parent.parent:
                break

            parent = grand_parent

        wanted_attr = getattr(child, "wanted_attr", None)
        is_full_url = getattr(child, "is_full_url", False)
        is_non_rec_text = getattr(child, "is_non_rec_text", False)
        stack = dict(
            content=content,
            wanted_attr=wanted_attr,
            is_full_url=is_full_url,
            is_non_rec_text=is_non_rec_text,
        )
        stack["url"] = url if is_full_url else ""
        stack["hash"] = hashlib.sha256(str(stack).encode("utf-8")).hexdigest()
        stack["stack_id"] = "rule_" + stack["hash"][:8]
        return stack

    def _get_result_for_child(self, child, soup, url):
        stack = self._build_stack(child, url)
        result = self._get_result_with_stack(stack, soup, url, 1.0)
        return result, stack

    @staticmethod
    def _fetch_result_from_child(child, wanted_attr, is_full_url, url, is_non_rec_text):
        if wanted_attr is None:
            if is_non_rec_text:
                return get_non_rec_text(child)
            return child.getText().strip()

        if wanted_attr not in child.attrs:
            return None

        if is_full_url:
            return urljoin(url, child.attrs[wanted_attr])

        return child.attrs[wanted_attr]

    @staticmethod
    def _get_fuzzy_attrs(attrs, attr_fuzz_ratio):
        attrs = dict(attrs)
        for key, val in attrs.items():
            if isinstance(val, str) and val:
                val = FuzzyText(val, attr_fuzz_ratio)
            elif isinstance(val, (list, tuple)):
                val = [FuzzyText(x, attr_fuzz_ratio) if x else x for x in val]
            attrs[key] = val
        return attrs

    def _get_result_with_stack(self, stack, soup, url, attr_fuzz_ratio, **kwargs):
        parents = [soup]
        stack_content = stack["content"]
        contain_sibling_leaves = kwargs.get("contain_sibling_leaves", False)
        for index, item in enumerate(stack_content):
            children = []
            if item[0] == "[document]":
                continue
            for parent in parents:

                attrs = item[1]
                if attr_fuzz_ratio < 1.0:
                    attrs = self._get_fuzzy_attrs(attrs, attr_fuzz_ratio)

                found = parent.findAll(item[0], attrs, recursive=False)
                if not found:
                    continue

                if not contain_sibling_leaves and index == len(stack_content) - 1:
                    idx = min(len(found) - 1, stack_content[index - 1][2])
                    found = [found[idx]]

                children += found

            parents = children

        wanted_attr = stack["wanted_attr"]
        is_full_url = stack["is_full_url"]
        is_non_rec_text = stack.get("is_non_rec_text", False)
        result = [
            ResultItem(
                self._fetch_result_from_child(
                    i, wanted_attr, is_full_url, url, is_non_rec_text
                ),
                getattr(i, "child_index", 0),
                i  # Store the element for container detection
            )
            for i in parents
        ]
        if not kwargs.get("keep_blank", False):
            result = [x for x in result if x.text]
        return result

    def _get_result_with_stack_index_based(
        self, stack, soup, url, attr_fuzz_ratio, **kwargs
    ):
        p = soup.findChildren(recursive=False)[0]
        stack_content = stack["content"]
        for index, item in enumerate(stack_content[:-1]):
            if item[0] == "[document]":
                continue
            content = stack_content[index + 1]
            attrs = content[1]
            if attr_fuzz_ratio < 1.0:
                attrs = self._get_fuzzy_attrs(attrs, attr_fuzz_ratio)
            p = p.findAll(content[0], attrs, recursive=False)
            if not p:
                return []
            idx = min(len(p) - 1, item[2])
            p = p[idx]

        result = [
            ResultItem(
                self._fetch_result_from_child(
                    p,
                    stack["wanted_attr"],
                    stack["is_full_url"],
                    url,
                    stack["is_non_rec_text"],
                ),
                getattr(p, "child_index", 0),
            )
        ]
        if not kwargs.get("keep_blank", False):
            result = [x for x in result if x.text]
        return result

    def _get_result_by_func(
        self,
        func,
        url,
        html,
        soup,
        request_args,
        grouped,
        group_by_alias,
        unique,
        attr_fuzz_ratio,
        **kwargs
    ):
        if not soup:
            soup = self._get_soup(url=url, html=html, request_args=request_args)

        keep_order = kwargs.get("keep_order", False)

        if group_by_alias or (keep_order and not grouped):
            for index, child in enumerate(soup.findChildren()):
                setattr(child, "child_index", index)

        result_list = []
        grouped_result = defaultdict(list)
        for stack in self.stack_list:
            if not url:
                url = stack.get("url", "")

            result = func(stack, soup, url, attr_fuzz_ratio, **kwargs)

            if not grouped and not group_by_alias:
                result_list += result
                continue

            group_id = stack.get("alias", "") if group_by_alias else stack["stack_id"]
            grouped_result[group_id] += result

        return self._clean_result(
            result_list, grouped_result, grouped, group_by_alias, unique, keep_order
        )

    @staticmethod
    def _clean_result(
        result_list, grouped_result, grouped, grouped_by_alias, unique, keep_order
    ):
        if not grouped and not grouped_by_alias:
            if unique is None:
                unique = True
            if keep_order:
                result_list = sorted(result_list, key=lambda x: x.index)
            result = [x.text for x in result_list]
            if unique:
                result = unique_hashable(result)
            return result

        for k, val in grouped_result.items():
            if grouped_by_alias:
                val = sorted(val, key=lambda x: x.index)
            val = [x.text for x in val]
            if unique:
                val = unique_hashable(val)
            grouped_result[k] = val

        return dict(grouped_result)

    def get_result_similar(
        self,
        url=None,
        html=None,
        soup=None,
        request_args=None,
        grouped=False,
        group_by_alias=False,
        unique=None,
        attr_fuzz_ratio=1.0,
        keep_blank=False,
        keep_order=False,
        contain_sibling_leaves=False,
    ):
        """
        Gets similar results based on the previously learned rules.

        Parameters:
        ----------
        url: str, optional
            URL of the target web page. You should either pass url or html or both.

        html: str, optional
            An HTML string can also be passed instead of URL.
                You should either pass url or html or both.

        request_args: dict, optional
            A dictionary used to specify a set of additional request parameters used by requests
                module. You can specify proxy URLs, custom headers etc.

        grouped: bool, optional, defaults to False
            If set to True, the result will be a dictionary with the rule_ids as keys
                and a list of scraped data per rule as values.

        group_by_alias: bool, optional, defaults to False
            If set to True, the result will be a dictionary with the rule alias as keys
                and a list of scraped data per alias as values.

        unique: bool, optional, defaults to True for non grouped results and
                False for grouped results.
            If set to True, will remove duplicates from returned result list.

        attr_fuzz_ratio: float in range [0, 1], optional, defaults to 1.0
            The fuzziness ratio threshold for matching html tag attributes.

        keep_blank: bool, optional, defaults to False
            If set to True, missing values will be returned as empty strings.

        keep_order: bool, optional, defaults to False
            If set to True, the results will be ordered as they are present on the web page.

        contain_sibling_leaves: bool, optional, defaults to False
            If set to True, the results will also contain the sibling leaves of the wanted elements.

        Returns:
        --------
        List of similar results scraped from the web page.
        Dictionary if grouped=True or group_by_alias=True.
        """

        func = self._get_result_with_stack
        result = self._get_result_by_func(
            func,
            url,
            html,
            soup,
            request_args,
            grouped,
            group_by_alias,
            unique,
            attr_fuzz_ratio,
            keep_blank=keep_blank,
            keep_order=keep_order,
            contain_sibling_leaves=contain_sibling_leaves,
        )
        
        # If adaptive mode is enabled and no results found, try adaptive matching
        if self.adaptive and not result:
            result = self.get_result_adaptive(
                url=url,
                html=html,
                request_args=request_args,
                grouped=grouped,
                group_by_alias=group_by_alias,
            )
        
        return result

    def get_result_exact(
        self,
        url=None,
        html=None,
        soup=None,
        request_args=None,
        grouped=False,
        group_by_alias=False,
        unique=None,
        attr_fuzz_ratio=1.0,
        keep_blank=False,
    ):
        """
        Gets exact results based on the previously learned rules.

        Parameters:
        ----------
        url: str, optional
            URL of the target web page. You should either pass url or html or both.

        html: str, optional
            An HTML string can also be passed instead of URL.
                You should either pass url or html or both.

        request_args: dict, optional
            A dictionary used to specify a set of additional request parameters used by requests
                module. You can specify proxy URLs, custom headers etc.

        grouped: bool, optional, defaults to False
            If set to True, the result will be a dictionary with the rule_ids as keys
                and a list of scraped data per rule as values.

        group_by_alias: bool, optional, defaults to False
            If set to True, the result will be a dictionary with the rule alias as keys
                and a list of scraped data per alias as values.

        unique: bool, optional, defaults to True for non grouped results and
                False for grouped results.
            If set to True, will remove duplicates from returned result list.

        attr_fuzz_ratio: float in range [0, 1], optional, defaults to 1.0
            The fuzziness ratio threshold for matching html tag attributes.

        keep_blank: bool, optional, defaults to False
            If set to True, missing values will be returned as empty strings.

        Returns:
        --------
        List of exact results scraped from the web page.
        Dictionary if grouped=True or group_by_alias=True.
        """

        func = self._get_result_with_stack_index_based
        result = self._get_result_by_func(
            func,
            url,
            html,
            soup,
            request_args,
            grouped,
            group_by_alias,
            unique,
            attr_fuzz_ratio,
            keep_blank=keep_blank,
        )
        
        # If adaptive mode is enabled and no results found, try adaptive matching
        if self.adaptive and not result:
            result = self.get_result_adaptive(
                url=url,
                html=html,
                request_args=request_args,
                grouped=grouped,
                group_by_alias=group_by_alias,
            )
        
        return result

    def get_result(
        self,
        url=None,
        html=None,
        request_args=None,
        grouped=False,
        group_by_alias=False,
        unique=None,
        attr_fuzz_ratio=1.0,
    ):
        """
        Gets similar and exact results based on the previously learned rules.

        Parameters:
        ----------
        url: str, optional
            URL of the target web page. You should either pass url or html or both.

        html: str, optional
            An HTML string can also be passed instead of URL.
                You should either pass url or html or both.

        request_args: dict, optional
            A dictionary used to specify a set of additional request parameters used by requests
                module. You can specify proxy URLs, custom headers etc.

        grouped: bool, optional, defaults to False
            If set to True, the result will be dictionaries with the rule_ids as keys
                and a list of scraped data per rule as values.

        group_by_alias: bool, optional, defaults to False
            If set to True, the result will be a dictionary with the rule alias as keys
                and a list of scraped data per alias as values.

        unique: bool, optional, defaults to True for non grouped results and
                False for grouped results.
            If set to True, will remove duplicates from returned result list.

        attr_fuzz_ratio: float in range [0, 1], optional, defaults to 1.0
            The fuzziness ratio threshold for matching html tag attributes.

        Returns:
        --------
        Pair of (similar, exact) results.
        See get_result_similar and get_result_exact methods.
        """

        soup = self._get_soup(url=url, html=html, request_args=request_args)
        args = dict(
            url=url,
            soup=soup,
            grouped=grouped,
            group_by_alias=group_by_alias,
            unique=unique,
            attr_fuzz_ratio=attr_fuzz_ratio,
        )
        similar = self.get_result_similar(**args)
        exact = self.get_result_exact(**args)
        return similar, exact

    def remove_rules(self, rules):
        """
        Removes a list of learned rules from stack_list.

        Parameters:
        ----------
        rules : list
            A list of rules to be removed

        Returns:
        --------
        None
        """

        self.stack_list = [x for x in self.stack_list if x["stack_id"] not in rules]

    def keep_rules(self, rules):
        """
        Removes all other rules except the specified ones.

        Parameters:
        ----------
        rules : list
            A list of rules to keep in stack_list and removing the rest.

        Returns:
        --------
        None
        """

        self.stack_list = [x for x in self.stack_list if x["stack_id"] in rules]

    def set_rule_aliases(self, rule_aliases):
        """
        Sets the specified alias for each rule

        Parameters:
        ----------
        rule_aliases : dict
            A dictionary with keys of rule_id and values of alias

        Returns:
        --------
        None
        """

        id_to_stack = {stack["stack_id"]: stack for stack in self.stack_list}
        for rule_id, alias in rule_aliases.items():
            if rule_id not in id_to_stack:
                raise KeyError(
                    f"Rule '{rule_id}' not found in stack_list. "
                    f"Available rules: {list(id_to_stack.keys())}"
                )
            id_to_stack[rule_id]["alias"] = alias

    def generate_python_code(self):
        """Deprecated: Use save() and load() instead."""
        warnings.warn(
            "generate_python_code() is deprecated. Use save() and load() instead.",
            DeprecationWarning,
            stacklevel=2
        )
    # =========================================================================
    # ADVANCED EXTRACTION METHODS
    # =========================================================================
    
    def extract_data_types(self, url=None, html=None, data_types=None):
        """
        Extract specific data types (emails, phones, prices, etc.) from HTML.
        
        Parameters
        ----------
        url : str, optional
            URL to fetch HTML from.
        html : str, optional
            HTML content to parse.
        data_types : list, optional
            List of data types to extract. Options: 'email', 'phone', 'price',
            'url', 'date', 'time', 'percentage', 'number', 'rating'.
            If None, extracts all types.
            
        Returns
        -------
        dict
            Dictionary with data types as keys and lists of matches as values.
            
        Examples
        --------
        >>> scraper = DejavuScraper()
        >>> result = scraper.extract_data_types(html=html, data_types=['email', 'phone'])
        >>> print(result['email'])  # ['contact@example.com']
        >>> print(result['phone'])  # ['+1-555-123-4567']
        """
        soup = self._get_soup(url=url, html=html)
        text = soup.get_text()
        
        if data_types is None:
            return SmartExtractor.extract_all(text)
        
        results = {}
        for dtype in data_types:
            matches = SmartExtractor.extract_type(text, dtype)
            if matches:
                results[dtype] = matches
        return results
    
    def extract_emails(self, url=None, html=None):
        """Extract all email addresses from HTML."""
        soup = self._get_soup(url=url, html=html)
        return SmartExtractor.extract_emails(soup.get_text())
    
    def extract_phones(self, url=None, html=None):
        """Extract all phone numbers from HTML."""
        soup = self._get_soup(url=url, html=html)
        return SmartExtractor.extract_phones(soup.get_text())
    
    def extract_prices(self, url=None, html=None, parse=False):
        """
        Extract all prices from HTML.
        
        Parameters
        ----------
        url : str, optional
            URL to fetch.
        html : str, optional
            HTML content.
        parse : bool
            If True, return parsed float values instead of strings.
            
        Returns
        -------
        list
            List of prices (strings or floats).
        """
        soup = self._get_soup(url=url, html=html)
        prices = SmartExtractor.extract_prices(soup.get_text())
        if parse:
            return [SmartExtractor.parse_price(p) for p in prices if SmartExtractor.parse_price(p) is not None]
        return prices
    
    def auto_detect_patterns(self, url=None, html=None, min_occurrences=3):
        """
        Automatically detect repeating patterns without training.
        
        Finds lists, cards, tables, and other repeated structures.
        
        Parameters
        ----------
        url : str, optional
            URL to fetch.
        html : str, optional
            HTML content.
        min_occurrences : int
            Minimum times a pattern must appear.
            
        Returns
        -------
        dict
            Dictionary containing:
            - 'lists': Detected list structures
            - 'tables': Parsed tables
            - 'cards': Detected card/product patterns
            
        Examples
        --------
        >>> scraper = DejavuScraper()
        >>> patterns = scraper.auto_detect_patterns(html=html)
        >>> for card in patterns['cards']:
        ...     print(f"Found {card['count']} items")
        """
        soup = self._get_soup(url=url, html=html)
        detector = PatternDetector(soup, min_occurrences)
        return detector.auto_extract()
    
    def extract_tables(self, url=None, html=None, as_dicts=True):
        """
        Extract all tables from HTML.
        
        Parameters
        ----------
        url : str, optional
            URL to fetch.
        html : str, optional
            HTML content.
        as_dicts : bool
            If True, return rows as list of dicts. If False, return raw rows.
            
        Returns
        -------
        list
            List of parsed tables.
            
        Examples
        --------
        >>> tables = scraper.extract_tables(html=html)
        >>> for row in tables[0]['as_dicts']:
        ...     print(row['Name'], row['Price'])
        """
        soup = self._get_soup(url=url, html=html)
        parser = TableParser(soup)
        tables = parser.parse_all()
        
        if not as_dicts:
            for table in tables:
                del table['as_dicts']
        
        return tables
    
    def extract_table_to_csv(self, url=None, html=None, table_index=0):
        """
        Extract a table and return as CSV string.
        
        Parameters
        ----------
        url : str, optional
            URL to fetch.
        html : str, optional
            HTML content.
        table_index : int
            Index of the table to convert.
            
        Returns
        -------
        str
            CSV formatted string.
        """
        soup = self._get_soup(url=url, html=html)
        parser = TableParser(soup)
        return parser.to_csv_string(table_index)
    
    def extract_structured_data(self, url=None, html=None):
        """
        Extract structured data (JSON-LD, meta tags, microdata).
        
        Parameters
        ----------
        url : str, optional
            URL to fetch.
        html : str, optional
            HTML content.
            
        Returns
        -------
        dict
            Dictionary containing:
            - 'json_ld': JSON-LD structured data
            - 'meta_tags': Meta tag information
            - 'microdata': Microdata items
            
        Examples
        --------
        >>> data = scraper.extract_structured_data(url='https://example.com')
        >>> print(data['meta_tags']['og']['title'])  # Open Graph title
        >>> print(data['json_ld'])  # JSON-LD schema data
        """
        soup = self._get_soup(url=url, html=html)
        extractor = StructuredDataExtractor(soup)
        return extractor.extract_all()
    
    def extract_json_ld(self, url=None, html=None):
        """Extract JSON-LD structured data."""
        soup = self._get_soup(url=url, html=html)
        return StructuredDataExtractor(soup).extract_json_ld()
    
    def extract_meta_tags(self, url=None, html=None):
        """Extract all meta tags."""
        soup = self._get_soup(url=url, html=html)
        return StructuredDataExtractor(soup).extract_meta_tags()
    
    def detect_pagination(self, url=None, html=None):
        """
        Detect pagination links.
        
        Parameters
        ----------
        url : str, optional
            URL to fetch (also used as base URL for relative links).
        html : str, optional
            HTML content.
            
        Returns
        -------
        dict
            Dictionary containing:
            - 'next': URL of next page
            - 'prev': URL of previous page
            - 'pages': List of numbered page links
            - 'current': Current page number
            - 'total_pages': Estimated total pages
            
        Examples
        --------
        >>> pagination = scraper.detect_pagination(url='https://example.com/page/1')
        >>> print(pagination['next'])  # 'https://example.com/page/2'
        """
        soup = self._get_soup(url=url, html=html)
        detector = PaginationDetector(soup, base_url=url)
        return detector.detect()
    
    def extract_with_regex(self, pattern, url=None, html=None, flags=0):
        """
        Extract content using a regex pattern.
        
        Parameters
        ----------
        pattern : str
            Regex pattern to match.
        url : str, optional
            URL to fetch.
        html : str, optional
            HTML content.
        flags : int
            Regex flags (e.g., re.IGNORECASE).
            
        Returns
        -------
        list
            List of matches.
            
        Examples
        --------
        >>> import re
        >>> prices = scraper.extract_with_regex(r'\$[\d,]+\.?\d*', html=html)
        >>> skus = scraper.extract_with_regex(r'SKU-\d{6}', html=html, flags=re.IGNORECASE)
        """
        soup = self._get_soup(url=url, html=html)
        extractor = RegexExtractor(soup)
        return extractor.extract(pattern, flags)
    
    def extract_with_named_groups(self, pattern, url=None, html=None, flags=0):
        """
        Extract content using regex with named groups.
        
        Parameters
        ----------
        pattern : str
            Regex pattern with named groups (?P<name>...).
        url : str, optional
            URL to fetch.
        html : str, optional
            HTML content.
        flags : int
            Regex flags.
            
        Returns
        -------
        list
            List of dicts with group names as keys.
            
        Examples
        --------
        >>> pattern = r'(?P<product>\w+)\s*:\s*\$(?P<price>[\d.]+)'
        >>> items = scraper.extract_with_named_groups(pattern, html=html)
        >>> print(items)  # [{'product': 'Widget', 'price': '29.99'}]
        """
        soup = self._get_soup(url=url, html=html)
        extractor = RegexExtractor(soup)
        return extractor.extract_named_groups(pattern, flags)
    
    def clean_text(self, text, **options):
        """
        Clean and normalize text.
        
        Parameters
        ----------
        text : str
            Text to clean.
        **options : dict
            Cleaning options:
            - normalize_whitespace: bool (default True)
            - remove_extra_newlines: bool (default True)
            - decode_html_entities: bool (default True)
            - lowercase: bool (default False)
            - remove_punctuation: bool (default False)
            
        Returns
        -------
        str
            Cleaned text.
        """
        return TextCleaner.clean(text, options)
    
    def extract_clean_text(self, url=None, html=None, **options):
        """
        Extract and clean all text from HTML.
        
        Parameters
        ----------
        url : str, optional
            URL to fetch.
        html : str, optional
            HTML content.
        **options : dict
            Cleaning options (see clean_text).
            
        Returns
        -------
        str
            Cleaned text content.
        """
        soup = self._get_soup(url=url, html=html)
        raw_text = soup.get_text()
        return TextCleaner.clean(raw_text, options)
    
    def detect_lists(self, url=None, html=None, min_items=3):
        """
        Detect list-like structures in HTML.
        
        Parameters
        ----------
        url : str, optional
            URL to fetch.
        html : str, optional
            HTML content.
        min_items : int
            Minimum items for a list to be detected.
            
        Returns
        -------
        list
            List of detected list structures with their items.
        """
        soup = self._get_soup(url=url, html=html)
        detector = PatternDetector(soup, min_items)
        return detector.detect_lists()
    
    def detect_cards(self, url=None, html=None, min_items=3):
        """
        Detect card-like structures (products, articles, etc.).
        
        Parameters
        ----------
        url : str, optional
            URL to fetch.
        html : str, optional
            HTML content.
        min_items : int
            Minimum items for cards to be detected.
            
        Returns
        -------
        list
            List of detected card patterns with sample fields.
        """
        soup = self._get_soup(url=url, html=html)
        detector = PatternDetector(soup, min_items)
        return detector.detect_cards()
    
    def smart_extract(self, url=None, html=None):
        """
        Perform comprehensive smart extraction.
        
        Combines multiple extraction methods to gather all available data.
        
        Parameters
        ----------
        url : str, optional
            URL to fetch.
        html : str, optional
            HTML content.
            
        Returns
        -------
        dict
            Dictionary containing:
            - 'data_types': Extracted emails, phones, prices, etc.
            - 'patterns': Auto-detected repeating patterns
            - 'structured_data': JSON-LD, meta tags, microdata
            - 'pagination': Pagination information
            
        Examples
        --------
        >>> result = scraper.smart_extract(url='https://example.com/products')
        >>> print(result['data_types']['price'])  # All prices found
        >>> print(result['patterns']['cards'])    # Product cards detected
        >>> print(result['pagination']['next'])   # Next page URL
        """
        soup = self._get_soup(url=url, html=html)
        text = soup.get_text()
        
        return {
            'data_types': SmartExtractor.extract_all(text),
            'patterns': PatternDetector(soup).auto_extract(),
            'structured_data': StructuredDataExtractor(soup).extract_all(),
            'pagination': PaginationDetector(soup, base_url=url).detect()
        }