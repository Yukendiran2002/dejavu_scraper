"""
Advanced Extractors for DejavuScraper
=====================================

This module provides specialized extraction capabilities:
- Auto Pattern Detection (find repeating elements automatically)
- Smart Data Type Extraction (prices, dates, emails, phones, URLs)
- Table Parser (extract tables as structured data)
- Regex Extraction (apply regex patterns)
- Structured Data Extraction (JSON-LD, microdata)
- Pagination Detection (find next/prev page links)
- Clean Text Extraction (better text normalization)
"""

import re
import io
import csv
import json
from datetime import datetime
from collections import Counter, defaultdict
from urllib.parse import urljoin, urlparse


class SmartExtractor:
    """
    Smart extraction utilities for common data types.
    Automatically detects and extracts prices, dates, emails, phones, URLs.
    """
    
    # Regex patterns for common data types
    PATTERNS = {
        'email': re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        ),
        'phone': re.compile(
            r'(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+?\d{1,4}[-.\s]?\d{2,4}[-.\s]?\d{2,4}[-.\s]?\d{2,4}'
        ),
        'price': re.compile(
            r'[\$£€¥₹]\s*[\d,]+(?:\.\d{2})?|\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|EUR|GBP|INR|JPY|dollars?|euros?|pounds?)'
        ),
        'url': re.compile(
            r'https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+[/\w\-.~:/?#\[\]@!$&\'()*+,;=%]*'
        ),
        'date': re.compile(
            r'\b(?:\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|'
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{2,4}|'
            r'\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?,?\s*\d{2,4})\b',
            re.IGNORECASE
        ),
        'time': re.compile(
            r'\b(?:1[0-2]|0?[1-9]):[0-5][0-9]\s*(?:AM|PM|am|pm)|(?:2[0-3]|[01]?[0-9]):[0-5][0-9](?::[0-5][0-9])?\b'
        ),
        'percentage': re.compile(
            r'\b\d+(?:\.\d+)?%'
        ),
        'number': re.compile(
            r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b'
        ),
        'rating': re.compile(
            r'\b\d(?:\.\d)?\s*(?:/\s*5|stars?|⭐|★)|(?:★|⭐){1,5}'
        ),
        'hashtag': re.compile(
            r'#[A-Za-z_]\w*'
        ),
        'mention': re.compile(
            r'@[A-Za-z_]\w*'
        ),
        'ip_address': re.compile(
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        ),
        'zip_code': re.compile(
            r'\b\d{5}(?:-\d{4})?\b'
        ),
    }
    
    @classmethod
    def extract_all(cls, text):
        """
        Extract all detectable data types from text.
        
        Parameters
        ----------
        text : str
            The text to extract from.
            
        Returns
        -------
        dict
            Dictionary with data type as key and list of matches as value.
        """
        results = {}
        for dtype, pattern in cls.PATTERNS.items():
            matches = pattern.findall(text)
            if matches:
                results[dtype] = matches
        return results
    
    @classmethod
    def extract_type(cls, text, data_type):
        """
        Extract specific data type from text.
        
        Parameters
        ----------
        text : str
            The text to extract from.
        data_type : str
            Type to extract: 'email', 'phone', 'price', 'url', 'date', etc.
            
        Returns
        -------
        list
            List of matches.
        """
        if data_type not in cls.PATTERNS:
            raise ValueError(f"Unknown data type: {data_type}. Available: {list(cls.PATTERNS.keys())}")
        return cls.PATTERNS[data_type].findall(text)
    
    @classmethod
    def extract_emails(cls, text):
        """Extract all email addresses."""
        return cls.PATTERNS['email'].findall(text)
    
    @classmethod
    def extract_phones(cls, text):
        """Extract all phone numbers."""
        return cls.PATTERNS['phone'].findall(text)
    
    @classmethod
    def extract_prices(cls, text):
        """Extract all prices with currency."""
        return cls.PATTERNS['price'].findall(text)
    
    @classmethod
    def extract_urls(cls, text):
        """Extract all URLs."""
        return cls.PATTERNS['url'].findall(text)
    
    @classmethod
    def extract_dates(cls, text):
        """Extract all dates."""
        return cls.PATTERNS['date'].findall(text)
    
    @classmethod
    def parse_price(cls, price_str):
        """
        Parse a price string into a float.
        
        Parameters
        ----------
        price_str : str
            Price string like "$1,299.99" or "€99.00"
            
        Returns
        -------
        float
            The numeric price value.
        """
        # Remove currency symbols and whitespace
        cleaned = re.sub(r'[^\d.,]', '', price_str)
        # Handle European format (1.234,56 -> 1234.56)
        if ',' in cleaned and '.' in cleaned:
            if cleaned.rindex(',') > cleaned.rindex('.'):
                cleaned = cleaned.replace('.', '').replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        elif ',' in cleaned:
            # Could be European decimal or thousand separator
            parts = cleaned.split(',')
            if len(parts[-1]) == 2:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
        try:
            return float(cleaned)
        except ValueError:
            return None


