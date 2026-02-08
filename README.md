# 🕷️ DejavuScraper

**A Smart, Automatic, Fast and Lightweight Web Scraper for Python**

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-2.0.0-green.svg)]()

DejavuScraper is an intelligent web scraping library that automatically learns scraping rules from examples. Provide a sample of what you want to extract, and it figures out how to get similar data from any page — even pages with completely different HTML structures.

**No LLM needed. No per-page training. Learn once, extract everywhere.**

---

## 📑 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Core API](#-core-api)
  - [build()](#build)
  - [get_result_similar()](#get_result_similar)
  - [get_result_flexible()](#get_result_flexible--cross-site-extraction)
  - [Grouped Extraction](#grouped-extraction)
  - [Adaptive Extraction](#adaptive-extraction)
- [Smart Extractors](#-smart-extractors)
  - [Data Type Extraction](#data-type-extraction)
  - [Table Parsing](#table-parsing)
  - [Pattern Detection](#pattern-detection)
  - [Structured Data](#structured-data-json-ld-meta-tags-microdata)
  - [Pagination Detection](#pagination-detection)
  - [Regex Extraction](#regex-extraction)
  - [Text Cleaning](#text-cleaning)
  - [smart_extract()](#smart_extract--all-in-one)
- [Save & Load](#-save--load)
- [Rule Management](#-rule-management)
- [Production Features](#-production-features)
- [How It Works](#-how-it-works)
- [Testing](#-testing)
- [Project Structure](#-project-structure)
- [License](#-license)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎯 **Smart Learning** | Automatically learns scraping rules from examples |
| 🌐 **Cross-Site Extraction** | `get_result_flexible()` — extract from pages with completely different HTML using content fingerprinting |
| 🔄 **Adaptive Extraction** | Relocates elements even after website structure changes using 8-dimension similarity matching |
| 📦 **Grouped Extraction** | Extract multiple related fields per item (name + price + rating) |
| 🔍 **Smart Extractors** | Built-in extraction for emails, phones, prices, dates, tables, JSON-LD, pagination, and more |
| 💾 **Save/Load Models** | JSON and SQLite with atomic writes — learn once, deploy anywhere |
| 🎭 **Fuzzy Matching** | Approximate text matching with configurable ratio |
| 🔗 **URL Extraction** | Automatically extracts href/src attributes |
| ⚡ **Production Ready** | Rate limiting, retry with backoff, connection pooling, streaming responses, 10MB size limit |
| 🛡️ **Robust** | Context manager support, graceful error handling, SHA256 fingerprints |

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/Yukendiran2002/dejavu_scraper.git
cd dejavu_scraper

# Install dependencies
pip install requests
```

BeautifulSoup4 is bundled — no additional installation needed.

---

## 🚀 Quick Start

### Basic Example

```python
from dejavu_scraper import DejavuScraper

html = """
<div class="products">
  <div class="product"><h2>iPhone 15</h2><span>$999</span></div>
  <div class="product"><h2>Samsung Galaxy</h2><span>$899</span></div>
  <div class="product"><h2>Google Pixel</h2><span>$699</span></div>
</div>
"""

scraper = DejavuScraper()
result = scraper.build(html=html, wanted_list=['iPhone 15'])
print(result)
# ['iPhone 15', 'Samsung Galaxy', 'Google Pixel']
```

### From URL

```python
scraper = DejavuScraper()
result = scraper.build(
    url='https://example.com/products',
    wanted_list=['Product Name Example']
)
```

### Cross-Site Extraction (No LLM Needed)

```python
# Learn product names from Site A
scraper = DejavuScraper()
scraper.build(html=site_a_html, wanted_list=['iPhone 15'])

# Extract from Site B with COMPLETELY different HTML tags
results = scraper.get_result_flexible(html=site_b_html)
# Works! Finds product names even though tags are different
```

---

## 📚 Core API

### Constructor

```python
DejavuScraper(
    stack_list=None,      # Pre-existing rules to use
    adaptive=False,       # Enable adaptive extraction
    min_similarity=0.5,   # Minimum similarity for adaptive matching (0-1)
    rate_limit=0,         # Minimum seconds between requests per domain (0=no limit)
    max_retries=3,        # Retries on transient HTTP errors (5xx, timeouts)
    retry_backoff=1.0     # Backoff factor for retries (seconds)
)
```

---

### `build()`

Learn extraction rules from examples.

```python
scraper.build(
    url=None,              # URL to scrape
    wanted_list=None,      # List of example strings to find
    wanted_dict=None,      # Dict with aliases: {'title': 'iPhone 15'}
    html=None,             # HTML string (alternative to URL)
    request_args=None,     # Additional request parameters
    update=False,          # True = add to existing rules, False = replace
    text_fuzz_ratio=1.0    # Fuzzy matching ratio (0-1, 1=exact)
)
# Returns: list of all matching results
```

**With aliases:**
```python
scraper.build(
    html=html,
    wanted_dict={'product_name': 'iPhone 15', 'price': '$999'}
)
```

---

### `get_result_similar()`

Extract data from new pages using learned tag-based rules. Works on pages with the **same HTML structure**.

```python
scraper.get_result_similar(
    url=None,
    html=None,
    request_args=None,
    grouped=False,          # Group results by rule
    group_by_alias=False,   # Group by alias name
    unique=True             # Remove duplicates
)
# Returns: list of extracted values
```

---

### `get_result_flexible()` — Cross-Site Extraction

Extract data from pages with **completely different HTML structures**. Uses content fingerprinting instead of tag-based rules.

```python
scraper.get_result_flexible(
    url=None,
    html=None,
    request_args=None,
    min_score=0.4,          # Minimum fingerprint match score (0-1)
    unique=True
)
# Returns: list of extracted values
```

**How it works:**
1. During `build()`, alongside tag-based rules, a **content fingerprint** is created capturing the *data shape* — text length, word count, digit ratio, alpha ratio, currency presence, content type (text/price/date/url/code)
2. `get_result_flexible()` scans ALL text nodes on the new page and scores them against the fingerprint
3. Matches by **what the data looks like**, not what HTML tag wraps it

```python
# Site A: <h2 class="title">Sony Headphones</h2>
# Site B: <span data-name>Sony Headphones</span>
# Site C: <p id="prod">Sony Headphones</p>

# Learn from Site A, extract from B and C — all work!
scraper = DejavuScraper()
scraper.build(html=site_a, wanted_list=['Sony Headphones'])
scraper.get_result_flexible(html=site_b)  # ✅ Found
scraper.get_result_flexible(html=site_c)  # ✅ Found
```

---

### `get_result_exact()`

Get results grouped by rule, with optional alias grouping.

```python
scraper.get_result_exact(
    html=html,
    group_by_alias=True
)
# Returns: {'title': [...], 'price': [...]}
```

---

### `get_result()`

Generic extraction method that combines all result types.

```python
scraper.get_result(
    url=None, html=None,
    grouped=False,
    group_by_alias=False,
    unique=True
)
```

---

### Grouped Extraction

Extract multiple related fields per item (e.g., name + price + rating):

#### `build_grouped()`

```python
scraper.build_grouped(
    html=html,
    wanted_list=[
        ['iPhone 15', '$999'],      # Group 1: [field1, field2]
        ['Samsung Galaxy', '$899']   # Group 2
    ]
)
```

#### `get_result_grouped()`

```python
results = scraper.get_result_grouped(html=new_html)
# [['iPhone 15', '$999'], ['Samsung Galaxy', '$899'], ['Google Pixel', '$699']]
```

Handles missing fields gracefully — returns `None` for fields not found.

---

### Adaptive Extraction

Survives website structure changes using 8-dimension weighted similarity matching.

```python
scraper = DejavuScraper(adaptive=True, min_similarity=0.5)
scraper.build(html=original_html, wanted_list=['Breaking News'])

# Website changes its HTML structure...
results = scraper.get_result_similar(html=changed_html)
# Still finds the element!
```

**Similarity dimensions:**

| Dimension | Weight |
|-----------|--------|
| Tag name | 15% |
| Attributes | 20% |
| Text content | 15% |
| DOM path | 10% |
| Parent element | 15% |
| Grandparent element | 10% |
| Children structure | 10% |
| Special attributes | 5% |

#### Direct Adaptive API

```python
# Save element fingerprint
scraper.adaptive_save(element, identifier='product_title', url='https://...')

# Find element by fingerprint on changed page
element = scraper.adaptive_find(soup, identifier='product_title')

# Build with adaptive tracking
scraper.adaptive_build(html=html, wanted_list=['...'])

# Get results with adaptive fallback
results = scraper.get_result_adaptive(html=html)

# Find similar elements
similar = scraper.find_similar_elements(html=html, element=target)
```

---

## 🔍 Smart Extractors

Built-in extraction for common data types — no rules needed.

### Data Type Extraction

```python
scraper = DejavuScraper()

# Extract all data types at once
data = scraper.extract_data_types(html=html)
# {'email': [...], 'phone': [...], 'price': [...], 'date': [...], ...}

# Or extract specific types
emails = scraper.extract_emails(html=html)
phones = scraper.extract_phones(html=html)
prices = scraper.extract_prices(html=html, parse=True)  # parse=True returns floats
```

**Supported data types:**

| Type | Example |
|------|---------|
| `email` | `user@example.com` |
| `phone` | `+1-555-123-4567`, `(800) 555-9999` |
| `price` | `$999.99`, `€49.00`, `£29.99` |
| `date` | `2025-01-15`, `January 15, 2025`, `03/15/2025` |
| `url` | `https://www.example.com` |
| `number` | `42`, `3.14` |
| `rating` | `4.5 stars` |
| `percentage` | `25%`, `99.9%` |
| `mention` | `@username` |
| `hashtag` | `#trending` |
| `ip_address` | `192.168.1.1` |
| `time` | `14:30`, `2:30 PM` |

---

### Table Parsing

```python
# Extract all tables
tables = scraper.extract_tables(html=html, as_dicts=True)
# [{'headers': ['Name', 'Price'], 'rows': [{'Name': 'iPhone', 'Price': '$999'}, ...]}]

# Export table to CSV
csv_string = scraper.extract_table_to_csv(html=html, table_index=0)
```

---

### Pattern Detection

Automatically detect repeated patterns in HTML:

```python
# Detect lists (ul/ol, repeated siblings)
lists = scraper.detect_lists(html=html, min_items=3)

# Detect card-like layouts
cards = scraper.detect_cards(html=html, min_items=3)

# Auto-detect all patterns
patterns = scraper.auto_detect_patterns(html=html, min_occurrences=3)
# {'lists': [...], 'tables': [...], 'cards': [...]}
```

---

### Structured Data (JSON-LD, Meta Tags, Microdata)

```python
# Extract all structured data
data = scraper.extract_structured_data(html=html)
# {'json_ld': [...], 'meta_tags': {...}, 'microdata': [...]}

# Or individually
json_ld = scraper.extract_json_ld(html=html)
meta = scraper.extract_meta_tags(html=html)
# {'standard': {...}, 'og': {...}, 'twitter': {...}, 'other': {...}}
```

---

### Pagination Detection

```python
pagination = scraper.detect_pagination(html=html)
# {
#   'next': '/page/3',
#   'prev': '/page/1',
#   'current': 2,
#   'pages': [{'number': 1, 'url': '/page/1'}, ...]
# }
```

---

### Regex Extraction

```python
# Simple regex
prices = scraper.extract_with_regex(r'\$[\d,]+\.?\d*', html=html)

# Named groups
matches = scraper.extract_with_named_groups(
    r'(?P<name>\w+)@(?P<domain>[\w.]+)',
    html=html
)
# [{'name': 'john', 'domain': 'example.com'}, ...]
```

---

### Text Cleaning

```python
# Clean text
clean = scraper.clean_text("  Hello   World  &amp; entities  ", lowercase=True)

# Extract all visible text from HTML, cleaned
text = scraper.extract_clean_text(html=html)
```

---

### `smart_extract()` — All-in-One

Run all extractors at once:

```python
everything = scraper.smart_extract(html=html)
# {
#   'data_types': {'email': [...], 'price': [...], ...},
#   'patterns': {'lists': [...], 'tables': [...], 'cards': [...]},
#   'structured_data': {'json_ld': [...], 'meta_tags': {...}, 'microdata': [...]},
#   'pagination': {'next': ..., 'prev': ..., 'pages': [...]}
# }
```

---

## 💾 Save & Load

Save learned rules and fingerprints for reuse. Both formats support content fingerprints and adaptive data.

### JSON

```python
scraper.save('model.json')

new_scraper = DejavuScraper()
new_scraper.load('model.json')
```

### SQLite

```python
scraper.save('model.db')

new_scraper = DejavuScraper()
new_scraper.load('model.db')
```

Both formats use **atomic writes** (temp file + rename) — no data corruption on crash.

Format is auto-detected from file extension, or specify explicitly:
```python
scraper.save('model', format='json')   # or 'db', 'sqlite'
```

---

## 🔧 Rule Management

```python
# View all rules with their IDs
rules = scraper.stack_list
for rule in rules:
    print(rule['stack_id'], rule.get('alias'))

# Keep only specific rules
scraper.keep_rules(['rule_abc123', 'rule_def456'])

# Remove specific rules
scraper.remove_rules(['rule_abc123'])

# Set friendly aliases
scraper.set_rule_aliases({
    'rule_abc123': 'product_title',
    'rule_def456': 'product_price'
})

# Generate reusable Python code from current rules
code = scraper.generate_python_code()
print(code)
```

---

## 🏭 Production Features

### Rate Limiting

```python
scraper = DejavuScraper(rate_limit=2)  # 2 seconds between requests per domain
```

### Retry with Exponential Backoff

```python
scraper = DejavuScraper(max_retries=3, retry_backoff=1.0)
# Retries: 1s, 2s, 4s on 5xx errors and timeouts
```

### Connection Pooling

Sessions are reused with `requests.Session` (pool_maxsize=10) for better performance across multiple requests.

### Streaming Responses

HTML is downloaded in chunks (64KB) with a **10MB hard limit** — prevents memory bombs from huge pages.

### Custom Headers

```python
scraper = DejavuScraper()
scraper.request_headers = {
    'User-Agent': 'Custom Agent',
    'Accept-Language': 'en-US'
}

result = scraper.build(
    url='https://example.com',
    request_args={'timeout': 10, 'verify': False}
)
```

### Context Manager

```python
with DejavuScraper(rate_limit=1) as scraper:
    scraper.build(url='https://example.com', wanted_list=['data'])
    results = scraper.get_result_similar(url='https://example.com/page2')
# Session automatically closed
```

Or manually:
```python
scraper = DejavuScraper()
# ... use scraper ...
scraper.close()  # Closes the requests session
```

---

## 🧠 How It Works

### 1. Tag-Based Rules (`build` → `get_result_similar`)

```
BUILD:  Parse HTML → Find elements matching wanted text → Store tag/attribute rules
EXTRACT: Replay rules on new page → Find elements with same tags/attributes
```

Each rule stores: tag name, attributes (class, id, etc.), parent chain, and what to extract (text or href/src).

### 2. Content Fingerprinting (`build` → `get_result_flexible`)

```
BUILD:  Analyze matched text → Capture data shape (length, word count, digit ratio,
        alpha ratio, currency, content type) → Store fingerprint
EXTRACT: Scan ALL text nodes on new page → Score each against fingerprint → Return matches
```

This is what enables cross-site extraction — no LLM, no model, just pattern matching on data shape.

### 3. Adaptive Matching (`build` with `adaptive=True`)

```
BUILD:  Fingerprint each element across 8 dimensions (tag, attributes, text, DOM path,
        parent, grandparent, children, special attrs) → Store signature
EXTRACT: When tag rules fail → Compare all candidates using weighted similarity
         → Return best match above min_similarity threshold
```

---

## 🧪 Testing

```bash
# Run all test suites
python test_all.py              # 16 core tests
python test_comprehensive.py    # 61 tests across 15 categories
python test_extractors.py       # 40 tests for smart extractors
python test_cross_site.py       # 25 cross-site flexible extraction tests

# Total: 142 tests, 100% pass rate
```

**Test coverage includes:**
- Core build & extraction
- Same-site and cross-site extraction
- Grouped extraction with missing fields
- Save/Load JSON and SQLite (with fingerprints)
- Adaptive extraction with structure changes
- Fuzzy matching
- URL extraction
- Rule management (keep, remove, aliases)
- All 7 smart extractor classes
- Edge cases and large data handling
- Content fingerprint quality validation

---

## 📁 Project Structure

```
dejavu_scraper/
├── dejavu_scraper/
│   ├── __init__.py             # Package exports (v2.0.0)
│   ├── dejavu_scraper.py       # Main DejavuScraper class (~3000 lines)
│   ├── extractors.py           # 7 smart extractor classes (~1100 lines)
│   ├── adaptive_storage.py     # Thread-safe element fingerprint storage
│   ├── adaptive_matcher.py     # 8-dimension weighted similarity matching
│   ├── utils.py                # ResultItem, FuzzyText helpers
│   └── beautifulsoup4/         # Bundled BeautifulSoup4
├── test_all.py                 # 16 core tests
├── test_comprehensive.py       # 61 tests (15 categories)
├── test_extractors.py          # 40 extractor tests
├── test_cross_site.py          # 25 cross-site tests
├── DOCUMENTATION.md            # Detailed API documentation
├── ADAPTIVE_GUIDE.md           # Adaptive extraction deep-dive
├── TEST_DOCUMENTATION.md       # Test suite documentation
├── pyproject.toml              # Package configuration
├── requirements.txt            # Dependencies (requests>=2.25.0)
├── LICENSE                     # MIT License
└── README.md                   # This file
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Original [AutoScraper](https://github.com/alirezamika/autoscraper) by Alireza Mika
- Adaptive extraction inspired by [Scrapling](https://github.com/D4Vinci/Scrapling)
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) for HTML parsing
