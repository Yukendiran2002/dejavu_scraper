# Intelligent Scraper - Adaptive Extraction Guide

## Overview

The Intelligent Scraper now includes **Adaptive Extraction** capabilities inspired by [Scrapling](https://github.com/D4Vinci/Scrapling). This feature allows your scrapers to survive website structure changes by intelligently tracking and relocating elements.

## Key Features

### 🔄 Smart Element Tracking
When you save an element, the scraper stores its unique "fingerprint" including:
- Tag name and attributes
- Text content
- DOM path and depth
- Parent/grandparent information
- Children structure

### 🎯 Similarity-Based Matching
When the website structure changes, the scraper uses similarity algorithms to find the best matching element by comparing:
- Tag names (15% weight)
- Attributes (20% weight)
- Text content (15% weight)
- DOM path (10% weight)
- Parent structure (15% weight)
- Grandparent structure (10% weight)
- Children structure (10% weight)
- Special attributes like class, id, href (5% weight)

## Quick Start

### 1. Enable Adaptive Mode

```python
from autoscraper import AutoScraper

# Enable adaptive mode when creating the scraper
scraper = AutoScraper(adaptive=True)
```

### 2. Save Elements for Later Matching

```python
# Get your page
soup = scraper._get_soup(url='https://example.com')

# Find and save elements you want to track
product_title = soup.find('h3', class_='title')
scraper.adaptive_save(product_title, 'product_title', url='https://example.com')

# Save the price too
price = soup.find('span', class_='price')
scraper.adaptive_save(price, 'product_price', url='https://example.com')
```

### 3. Find Elements After Structure Changes

```python
# Later, when the website structure has changed:
element, score, all_matches = scraper.adaptive_find(
    'product_title',
    url='https://example.com'
)

if element:
    print(f"Found with {score*100:.1f}% confidence: {element.text}")
```

## API Reference

### `AutoScraper(adaptive=True, db_path=None, min_similarity=0.5)`

Initialize the scraper with adaptive mode.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `adaptive` | bool | False | Enable adaptive extraction mode |
| `db_path` | str | None | Path to SQLite database for storage |
| `min_similarity` | float | 0.5 | Minimum similarity score (0-1) |

### `adaptive_save(element, identifier, url=None)`

Save element properties for later adaptive matching.

```python
scraper.adaptive_save(element, 'my_element', url='https://example.com')
```

### `adaptive_find(identifier, url=None, html=None, soup=None, ...)`

Find elements using adaptive matching.

```python
element, score, matches = scraper.adaptive_find(
    'my_element',
    url='https://example.com',
    min_similarity=0.4  # Override default
)
```

Returns: `(best_match_element, similarity_score, all_matches_list)`

### `find_similar_elements(reference_element, ...)`

Find elements similar to a reference element on the page.

```python
# Find one product, then find all similar products
first_product = soup.find('div', class_='product')
similar = scraper.find_similar_elements(
    first_product,
    soup=soup,
    similarity_threshold=0.6
)

for element, score in similar:
    print(f"Found similar: {element.text} ({score*100:.1f}%)")
```

### `get_result_adaptive(url=None, identifiers=None, ...)`

Find multiple saved elements at once.

```python
results = scraper.get_result_adaptive(
    url='https://example.com',
    group_by_identifier=True
)

for identifier, matches in results.items():
    for match in matches:
        print(f"{identifier}: {match['text']} ({match['score']*100:.1f}%)")
```

### `adaptive_build(url=None, wanted_list=None, auto_save=True, ...)`

Build rules AND automatically save element properties.

```python
results = scraper.adaptive_build(
    url='https://example.com',
    wanted_dict={
        'title': ['Product Name'],
        'price': ['$19.99'],
    },
    auto_save=True
)
```

## How It Works

### Save Phase
When you call `adaptive_save()`:
1. Extracts all unique properties from the element
2. Generates a fingerprint including tag, attributes, text, path, parent info
3. Stores in SQLite database, isolated by domain

### Match Phase
When you call `adaptive_find()`:
1. Retrieves stored properties from database
2. Finds all elements with the same tag name
3. Calculates similarity score for each candidate
4. Returns the element with the highest score above the threshold

### Similarity Calculation
The similarity score is a weighted average of:
- **Tag match**: Must match exactly (15%)
- **Attributes**: Sequence matching on attribute values (20%)
- **Text**: Fuzzy text comparison (15%)
- **Path**: DOM path similarity with suffix weighting (10%)
- **Parent**: Parent tag and attributes (15%)
- **Grandparent**: Grandparent tag and attributes (10%)
- **Children**: Children tag sequence matching (10%)
- **Special attrs**: Class, ID, href, src comparison (5%)

## Best Practices

### 1. Use Descriptive Identifiers
```python
# Good
scraper.adaptive_save(element, 'product_title', url=url)
scraper.adaptive_save(element, 'checkout_button', url=url)

# Bad
scraper.adaptive_save(element, 'el1', url=url)
```

### 2. Always Include the URL
```python
# This isolates data per domain
scraper.adaptive_save(element, 'title', url='https://site-a.com')
scraper.adaptive_save(element, 'title', url='https://site-b.com')  # Different!
```

### 3. Adjust Similarity Threshold as Needed
```python
# More strict (fewer matches, higher confidence)
element, score, _ = scraper.adaptive_find('title', min_similarity=0.7)

# More lenient (more matches, lower confidence)
element, score, _ = scraper.adaptive_find('title', min_similarity=0.3)
```

### 4. Save Multiple Properties for Important Elements
```python
# Save the element itself
scraper.adaptive_save(product_div, 'product_container', url=url)

# Also save key child elements
scraper.adaptive_save(product_div.find('h3'), 'product_title', url=url)
scraper.adaptive_save(product_div.find('.price'), 'product_price', url=url)
```

## Comparison with Scrapling

| Feature | Intelligent Scraper | Scrapling |
|---------|---------------------|-----------|
| Adaptive extraction | ✅ | ✅ |
| SQLite storage | ✅ | ✅ |
| Similarity algorithms | ✅ | ✅ |
| Find similar elements | ✅ | ✅ |
| Rule-based scraping | ✅ | ❌ |
| Auto-learn from examples | ✅ | ❌ |
| Stealth fetching | ❌ | ✅ |
| Browser automation | ❌ | ✅ |

## Troubleshooting

### No Match Found
1. Check if data was saved: `scraper.adaptive_storage.list_identifiers(domain)`
2. Lower the similarity threshold: `min_similarity=0.3`
3. Make sure the URL domain matches

### Wrong Element Matched
1. Increase similarity threshold: `min_similarity=0.7`
2. Save more specific elements (children instead of parents)
3. Check the similarity scores of all matches

### Performance
- Use `selector` parameter to narrow candidates: `adaptive_find('title', selector='h1, h2, h3')`
- The database is SQLite - consider cleanup for old entries