class PatternDetector:
    """
    Automatically detect repeating patterns in HTML without training.
    Finds lists, grids, and repeating structures.
    """
    
    def __init__(self, soup, min_occurrences=3):
        """
        Initialize pattern detector.
        
        Parameters
        ----------
        soup : BeautifulSoup
            Parsed HTML.
        min_occurrences : int
            Minimum times a pattern must appear to be detected.
        """
        self.soup = soup
        self.min_occurrences = min_occurrences
    
    def detect_lists(self):
        """
        Detect list-like structures (ul/ol/repeated divs).
        
        Returns
        -------
        list
            List of detected list containers with their items.
        """
        lists = []
        
        # Standard HTML lists
        for ul in self.soup.find_all(['ul', 'ol']):
            items = ul.find_all('li', recursive=False)
            if len(items) >= self.min_occurrences:
                lists.append({
                    'type': 'html_list',
                    'container': ul,
                    'items': items,
                    'count': len(items),
                    'texts': [item.get_text(strip=True) for item in items]
                })
        
        # Detect repeated sibling patterns
        lists.extend(self._detect_repeated_siblings())
        
        return lists
    
    def _detect_repeated_siblings(self):
        """Find repeated sibling elements with similar structure."""
        detected = []
        processed_parents = set()
        
        for element in self.soup.find_all(True):
            parent = element.parent
            if parent is None or id(parent) in processed_parents:
                continue
            
            # Get direct children with same tag
            children = parent.find_all(element.name, recursive=False)
            if len(children) < self.min_occurrences:
                continue
            
            # Check if children have similar structure
            structures = [self._get_structure(child) for child in children]
            structure_counts = Counter(structures)
            most_common = structure_counts.most_common(1)
            
            if most_common and most_common[0][1] >= self.min_occurrences:
                common_structure = most_common[0][0]
                matching_children = [c for c, s in zip(children, structures) if s == common_structure]
                
                if matching_children:
                    detected.append({
                        'type': 'repeated_pattern',
                        'tag': element.name,
                        'container': parent,
                        'items': matching_children,
                        'count': len(matching_children),
                        'structure': common_structure
                    })
                    processed_parents.add(id(parent))
        
        return detected
    
    def _get_structure(self, element):
        """Get a string representation of element structure."""
        if element.name is None:
            return ''
        children_tags = tuple(sorted([c.name for c in element.children if hasattr(c, 'name') and c.name]))
        classes = tuple(sorted(element.get('class', [])))
        return f"{element.name}:{classes}:{children_tags}"
    
    def detect_tables(self):
        """
        Detect and parse HTML tables.
        
        Returns
        -------
        list
            List of parsed tables as list of dicts.
        """
        tables = []
        for table in self.soup.find_all('table'):
            parsed = self._parse_table(table)
            if parsed:
                tables.append(parsed)
        return tables
    
    def _parse_table(self, table):
        """Parse a single table into structured data."""
        rows = table.find_all('tr')
        if not rows:
            return None
        
        # Try to get headers
        headers = []
        header_row = rows[0]
        header_cells = header_row.find_all(['th', 'td'])
        
        if header_row.find('th'):
            headers = [cell.get_text(strip=True) for cell in header_cells]
            data_rows = rows[1:]
        else:
            # No explicit headers, use column indices
            num_cols = len(header_cells)
            headers = [f'col_{i}' for i in range(num_cols)]
            data_rows = rows
        
        # Parse data rows
        data = []
        for row in data_rows:
            cells = row.find_all(['td', 'th'])
            if cells:
                row_data = {}
                for i, cell in enumerate(cells):
                    header = headers[i] if i < len(headers) else f'col_{i}'
                    row_data[header] = cell.get_text(strip=True)
                data.append(row_data)
        
        return {
            'headers': headers,
            'data': data,
            'row_count': len(data)
        }
    
    def detect_cards(self):
        """
        Detect card-like structures (product cards, article previews, etc.).
        
        Returns
        -------
        list
            List of detected card patterns.
        """
        cards = []
        
        # Common card container classes
        card_indicators = ['card', 'item', 'product', 'article', 'post', 'entry', 
                          'listing', 'result', 'tile', 'box', 'block']
        
        for indicator in card_indicators:
            # Find by class
            elements = self.soup.find_all(class_=re.compile(indicator, re.I))
            if len(elements) >= self.min_occurrences:
                # Group by structure
                structures = defaultdict(list)
                for el in elements:
                    struct = self._get_structure(el)
                    structures[struct].append(el)
                
                for struct, items in structures.items():
                    if len(items) >= self.min_occurrences:
                        cards.append({
                            'type': 'card',
                            'indicator': indicator,
                            'items': items,
                            'count': len(items),
                            'sample_fields': self._extract_card_fields(items[0])
                        })
        
        return cards
    
    def _extract_card_fields(self, card):
        """Extract common fields from a card element."""
        fields = {}
        
        # Title (h1-h6 or .title/.name)
        title = card.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        if not title:
            title = card.find(class_=re.compile(r'title|name|heading', re.I))
        if title:
            fields['title'] = title.get_text(strip=True)
        
        # Price
        price = card.find(class_=re.compile(r'price|cost|amount', re.I))
        if price:
            fields['price'] = price.get_text(strip=True)
        
        # Description
        desc = card.find(class_=re.compile(r'desc|summary|excerpt|content', re.I))
        if not desc:
            desc = card.find('p')
        if desc:
            fields['description'] = desc.get_text(strip=True)[:200]
        
        # Image
        img = card.find('img')
        if img:
            fields['image'] = img.get('src') or img.get('data-src')
        
        # Link
        link = card.find('a', href=True)
        if link:
            fields['link'] = link.get('href')
        
        return fields
    
    def auto_extract(self):
        """
        Automatically detect and extract all repeating patterns.
        
        Returns
        -------
        dict
            Dictionary containing all detected patterns.
        """
        return {
            'lists': self.detect_lists(),
            'tables': self.detect_tables(),
            'cards': self.detect_cards()
        }


