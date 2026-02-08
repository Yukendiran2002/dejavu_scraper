# DejavuScraper with Adaptive Extraction

## Complete Documentation

A smart, automatic, and adaptive web scraper for Python that learns extraction rules and can find elements even after website structure changes.

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Core Concepts](#core-concepts)
4. [Basic Usage](#basic-usage)
5. [Grouped Extraction](#grouped-extraction)
6. [Adaptive Extraction](#adaptive-extraction)
7. [Save and Load Models](#save-and-load-models)
8. [API Reference](#api-reference)
9. [Examples](#examples)
10. [Best Practices](#best-practices)

---

## Installation

```python
# The module is self-contained, just import it
from dejavu_scraper import DejavuScraper
```

### Dependencies
- `requests` - For fetching web pages
- `beautifulsoup4` - For parsing HTML (included in package)

---

## Quick Start

```python
from dejavu_scraper import DejavuScraper

# Create scraper with adaptive mode enabled
scraper = DejavuScraper(adaptive=True)

# Train on sample data
html = '''
<div class="product">
    <h3 class="name">iPhone 15 Pro</h3>
    <span class="price">$999</span>
</div>
<div class="product">
    <h3 class="name">Samsung Galaxy S24</h3>
    <span class="price">$899</span>
</div>
'''

# Simple extraction (flat list)
result = scraper.build(html=html, wanted_list=['iPhone 15 Pro', '$999'])
print(result)  # ['iPhone 15 Pro', 'Samsung Galaxy S24', '$999', '$899']

# Grouped extraction (list of lists)
result = scraper.build_grouped(html=html, wanted_list=[
    ['iPhone 15 Pro', '$999'],
    ['Samsung Galaxy S24', '$899']
])
print(result)  # [['iPhone 15 Pro', '$999'], ['Samsung Galaxy S24', '$899']]

# Save model
scraper.save('my_scraper.json')

# Load and use later
new_scraper = DejavuScraper(adaptive=True)
new_scraper.load('my_scraper.json')
result = new_scraper.get_result_grouped(html=new_html)
```

---

## Core Concepts

### 1. Standard Mode vs Adaptive Mode

| Feature | Standard Mode | Adaptive Mode |
|---------|--------------|---------------|
| Create | `DejavuScraper()` | `DejavuScraper(adaptive=True)` |
| Learning | CSS selectors only | CSS + element fingerprints |
| Structure changes | ❌ Breaks | ✅ Falls back to similarity matching |
| File size | Smaller | Larger (stores fingerprints) |

### 2. Flat vs Grouped Extraction

| Type | Method | Output | Use Case |
|------|--------|--------|----------|
| Flat | `build()` | `['a', 'b', 'c', 'd']` | Simple lists |
| Grouped | `build_grouped()` | `[['a', 'b'], ['c', 'd']]` | Products, articles |

### 3. Input Options

```python
# Option 1: HTML string
scraper.build(html='<html>...</html>', wanted_list=[...])

# Option 2: URL (auto-fetches HTML)
scraper.build(url='https://example.com', wanted_list=[...])

# Option 3: Both (HTML content, URL for domain tracking)
scraper.build(url='https://example.com', html='<html>...</html>', wanted_list=[...])
```

---

## Basic Usage

### Training the Scraper

```python
from dejavu_scraper import DejavuScraper

scraper = DejavuScraper(adaptive=True)

# Method 1: Using wanted_list (simple)
result = scraper.build(
    html=html_content,           # or url='https://...'
    wanted_list=['Product Name', '$99.99', 'Buy Now']
)

# Method 2: Using wanted_dict (with aliases)
result = scraper.build(
    html=html_content,
    wanted_dict={
        'product_name': ['iPhone 15 Pro'],
        'price': ['$999'],
        'link': ['https://apple.com/buy']
    }
)
```

### Getting Results

```python
# Similar results (finds elements with similar structure)
result = scraper.get_result_similar(html=new_html)

# Exact results (stricter matching)
result = scraper.get_result_exact(html=new_html)

# Combined results
result = scraper.get_result(html=new_html)

# Grouped results (for grouped training)
result = scraper.get_result_grouped(html=new_html)
```

### Result Options

```python
# Get unique results only
result = scraper.get_result_similar(html=html, unique=True)

# Group by rule ID
result = scraper.get_result_similar(html=html, grouped=True)
# Returns: {'rule_abc123': ['value1', 'value2'], 'rule_def456': ['value3']}

# Group by alias
result = scraper.get_result_similar(html=html, group_by_alias=True)
# Returns: {'product_name': ['iPhone', 'Samsung'], 'price': ['$999', '$899']}

# Keep blank/empty values
result = scraper.get_result_similar(html=html, keep_blank=True)

# Maintain page order
result = scraper.get_result_similar(html=html, keep_order=True)
```

---

## Grouped Extraction

### Training with Groups

```python
scraper = DejavuScraper(adaptive=True)

# Each inner list = one item's attributes
# [name, price, link] for each product
wanted_list = [
    ['iPhone 15 Pro', '$999', 'https://apple.com/iphone'],
    ['Samsung Galaxy S24', '$899', 'https://samsung.com/galaxy']
]

result = scraper.build_grouped(
    html=html_content,
    wanted_list=wanted_list
)
# Returns: [
#   ['iPhone 15 Pro', '$999', 'https://apple.com/iphone'],
#   ['Samsung Galaxy S24', '$899', 'https://samsung.com/galaxy'],
#   ['Google Pixel 8', '$699', 'https://google.com/pixel']  # Found similar!
# ]
```

### Getting Grouped Results

```python
# As list of lists (default)
result = scraper.get_result_grouped(html=new_html)
# [['Product1', '$100', 'link1'], ['Product2', '$200', 'link2']]

# As list of tuples
result = scraper.get_result_grouped(html=new_html, output_format='tuple')
# [('Product1', '$100', 'link1'), ('Product2', '$200', 'link2')]
```

### Use Cases for Grouped Extraction

| Use Case | Attributes | Example |
|----------|------------|---------|
| E-commerce | name, price, rating, link | Product listings |
| News | headline, author, date, summary | Article lists |
| Jobs | title, company, location, salary | Job boards |
| Real Estate | address, price, beds, baths, sqft | Property listings |
| Press Releases | title, date, summary, link | News feeds |

---

## Adaptive Extraction

### How It Works

1. **Training**: Saves element "fingerprints" (tag, attributes, position, parent structure)
2. **Normal extraction**: Uses CSS rules first
3. **Fallback**: If CSS rules fail, uses similarity matching to find elements

### Similarity Matching Weights

| Property | Weight | Description |
|----------|--------|-------------|
| Tag name | 15% | HTML tag (div, span, h1, etc.) |
| Attributes | 20% | Classes, styles |
| Text content | 15% | Inner text |
| DOM path | 10% | Path from root |
| Parent | 15% | Parent element properties |
| Grandparent | 10% | Grandparent properties |
| Children | 10% | Child element tags |
| Special attrs | 5% | ID, data-* attributes |

### Configuring Similarity

```python
# Set minimum similarity threshold (0.0 to 1.0)
scraper = DejavuScraper(adaptive=True, min_similarity=0.5)

# Lower = more matches but less accurate
# Higher = fewer matches but more accurate
```

### Manual Adaptive Methods

```python
# Save element fingerprint manually
scraper.adaptive_save(element, identifier='product_title', url='https://...')

# Find element by identifier
element, score, properties = scraper.adaptive_find(
    identifier='product_title',
    html=new_html
)

# Find similar elements to a reference
similar = scraper.find_similar_elements(
    reference_element,
    soup=soup,
    similarity_threshold=0.6
)
```

---

## Save and Load Models

### JSON Format (Default)

```python
# Save as JSON
scraper.save('model.json')
scraper.save('model.json', format='json')

# Load from JSON
scraper.load('model.json')
scraper.load('model.json', format='json')
```

**JSON Structure:**
```json
{
  "stack_list": [...],        // Extraction rules
  "group_rules": [...],       // Grouped extraction metadata
  "adaptive_data": {          // Element fingerprints
    "domain.com": {
      "group_0_attr_0": {...},
      "group_0_attr_1": {...}
    }
  }
}
```

### SQLite Database Format

```python
# Save as SQLite database
scraper.save('model.db')
scraper.save('model.db', format='db')
scraper.save('model.sqlite', format='sqlite')

# Load from database
scraper.load('model.db')
scraper.load('model.db', format='db')
```

**Database Tables:**
| Table | Description |
|-------|-------------|
| `metadata` | Version, settings |
| `stack_list` | Extraction rules |
| `group_rules` | Group definitions |
| `adaptive_data` | Element fingerprints |

### Auto Format Detection

```python
# Automatically detects format from extension
scraper.save('model.json')  # → JSON
scraper.save('model.db')    # → SQLite
scraper.save('model.sqlite3')  # → SQLite

scraper.load('model.json')  # → Loads JSON
scraper.load('model.db')    # → Loads SQLite
```

### Format Comparison

| Feature | JSON | SQLite |
|---------|------|--------|
| File extension | `.json` | `.db`, `.sqlite`, `.sqlite3` |
| Human readable | ✅ Yes | ❌ No |
| Queryable | ❌ No | ✅ Yes (SQL) |
| File size | Smaller | Larger |
| Best for | Simple use | Large datasets |

### Save/Load Options

```python
# Don't include adaptive data (smaller file)
scraper.save('model.json', include_adaptive=False)

# Don't load adaptive data
scraper.load('model.json', include_adaptive=False)
```

---

## API Reference

### DejavuScraper Class

#### Constructor

```python
DejavuScraper(
    stack_list=None,      # Pre-existing rules
    adaptive=False,       # Enable adaptive mode
    min_similarity=0.5    # Minimum similarity threshold (0.0-1.0)
)
```

#### Training Methods

| Method | Description |
|--------|-------------|
| `build(url, html, wanted_list, wanted_dict, update, text_fuzz_ratio)` | Train on flat wanted list |
| `build_grouped(url, html, wanted_list, update, text_fuzz_ratio)` | Train on grouped wanted list |

#### Extraction Methods

| Method | Description |
|--------|-------------|
| `get_result_similar(...)` | Get results using similar matching |
| `get_result_exact(...)` | Get results using exact matching |
| `get_result(...)` | Get both similar and exact results |
| `get_result_grouped(...)` | Get grouped results |
| `get_result_adaptive(...)` | Get results using adaptive matching only |

#### Save/Load Methods

| Method | Description |
|--------|-------------|
| `save(file_path, format, include_adaptive)` | Save model to file |
| `load(file_path, format, include_adaptive)` | Load model from file |

#### Rule Management Methods

| Method | Description |
|--------|-------------|
| `remove_rules(rules)` | Remove specific rules |
| `keep_rules(rules)` | Keep only specific rules |
| `get_rules()` | Get all rule IDs |
| `set_rule_aliases(alias_dict)` | Set aliases for rules |

#### Adaptive Methods

| Method | Description |
|--------|-------------|
| `adaptive_save(element, identifier, url)` | Save element fingerprint |
| `adaptive_find(identifier, url, html, soup, min_similarity)` | Find element by fingerprint |
| `find_similar_elements(reference_element, url, html, soup, similarity_threshold)` | Find similar elements |

### Common Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `url` | str | URL to fetch HTML from |
| `html` | str | HTML string to parse |
| `soup` | BeautifulSoup | Pre-parsed soup object |
| `request_args` | dict | Arguments for requests (headers, proxies, etc.) |
| `grouped` | bool | Group results by rule ID |
| `group_by_alias` | bool | Group results by alias |
| `unique` | bool | Remove duplicate results |
| `keep_blank` | bool | Include empty/blank results |
| `keep_order` | bool | Maintain page order |
| `attr_fuzz_ratio` | float | Fuzzy matching ratio for attributes |
| `text_fuzz_ratio` | float | Fuzzy matching ratio for text |

---

## Examples

### Example 1: E-commerce Product Scraping

```python
from dejavu_scraper import DejavuScraper

scraper = DejavuScraper(adaptive=True)

html = '''
<div class="products">
    <div class="product-card">
        <h3 class="product-name">iPhone 15 Pro</h3>
        <span class="price">$999</span>
        <div class="rating">4.8 stars</div>
        <a href="/buy/iphone" class="buy-btn">Buy Now</a>
    </div>
    <div class="product-card">
        <h3 class="product-name">Samsung Galaxy S24</h3>
        <span class="price">$899</span>
        <div class="rating">4.7 stars</div>
        <a href="/buy/samsung" class="buy-btn">Buy Now</a>
    </div>
</div>
'''

# Train with grouped data
wanted = [
    ['iPhone 15 Pro', '$999', '4.8 stars', '/buy/iphone'],
    ['Samsung Galaxy S24', '$899', '4.7 stars', '/buy/samsung']
]

result = scraper.build_grouped(html=html, wanted_list=wanted)
print(result)

# Save model
scraper.save('ecommerce_scraper.json')

# Later: Load and use on different site structure
scraper2 = DejavuScraper(adaptive=True)
scraper2.load('ecommerce_scraper.json')

new_html = '''
<ul class="items">
    <li class="item">
        <span class="title">MacBook Pro</span>
        <span class="cost">$2499</span>
        <span class="stars">4.9 stars</span>
        <a href="/shop/macbook">Purchase</a>
    </li>
</ul>
'''

result = scraper2.get_result_grouped(html=new_html)
print(result)  # [['MacBook Pro', '$2499', '4.9 stars', '/shop/macbook']]
```

### Example 2: News Article Scraping

```python
from dejavu_scraper import DejavuScraper

scraper = DejavuScraper(adaptive=True)

html = '''
<div class="news-feed">
    <article class="news-item">
        <h1 class="headline">Breaking: Major Discovery Announced</h1>
        <span class="author">By John Smith</span>
        <time class="date">2026-01-19</time>
        <p class="summary">Scientists reveal groundbreaking findings...</p>
    </article>
    <article class="news-item">
        <h1 class="headline">Tech Giants Report Record Earnings</h1>
        <span class="author">By Jane Doe</span>
        <time class="date">2026-01-18</time>
        <p class="summary">Major technology companies exceeded expectations...</p>
    </article>
</div>
'''

wanted = [
    ['Breaking: Major Discovery Announced', 'By John Smith', '2026-01-19'],
    ['Tech Giants Report Record Earnings', 'By Jane Doe', '2026-01-18']
]

result = scraper.build_grouped(html=html, wanted_list=wanted)
scraper.save('news_scraper.db')  # Save as SQLite
```

### Example 3: Job Listings

```python
from dejavu_scraper import DejavuScraper

scraper = DejavuScraper(adaptive=True)

html = '''
<div class="job-board">
    <div class="job">
        <h2 class="title">Software Engineer</h2>
        <span class="company">Google</span>
        <span class="location">Mountain View, CA</span>
        <span class="salary">$150,000 - $200,000</span>
    </div>
    <div class="job">
        <h2 class="title">Data Scientist</h2>
        <span class="company">Meta</span>
        <span class="location">Menlo Park, CA</span>
        <span class="salary">$140,000 - $190,000</span>
    </div>
</div>
'''

wanted = [
    ['Software Engineer', 'Google', 'Mountain View, CA', '$150,000 - $200,000'],
    ['Data Scientist', 'Meta', 'Menlo Park, CA', '$140,000 - $190,000']
]

result = scraper.build_grouped(html=html, wanted_list=wanted)
print(result)

# Get results as tuples
result_tuples = scraper.get_result_grouped(html=html, output_format='tuple')
for job in result_tuples:
    title, company, location, salary = job
    print(f"{title} at {company} - {location} - {salary}")
```

### Example 4: Using with Real URLs

```python
from dejavu_scraper import DejavuScraper

scraper = DejavuScraper(adaptive=True)

# Train on a real website
result = scraper.build(
    url='https://example.com/products',
    wanted_list=['Example Product', '$99.99']
)

# Use custom headers
result = scraper.get_result_similar(
    url='https://example.com/products',
    request_args={
        'headers': {
            'User-Agent': 'Mozilla/5.0 ...',
            'Accept-Language': 'en-US,en;q=0.9'
        },
        'timeout': 10
    }
)
```

### Example 5: Handling Multiple Aliases

```python
from dejavu_scraper import DejavuScraper

scraper = DejavuScraper(adaptive=True)

# Train with aliases
result = scraper.build(
    html=html,
    wanted_dict={
        'product_name': ['iPhone 15 Pro', 'Samsung Galaxy S24'],
        'price': ['$999', '$899'],
        'rating': ['4.8 stars', '4.7 stars']
    }
)

# Get results grouped by alias
result = scraper.get_result_similar(html=new_html, group_by_alias=True)
# {
#   'product_name': ['MacBook Pro', 'Dell XPS'],
#   'price': ['$2499', '$1299'],
#   'rating': ['4.9 stars', '4.6 stars']
# }
```

---

## Best Practices

### 1. Training Data Quality

```python
# ✅ GOOD: Provide multiple examples
wanted = [
    ['iPhone 15 Pro', '$999', '4.8 stars'],
    ['Samsung Galaxy S24', '$899', '4.7 stars']
]

# ❌ BAD: Single example may not generalize
wanted = [['iPhone 15 Pro', '$999', '4.8 stars']]
```

### 2. Use Adaptive Mode for Resilience

```python
# ✅ For production: Use adaptive mode
scraper = DejavuScraper(adaptive=True)

# ❌ For quick tests: Standard mode is fine
scraper = DejavuScraper()
```

### 3. Save Models After Training

```python
# Always save after successful training
scraper.build_grouped(html=html, wanted_list=wanted)
scraper.save('my_scraper.json')  # Don't lose your work!
```

### 4. Handle Missing Data

```python
# Enable keep_blank to see missing values
result = scraper.get_result_grouped(html=html, keep_blank=True)
# [['Product1', '$100', ''], ['Product2', '', 'link2']]
```

### 5. Choose the Right Format

```python
# JSON for: Simple storage, human-readable, version control
scraper.save('model.json')

# SQLite for: Large models, querying, complex data
scraper.save('model.db')
```

### 6. Adjust Similarity Threshold

```python
# Strict matching (fewer false positives)
scraper = DejavuScraper(adaptive=True, min_similarity=0.7)

# Loose matching (catches more, but may have errors)
scraper = DejavuScraper(adaptive=True, min_similarity=0.3)
```

---

## Troubleshooting

### Issue: No results found

```python
# 1. Check if training was successful
print(len(scraper.stack_list))  # Should be > 0

# 2. Try with lower similarity threshold
scraper = DejavuScraper(adaptive=True, min_similarity=0.3)

# 3. Enable keep_blank to see empty results
result = scraper.get_result_grouped(html=html, keep_blank=True)
```

### Issue: Wrong elements extracted

```python
# 1. Provide more training examples
# 2. Use more specific wanted values
# 3. Remove bad rules
scraper.remove_rules(['rule_bad123'])
```

### Issue: Structure changed, no adaptive fallback

```python
# Make sure adaptive mode is enabled
scraper = DejavuScraper(adaptive=True)  # ✅

# Make sure adaptive data was saved
scraper.save('model.json', include_adaptive=True)  # ✅

# Make sure adaptive data was loaded
scraper.load('model.json', include_adaptive=True)  # ✅
```

---

## Version History

- **v1.0** - Basic DejavuScraper functionality
- **v2.0** - Added adaptive extraction (inspired by Scrapling)
- **v2.1** - Added grouped extraction (`build_grouped`, `get_result_grouped`)
- **v2.2** - Added SQLite database save/load format

---

## License

MIT License - See LICENSE file for details.
