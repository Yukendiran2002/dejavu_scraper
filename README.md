# 🕷️ Intelligent DejavuScraper

**A Smart, Automatic, Fast and Lightweight Web Scraper for Python with Adaptive Extraction**

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

DejavuScraper is an intelligent web scraping library that automatically learns scraping rules from examples. Just provide a sample of what you want to extract, and it figures out how to get similar data from any page with the same structure.

**Now enhanced with Adaptive Extraction** - elements can be relocated even after website structure changes using similarity-based matching algorithms.

---

## 📑 Table of Contents

- [Features](#-features)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [How DejavuScraper Works](#-how-DejavuScraper-works)
- [How Adaptive Extraction Works](#-how-adaptive-extraction-works)
- [API Reference](#-api-reference)
- [Advanced Usage](#-advanced-usage)
- [Save & Load Models](#-save--load-models)
- [Examples](#-examples)
- [Testing](#-testing)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎯 **Smart Learning** | Automatically learns scraping rules from examples |
| 🔄 **Adaptive Extraction** | Relocates elements even after website structure changes |
| 📦 **Grouped Extraction** | Extract multiple related fields per item |
| 💾 **Multiple Save Formats** | JSON and SQLite database support |
| 🎭 **Fuzzy Matching** | Approximate text matching with configurable ratio |
| 🔗 **URL Extraction** | Automatically extracts href/src attributes |
| ⚡ **Lightweight** | Minimal dependencies (requests + BeautifulSoup) |
| 🛡️ **Robust** | Handles missing fields gracefully |

---

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/Yukendiran2002/dejavu_scraper.git
cd dejavu_scraper

# Install dependencies
pip install requests
```

The project includes BeautifulSoup4 bundled, so no additional installation needed.

---

## 🚀 Quick Start

### Basic Example

```python
from dejavu_scraper import DejavuScraper

# Sample HTML (or use a URL)
html = """
<html>
<body>
  <div class="products">
    <div class="product">
      <h2 class="title">iPhone 15</h2>
      <span class="price">$999</span>
    </div>
    <div class="product">
      <h2 class="title">Samsung Galaxy</h2>
      <span class="price">$899</span>
    </div>
  </div>
</body>
</html>
"""

# Create scraper and build rules
scraper = DejavuScraper()
result = scraper.build(html=html, wanted_list=['iPhone 15'])

print(result)
# Output: ['iPhone 15', 'Samsung Galaxy']
```

### From URL

```python
scraper = DejavuScraper()
result = scraper.build(
    url='https://example.com/products',
    wanted_list=['Product Name Example']
)
```

---

## 🧠 How DejavuScraper Works

DejavuScraper uses a **rule-based learning approach** to automatically discover patterns in HTML:

### Step 1: Learning Phase (`build()`)

When you call `build()` with a `wanted_list`, DejavuScraper:

```
┌─────────────────────────────────────────────────────────────────┐
│                        BUILD PROCESS                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Parse HTML with BeautifulSoup                               │
│           ↓                                                      │
│  2. Find ALL elements containing wanted text                    │
│           ↓                                                      │
│  3. For each match, create a "stack" (extraction rule):         │
│     • Tag name (e.g., 'h2', 'span', 'a')                       │
│     • Attributes (e.g., class=['title'], style='')             │
│     • Path from root (parent → child relationships)            │
│     • Whether to extract text or attribute (href, src)         │
│           ↓                                                      │
│  4. Store rules in stack_list                                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Step 2: Extraction Phase (`get_result_similar()`)

When extracting from new pages:

```
┌─────────────────────────────────────────────────────────────────┐
│                      EXTRACTION PROCESS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  For each rule in stack_list:                                   │
│           ↓                                                      │
│  1. Start from document root                                    │
│           ↓                                                      │
│  2. Navigate using stored tag names + attributes                │
│           ↓                                                      │
│  3. Apply fuzzy matching if configured                          │
│           ↓                                                      │
│  4. Extract text content or specified attribute                 │
│           ↓                                                      │
│  5. Return all matching results                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Stack Structure

Each learned rule (stack) contains:

```python
{
    'content': [
        ('div', {'class': ['product']}),      # Level 1
        ('h2', {'class': ['title'], 'style': ''})  # Level 2 (target)
    ],
    'wanted_attr': None,        # None=text, 'href'=link, 'src'=image
    'is_full_url': False,       # Whether to resolve relative URLs
    'url': 'https://...',       # Source URL
    'stack_id': 'rule_abc123',  # Unique identifier
    'alias': 'product_title'    # Optional friendly name
}
```

---

## 🔄 How Adaptive Extraction Works

Adaptive extraction solves a critical problem: **websites change their structure**, breaking traditional scrapers. Our adaptive system can relocate elements even after HTML changes.

### Enable Adaptive Mode

```python
scraper = DejavuScraper(adaptive=True)
```

### The Adaptive Algorithm

```
┌─────────────────────────────────────────────────────────────────┐
│                   ADAPTIVE EXTRACTION FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  PHASE 1: FINGERPRINTING (during build)                         │
│  ─────────────────────────────────────                          │
│  For each found element, capture:                               │
│  • Tag name                                                      │
│  • All attributes (class, id, data-*, etc.)                     │
│  • Text content                                                  │
│  • DOM path (parent/child hierarchy)                            │
│  • Parent element properties                                     │
│  • Grandparent element properties                                │
│  • Children structure                                            │
│  • Special attributes (href, src, etc.)                         │
│                                                                  │
│  PHASE 2: SIMILARITY MATCHING (during extraction)               │
│  ───────────────────────────────────────────────                │
│  When structure changes:                                         │
│           ↓                                                      │
│  1. Extract properties from ALL candidate elements              │
│           ↓                                                      │
│  2. Calculate weighted similarity score:                        │
│     ┌──────────────────────────────────────┐                    │
│     │  tag_name:      15% weight           │                    │
│     │  attributes:    20% weight           │                    │
│     │  text:          15% weight           │                    │
│     │  path:          10% weight           │                    │
│     │  parent:        15% weight           │                    │
│     │  grandparent:   10% weight           │                    │
│     │  children:      10% weight           │                    │
│     │  special_attrs:  5% weight           │                    │
│     └──────────────────────────────────────┘                    │
│           ↓                                                      │
│  3. Return element with highest score > min_similarity          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Similarity Calculation Details

```python
# Text similarity uses SequenceMatcher
def _compare_text(text1, text2):
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

# Attribute comparison uses Jaccard similarity
def _compare_attributes(attrs1, attrs2):
    keys1, keys2 = set(attrs1.keys()), set(attrs2.keys())
    intersection = keys1 & keys2
    union = keys1 | keys2
    
    if not union:
        return 1.0
    
    # Compare both key overlap and value similarity
    key_score = len(intersection) / len(union)
    value_score = sum(SequenceMatcher(attrs1[k], attrs2[k]).ratio() 
                      for k in intersection) / max(len(intersection), 1)
    
    return (key_score + value_score) / 2
```

### Example: Handling Structure Changes

```python
# Original HTML
original = """
<div class="news">
  <article>
    <h2 class="title">Breaking News</h2>
  </article>
</div>
"""

# Changed HTML (different structure!)
changed = """
<section class="articles">
  <div class="card">
    <h3 class="headline">Breaking News</h3>  <!-- Different tag and class! -->
  </div>
</section>
"""

# Adaptive scraper handles this
scraper = DejavuScraper(adaptive=True)
scraper.build(html=original, wanted_list=['Breaking News'])

# Still finds the element despite structural changes
results = scraper.get_result_similar(html=changed)
# Output: ['Breaking News']
```

---

## 📚 API Reference

### DejavuScraper Class

```python
DejavuScraper(stack_list=None, adaptive=False, min_similarity=0.5)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `stack_list` | list | None | Pre-existing rules to use |
| `adaptive` | bool | False | Enable adaptive extraction |
| `min_similarity` | float | 0.5 | Minimum similarity for adaptive matching (0-1) |

### Core Methods

#### `build()`

Learn extraction rules from examples.

```python
scraper.build(
    url=None,           # URL to scrape
    wanted_list=None,   # List of example strings to find
    wanted_dict=None,   # Dict with aliases as keys
    html=None,          # HTML string (alternative to URL)
    request_args=None,  # Additional request parameters
    update=False,       # Add to existing rules
    text_fuzz_ratio=1.0 # Fuzzy matching ratio (0-1)
)
```

#### `get_result_similar()`

Get results using learned rules.

```python
scraper.get_result_similar(
    url=None,
    html=None,
    request_args=None,
    grouped=False,      # Return results grouped by rule
    group_by_alias=False,
    unique=True         # Remove duplicates
)
```

#### `build_grouped()`

Build rules for extracting multiple fields per item.

```python
scraper.build_grouped(
    url=None,
    html=None,
    wanted_list=None,   # List of lists: [['title1', 'price1'], ...]
    request_args=None
)
```

#### `get_result_grouped()`

Get grouped results (multiple fields per item).

```python
scraper.get_result_grouped(
    url=None,
    html=None,
    request_args=None
)
```

### Save/Load Methods

#### `save()`

```python
scraper.save(
    file_path,              # Path to save file
    format='auto',          # 'json', 'db', 'sqlite', or 'auto'
    include_adaptive=True   # Include adaptive data
)
```

#### `load()`

```python
scraper.load(file_path)  # Auto-detects format
```

### Rule Management

#### `keep_rules()`

Keep only specified rules.

```python
scraper.keep_rules(['rule_abc123', 'rule_def456'])
```

#### `remove_rules()`

Remove specified rules.

```python
scraper.remove_rules(['rule_abc123'])
```

#### `get_result_exact()`

Get results grouped by rule alias.

```python
scraper.get_result_exact(html=html, group_by_alias=True)
# Returns: {'title': [...], 'price': [...]}
```

---

## 🔧 Advanced Usage

### Grouped Extraction with Missing Fields

Extract multiple fields per item, handling missing data gracefully:

```python
html = """
<div class="products">
  <div class="product">
    <h3>Product 1</h3>
    <span class="price">$99</span>
  </div>
  <div class="product">
    <h3>Product 2</h3>
    <!-- No price! -->
  </div>
</div>
"""

scraper = DejavuScraper()
scraper.build_grouped(
    html=html,
    wanted_list=[['Product 1', '$99']]
)

results = scraper.get_result_grouped(html=html)
# [['Product 1', '$99'], ['Product 2', None]]
```

### Custom Request Headers

```python
scraper = DejavuScraper()
scraper.request_headers = {
    'User-Agent': 'Custom User Agent',
    'Accept-Language': 'en-US'
}

result = scraper.build(
    url='https://example.com',
    wanted_list=['Example'],
    request_args={'timeout': 10, 'verify': False}
)
```

### Fuzzy Text Matching

```python
scraper = DejavuScraper()
scraper.build(
    html=html,
    wanted_list=['Approximate Text'],
    text_fuzz_ratio=0.8  # 80% similarity required
)
```

---

## 💾 Save & Load Models

### JSON Format

```python
# Save
scraper.save('model.json')

# Load
new_scraper = DejavuScraper()
new_scraper.load('model.json')
```

JSON structure:
```json
{
  "stack_list": [...],
  "group_rules": {...},
  "adaptive_data": {...}
}
```

### SQLite Database Format

```python
# Save
scraper.save('model.db')

# Load
new_scraper = DejavuScraper()
new_scraper.load('model.db')
```

Benefits of SQLite:
- Better for large datasets
- Atomic operations
- Query support for debugging

---

## 📋 Examples

### E-commerce Product Scraping

```python
from dejavu_scraper import DejavuScraper

scraper = DejavuScraper()

# Train on product page
scraper.build_grouped(
    url='https://shop.example.com/products',
    wanted_list=[
        ['iPhone 15 Pro', '$1199', '4.8 stars', 'In Stock']
    ]
)

# Scrape all products
products = scraper.get_result_grouped(url='https://shop.example.com/products')

for product in products:
    name, price, rating, stock = product
    print(f"{name}: {price} ({rating}) - {stock}")
```

### News Article Extraction

```python
scraper = DejavuScraper(adaptive=True)

# Learn from one article
scraper.build(
    url='https://news.example.com',
    wanted_list=['Breaking: Major Event Happens']
)

# Save for reuse
scraper.save('news_scraper.json')

# Later: load and scrape updated page
scraper2 = DejavuScraper()
scraper2.load('news_scraper.json')

headlines = scraper2.get_result_similar(url='https://news.example.com')
```

### Multi-page Scraping

```python
scraper = DejavuScraper()
scraper.build(url='https://example.com/page1', wanted_list=['Item 1'])

all_results = []
for page in range(1, 11):
    results = scraper.get_result_similar(
        url=f'https://example.com/page{page}'
    )
    all_results.extend(results)
```

---

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_all.py
```

Test coverage:
- ✅ Simple build and extraction
- ✅ Get similar results
- ✅ Grouped extraction
- ✅ Save/Load JSON
- ✅ Save/Load SQLite
- ✅ Adaptive extraction
- ✅ Fuzzy matching
- ✅ URL extraction
- ✅ Rule management
- ✅ Edge cases

---

## 📁 Project Structure

```
dejavu_scraper/
├── dejavu_scraper/
│   ├── __init__.py           # Package exports
│   ├── dejavu_scraper.py     # Main DejavuScraper class
│   ├── adaptive_storage.py   # Element fingerprint storage
│   ├── adaptive_matcher.py   # Similarity matching algorithms
│   ├── utils.py              # Helper functions
│   └── beautifulsoup4/       # Bundled BeautifulSoup
├── test_all.py               # Comprehensive test suite
├── DOCUMENTATION.md          # Detailed documentation
└── README.md                 # This file
```

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License.

---

## 🙏 Acknowledgments

- Original [AutoScraper](https://github.com/alirezamika/autoscraper) by Alireza Mika
- Adaptive extraction inspired by [Scrapling](https://github.com/D4Vinci/Scrapling)
- [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) for HTML parsing