class TableParser:
    """
    Advanced table parsing with multiple output formats.
    """
    
    def __init__(self, soup):
        """
        Initialize table parser.
        
        Parameters
        ----------
        soup : BeautifulSoup
            Parsed HTML containing tables.
        """
        self.soup = soup
    
    def parse_all(self):
        """
        Parse all tables in the HTML.
        
        Returns
        -------
        list
            List of parsed tables.
        """
        tables = []
        for i, table in enumerate(self.soup.find_all('table')):
            parsed = self.parse_table(table)
            parsed['table_index'] = i
            tables.append(parsed)
        return tables
    
    def parse_table(self, table):
        """
        Parse a single table element.
        
        Parameters
        ----------
        table : Tag
            BeautifulSoup table tag.
            
        Returns
        -------
        dict
            Parsed table data with headers and rows.
        """
        # Handle complex table structures
        thead = table.find('thead')
        tbody = table.find('tbody')
        
        # Get headers
        headers = []
        if thead:
            header_cells = thead.find_all(['th', 'td'])
            headers = [self._clean_cell(cell) for cell in header_cells]
        
        # Get data rows
        if tbody:
            rows = tbody.find_all('tr')
        else:
            rows = table.find_all('tr')
            # First row might be headers
            if not headers and rows:
                first_row = rows[0]
                if first_row.find('th'):
                    headers = [self._clean_cell(cell) for cell in first_row.find_all(['th', 'td'])]
                    rows = rows[1:]
        
        # Parse data
        data = []
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if not cells:
                continue
            
            row_data = [self._clean_cell(cell) for cell in cells]
            data.append(row_data)
        
        # Create default headers if needed
        if not headers and data:
            max_cols = max(len(row) for row in data)
            headers = [f'column_{i+1}' for i in range(max_cols)]
        
        return {
            'headers': headers,
            'rows': data,
            'as_dicts': self._rows_to_dicts(headers, data)
        }
    
    def _clean_cell(self, cell):
        """Clean and normalize cell content."""
        text = cell.get_text(strip=True)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text
    
    def _rows_to_dicts(self, headers, rows):
        """Convert rows to list of dicts."""
        result = []
        for row in rows:
            row_dict = {}
            for i, value in enumerate(row):
                key = headers[i] if i < len(headers) else f'col_{i}'
                row_dict[key] = value
            result.append(row_dict)
        return result
    
    def to_csv_string(self, table_index=0):
        """
        Convert table to CSV string.
        
        Parameters
        ----------
        table_index : int
            Index of the table to convert.
            
        Returns
        -------
        str
            CSV formatted string.
        """
        tables = self.parse_all()
        if table_index >= len(tables):
            return ""
        
        table = tables[table_index]
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        
        # Headers
        writer.writerow(table['headers'])
        
        # Rows
        for row in table['rows']:
            writer.writerow(row)
        
        return output.getvalue()


class StructuredDataExtractor:
    """
    Extract structured data from HTML (JSON-LD, microdata, meta tags).
    """
    
    def __init__(self, soup):
        """
        Initialize structured data extractor.
        
        Parameters
        ----------
        soup : BeautifulSoup
            Parsed HTML.
        """
        self.soup = soup
    
    def extract_json_ld(self):
        """
        Extract JSON-LD structured data.
        
        Returns
        -------
        list
            List of parsed JSON-LD objects.
        """
        json_ld = []
        for script in self.soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)
                json_ld.append(data)
            except (json.JSONDecodeError, TypeError):
                continue
        return json_ld
    
    def extract_meta_tags(self):
        """
        Extract all meta tags.
        
        Returns
        -------
        dict
            Dictionary of meta tag data organized by type.
        """
        meta = {
            'standard': {},
            'og': {},  # Open Graph
            'twitter': {},
            'other': {}
        }
        
        for tag in self.soup.find_all('meta'):
            name = tag.get('name', '') or tag.get('property', '')
            content = tag.get('content', '')
            
            if not name or not content:
                continue
            
            if name.startswith('og:'):
                meta['og'][name[3:]] = content
            elif name.startswith('twitter:'):
                meta['twitter'][name[8:]] = content
            elif name in ['description', 'keywords', 'author', 'viewport', 'robots']:
                meta['standard'][name] = content
            else:
                meta['other'][name] = content
        
        # Also get title
        title = self.soup.find('title')
        if title:
            meta['standard']['title'] = title.get_text(strip=True)
        
        return meta
    
    def extract_microdata(self):
        """
        Extract microdata (itemscope/itemprop).
        
        Returns
        -------
        list
            List of microdata items.
        """
        items = []
        for element in self.soup.find_all(itemscope=True):
            item = self._parse_microdata_item(element)
            items.append(item)
        return items
    
    def _parse_microdata_item(self, element):
        """Parse a single microdata item."""
        item = {
            'type': element.get('itemtype'),
            'properties': {}
        }
        
        for prop in element.find_all(itemprop=True):
            prop_name = prop.get('itemprop')
            
            # Get value based on element type
            if prop.name == 'meta':
                value = prop.get('content')
            elif prop.name in ['img', 'audio', 'video', 'source']:
                value = prop.get('src')
            elif prop.name == 'a':
                value = prop.get('href')
            elif prop.name == 'time':
                value = prop.get('datetime') or prop.get_text(strip=True)
            else:
                value = prop.get_text(strip=True)
            
            if prop_name in item['properties']:
                if isinstance(item['properties'][prop_name], list):
                    item['properties'][prop_name].append(value)
                else:
                    item['properties'][prop_name] = [item['properties'][prop_name], value]
            else:
                item['properties'][prop_name] = value
        
        return item
    
    def extract_all(self):
        """
        Extract all structured data.
        
        Returns
        -------
        dict
            All structured data found in the page.
        """
        return {
            'json_ld': self.extract_json_ld(),
            'meta_tags': self.extract_meta_tags(),
            'microdata': self.extract_microdata()
        }


class PaginationDetector:
    """
    Detect pagination links and patterns.
    """
    
    def __init__(self, soup, base_url=None):
        """
        Initialize pagination detector.
        
        Parameters
        ----------
        soup : BeautifulSoup
            Parsed HTML.
        base_url : str, optional
            Base URL for resolving relative links.
        """
        self.soup = soup
        self.base_url = base_url
    
    def detect(self):
        """
        Detect pagination pattern.
        
        Returns
        -------
        dict
            Pagination information including next/prev links and page numbers.
        """
        result = {
            'next': None,
            'prev': None,
            'pages': [],
            'current': None,
            'total_pages': None
        }
        
        # Find pagination container
        pagination = self._find_pagination_container()
        
        if pagination:
            # Find next/prev links
            result['next'] = self._find_next_link(pagination)
            result['prev'] = self._find_prev_link(pagination)
            result['pages'] = self._find_page_links(pagination)
            result['current'] = self._find_current_page(pagination)
        else:
            # Try to find standalone next/prev
            result['next'] = self._find_next_link(self.soup)
            result['prev'] = self._find_prev_link(self.soup)
        
        # Estimate total pages
        if result['pages']:
            page_nums = [p['number'] for p in result['pages'] if p.get('number')]
            if page_nums:
                result['total_pages'] = max(page_nums)
        
        return result
    
    def _find_pagination_container(self):
        """Find the pagination container element."""
        # Common pagination indicators
        indicators = ['pagination', 'pager', 'paginator', 'page-numbers', 'pages']
        
        for indicator in indicators:
            # By class
            container = self.soup.find(class_=re.compile(indicator, re.I))
            if container:
                return container
            
            # By role
            container = self.soup.find(attrs={'role': 'navigation', 'aria-label': re.compile(indicator, re.I)})
            if container:
                return container
        
        # By nav with pagination links
        for nav in self.soup.find_all('nav'):
            if nav.find('a', href=re.compile(r'page[=/-]?\d+')):
                return nav
        
        return None
    
    def _find_next_link(self, container):
        """Find the 'next' page link."""
        # By rel attribute
        link = container.find('a', rel='next')
        if link:
            return self._resolve_url(link.get('href'))
        
        # By text content
        next_patterns = ['next', 'следующая', '次', '下一页', '›', '»', '→', 'more']
        for pattern in next_patterns:
            link = container.find('a', string=re.compile(f'^{re.escape(pattern)}$', re.I))
            if link and link.get('href'):
                return self._resolve_url(link.get('href'))
        
        # By class/title
        link = container.find('a', class_=re.compile(r'next', re.I))
        if link and link.get('href'):
            return self._resolve_url(link.get('href'))
        
        return None
    
    def _find_prev_link(self, container):
        """Find the 'previous' page link."""
        # By rel attribute
        link = container.find('a', rel='prev')
        if link:
            return self._resolve_url(link.get('href'))
        
        # By text content
        prev_patterns = ['prev', 'previous', 'предыдущая', '前', '上一页', '‹', '«', '←', 'back']
        for pattern in prev_patterns:
            link = container.find('a', string=re.compile(f'^{re.escape(pattern)}$', re.I))
            if link and link.get('href'):
                return self._resolve_url(link.get('href'))
        
        # By class
        link = container.find('a', class_=re.compile(r'prev', re.I))
        if link and link.get('href'):
            return self._resolve_url(link.get('href'))
        
        return None
    
    def _find_page_links(self, container):
        """Find all numbered page links."""
        pages = []
        seen_urls = set()
        
        for link in container.find_all('a', href=True):
            text = link.get_text(strip=True)
            href = link.get('href')
            
            # Check if it's a page number
            if text.isdigit():
                url = self._resolve_url(href)
                if url and url not in seen_urls:
                    pages.append({
                        'number': int(text),
                        'url': url
                    })
                    seen_urls.add(url)
        
        return sorted(pages, key=lambda x: x['number'])
    
    def _find_current_page(self, container):
        """Find the current page number."""
        # By active/current class
        current = container.find(class_=re.compile(r'active|current|selected', re.I))
        if current:
            text = current.get_text(strip=True)
            if text.isdigit():
                return int(text)
        
        # By aria-current
        current = container.find(attrs={'aria-current': True})
        if current:
            text = current.get_text(strip=True)
            if text.isdigit():
                return int(text)
        
        return None
    
    def _resolve_url(self, url):
        """Resolve relative URL to absolute."""
        if not url or url == '#':
            return None
        if self.base_url:
            return urljoin(self.base_url, url)
        return url
    
    def get_all_page_urls(self, max_pages=100):
        """
        Generate URLs for all pages based on detected pattern.
        
        Parameters
        ----------
        max_pages : int
            Maximum number of page URLs to generate.
            
        Returns
        -------
        list
            List of page URLs.
        """
        pagination = self.detect()
        urls = []
        
        # If we have numbered page links, use those
        if pagination['pages']:
            for page in pagination['pages'][:max_pages]:
                urls.append(page['url'])
        
        return urls


class RegexExtractor:
    """
    Apply regex patterns to extract specific content.
    """
    
    def __init__(self, soup_or_text):
        """
        Initialize regex extractor.
        
        Parameters
        ----------
        soup_or_text : BeautifulSoup or str
            Parsed HTML or text string.
        """
        if hasattr(soup_or_text, 'get_text'):
            self.text = soup_or_text.get_text()
        else:
            self.text = str(soup_or_text)
    
    def extract(self, pattern, flags=0):
        """
        Extract all matches for a regex pattern.
        
        Parameters
        ----------
        pattern : str
            Regex pattern.
        flags : int
            Regex flags (e.g., re.IGNORECASE).
            
        Returns
        -------
        list
            List of matches.
        """
        return re.findall(pattern, self.text, flags)
    
    def extract_groups(self, pattern, flags=0):
        """
        Extract matches with groups.
        
        Parameters
        ----------
        pattern : str
            Regex pattern with groups.
        flags : int
            Regex flags.
            
        Returns
        -------
        list
            List of group tuples.
        """
        return re.findall(pattern, self.text, flags)
    
    def extract_named_groups(self, pattern, flags=0):
        """
        Extract matches with named groups as dicts.
        
        Parameters
        ----------
        pattern : str
            Regex pattern with named groups.
        flags : int
            Regex flags.
            
        Returns
        -------
        list
            List of dicts with group names as keys.
        """
        matches = []
        for match in re.finditer(pattern, self.text, flags):
            matches.append(match.groupdict())
        return matches
    
    def replace(self, pattern, replacement, flags=0):
        """
        Replace matches with a string.
        
        Parameters
        ----------
        pattern : str
            Regex pattern.
        replacement : str
            Replacement string.
        flags : int
            Regex flags.
            
        Returns
        -------
        str
            Modified text.
        """
        return re.sub(pattern, replacement, self.text, flags=flags)


class TextCleaner:
    """
    Clean and normalize extracted text.
    """
    
    @staticmethod
    def clean(text, options=None):
        """
        Clean text with various options.
        
        Parameters
        ----------
        text : str
            Text to clean.
        options : dict, optional
            Cleaning options:
            - normalize_whitespace: bool (default True)
            - remove_extra_newlines: bool (default True)
            - strip_html_tags: bool (default False)
            - decode_html_entities: bool (default True)
            - lowercase: bool (default False)
            - remove_punctuation: bool (default False)
            
        Returns
        -------
        str
            Cleaned text.
        """
        if options is None:
            options = {}
        
        # Defaults
        normalize_whitespace = options.get('normalize_whitespace', True)
        remove_extra_newlines = options.get('remove_extra_newlines', True)
        strip_html_tags = options.get('strip_html_tags', False)
        decode_html_entities = options.get('decode_html_entities', True)
        lowercase = options.get('lowercase', False)
        remove_punctuation = options.get('remove_punctuation', False)
        
        result = text
        
        # Decode HTML entities
        if decode_html_entities:
            from html import unescape
            result = unescape(result)
        
        # Strip HTML tags
        if strip_html_tags:
            result = re.sub(r'<[^>]+>', '', result)
        
        # Normalize whitespace
        if normalize_whitespace:
            result = re.sub(r'[ \t]+', ' ', result)
        
        # Remove extra newlines
        if remove_extra_newlines:
            result = re.sub(r'\n\s*\n+', '\n\n', result)
        
        # Lowercase
        if lowercase:
            result = result.lower()
        
        # Remove punctuation
        if remove_punctuation:
            result = re.sub(r'[^\w\s]', '', result)
        
        return result.strip()
    
    @staticmethod
    def extract_sentences(text):
        """
        Extract sentences from text.
        
        Parameters
        ----------
        text : str
            Input text.
            
        Returns
        -------
        list
            List of sentences.
        """
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    @staticmethod
    def truncate(text, max_length=200, suffix='...'):
        """
        Truncate text to max length at word boundary.
        
        Parameters
        ----------
        text : str
            Input text.
        max_length : int
            Maximum length.
        suffix : str
            Suffix to add if truncated.
            
        Returns
        -------
        str
            Truncated text.
        """
        if len(text) <= max_length:
            return text
        
        # Find last space before max_length
        truncated = text[:max_length - len(suffix)]
        last_space = truncated.rfind(' ')
        
        if last_space > 0:
            truncated = truncated[:last_space]
        
        return truncated + suffix
