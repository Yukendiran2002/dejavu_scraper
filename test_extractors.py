"""
Test Advanced Extraction Features
=================================
Tests for SmartExtractor, PatternDetector, TableParser, etc.
"""

import sys
sys.path.insert(0, '.')

from dejavu_scraper import (
    DejavuScraper,
    SmartExtractor,
    PatternDetector,
    TableParser,
    StructuredDataExtractor,
    PaginationDetector,
    RegexExtractor,
    TextCleaner,
)

# ============================================================================
# TEST HTML SAMPLES
# ============================================================================

CONTACT_HTML = '''
<html>
<body>
  <div class="contact-info">
    <p>Email us at: contact@example.com or sales@company.org</p>
    <p>Call us: +1-555-123-4567 or (800) 555-9999</p>
    <p>Visit: https://www.example.com/contact</p>
  </div>
</body>
</html>
'''

ECOMMERCE_HTML = '''
<html>
<head>
  <title>Products - Best Store</title>
  <meta name="description" content="Shop our amazing products">
  <meta property="og:title" content="Products Page">
  <meta property="og:type" content="website">
  <script type="application/ld+json">
  {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "Sample Product",
    "price": "29.99"
  }
  </script>
</head>
<body>
  <div class="products">
    <div class="product-card">
      <h3 class="title">iPhone 15</h3>
      <span class="price">$999.99</span>
      <p class="desc">Latest smartphone</p>
      <img src="/img/iphone.jpg">
      <a href="/product/1">View</a>
    </div>
    <div class="product-card">
      <h3 class="title">MacBook Pro</h3>
      <span class="price">$1,999.00</span>
      <p class="desc">Professional laptop</p>
      <img src="/img/macbook.jpg">
      <a href="/product/2">View</a>
    </div>
    <div class="product-card">
      <h3 class="title">AirPods Pro</h3>
      <span class="price">$249.99</span>
      <p class="desc">Wireless earbuds</p>
      <img src="/img/airpods.jpg">
      <a href="/product/3">View</a>
    </div>
  </div>
</body>
</html>
'''

TABLE_HTML = '''
<html>
<body>
  <table id="data-table">
    <thead>
      <tr>
        <th>Name</th>
        <th>Email</th>
        <th>Phone</th>
        <th>Amount</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>John Doe</td>
        <td>john@example.com</td>
        <td>555-1234</td>
        <td>$150.00</td>
      </tr>
      <tr>
        <td>Jane Smith</td>
        <td>jane@example.com</td>
        <td>555-5678</td>
        <td>$250.50</td>
      </tr>
      <tr>
        <td>Bob Wilson</td>
        <td>bob@example.com</td>
        <td>555-9999</td>
        <td>$75.25</td>
      </tr>
    </tbody>
  </table>
</body>
</html>
'''

PAGINATION_HTML = '''
<html>
<body>
  <div class="content">
    <p>Page content here</p>
  </div>
  <nav class="pagination">
    <a href="/page/1" class="prev">« Previous</a>
    <a href="/page/1">1</a>
    <span class="current">2</span>
    <a href="/page/3">3</a>
    <a href="/page/4">4</a>
    <a href="/page/5">5</a>
    <a href="/page/3" class="next" rel="next">Next »</a>
  </nav>
</body>
</html>
'''

LIST_HTML = '''
<html>
<body>
  <ul class="features">
    <li>Feature 1: Fast performance</li>
    <li>Feature 2: Easy to use</li>
    <li>Feature 3: Reliable</li>
    <li>Feature 4: Secure</li>
    <li>Feature 5: Scalable</li>
  </ul>
  
  <div class="news">
    <article class="news-item">
      <h2>News Article 1</h2>
      <p>Summary 1</p>
    </article>
    <article class="news-item">
      <h2>News Article 2</h2>
      <p>Summary 2</p>
    </article>
    <article class="news-item">
      <h2>News Article 3</h2>
      <p>Summary 3</p>
    </article>
  </div>
</body>
</html>
'''

DATES_HTML = '''
<html>
<body>
  <div class="events">
    <p>Event 1: January 15, 2025</p>
    <p>Event 2: 2025-02-20</p>
    <p>Event 3: 03/15/2025</p>
    <p>Time: 2:30 PM</p>
    <p>Rating: 4.5 stars</p>
    <p>Discount: 25% off</p>
  </div>
</body>
</html>
'''

# ============================================================================
# TEST FUNCTIONS
# ============================================================================

def print_header(title):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def print_test(name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}: {name}")
    if details:
        print(f"         {details}")
    return passed

all_passed = True

# ============================================================================
# TEST 1: Smart Data Type Extraction
# ============================================================================
print_header("TEST 1: Smart Data Type Extraction")

scraper = DejavuScraper()

# Test email extraction
emails = scraper.extract_emails(html=CONTACT_HTML)
p = print_test("Extract emails", len(emails) == 2, f"Found: {emails}")
all_passed = all_passed and p

# Test phone extraction
phones = scraper.extract_phones(html=CONTACT_HTML)
p = print_test("Extract phones", len(phones) >= 2, f"Found: {phones}")
all_passed = all_passed and p

# Test URL extraction
urls = scraper.extract_data_types(html=CONTACT_HTML, data_types=['url'])
p = print_test("Extract URLs", 'url' in urls and len(urls['url']) >= 1, f"Found: {urls.get('url', [])}")
all_passed = all_passed and p

# Test price extraction
prices = scraper.extract_prices(html=ECOMMERCE_HTML)
p = print_test("Extract prices", len(prices) >= 3, f"Found: {prices}")
all_passed = all_passed and p

# Test price parsing
parsed_prices = scraper.extract_prices(html=ECOMMERCE_HTML, parse=True)
p = print_test("Parse prices to float", all(isinstance(p, float) for p in parsed_prices), f"Parsed: {parsed_prices}")
all_passed = all_passed and p

# Test date extraction
dates = scraper.extract_data_types(html=DATES_HTML, data_types=['date'])
p = print_test("Extract dates", 'date' in dates and len(dates['date']) >= 2, f"Found: {dates.get('date', [])}")
all_passed = all_passed and p

# Test rating extraction
ratings = scraper.extract_data_types(html=DATES_HTML, data_types=['rating'])
p = print_test("Extract ratings", 'rating' in ratings, f"Found: {ratings.get('rating', [])}")
all_passed = all_passed and p

# Test percentage extraction
percentages = scraper.extract_data_types(html=DATES_HTML, data_types=['percentage'])
p = print_test("Extract percentages", 'percentage' in percentages, f"Found: {percentages.get('percentage', [])}")
all_passed = all_passed and p

# ============================================================================
# TEST 2: Table Extraction
# ============================================================================
print_header("TEST 2: Table Extraction")

# Test table parsing
tables = scraper.extract_tables(html=TABLE_HTML)
p = print_test("Extract tables", len(tables) >= 1, f"Found {len(tables)} table(s)")
all_passed = all_passed and p

# Test table headers
if tables:
    headers = tables[0]['headers']
    p = print_test("Table has headers", 'Name' in headers and 'Email' in headers, f"Headers: {headers}")
    all_passed = all_passed and p
    
    # Test table data as dicts
    rows = tables[0]['as_dicts']
    p = print_test("Table rows as dicts", len(rows) == 3, f"Rows: {len(rows)}")
    all_passed = all_passed and p
    
    # Test specific cell value
    p = print_test("Correct cell values", rows[0]['Name'] == 'John Doe', f"First name: {rows[0].get('Name')}")
    all_passed = all_passed and p

# Test CSV export
csv = scraper.extract_table_to_csv(html=TABLE_HTML)
p = print_test("Export to CSV", 'John Doe' in csv and 'jane@example.com' in csv, f"CSV length: {len(csv)} chars")
all_passed = all_passed and p

# ============================================================================
# TEST 3: Auto Pattern Detection
# ============================================================================
print_header("TEST 3: Auto Pattern Detection")

# Test list detection
lists = scraper.detect_lists(html=LIST_HTML)
p = print_test("Detect lists", len(lists) >= 1, f"Found {len(lists)} list(s)")
all_passed = all_passed and p

# Test card detection
cards = scraper.detect_cards(html=ECOMMERCE_HTML)
p = print_test("Detect cards", len(cards) >= 1, f"Found {len(cards)} card pattern(s)")
all_passed = all_passed and p

# Test auto pattern detection
patterns = scraper.auto_detect_patterns(html=ECOMMERCE_HTML)
p = print_test("Auto detect all patterns", 'lists' in patterns and 'cards' in patterns, f"Pattern types: {list(patterns.keys())}")
all_passed = all_passed and p

# ============================================================================
# TEST 4: Structured Data Extraction
# ============================================================================
print_header("TEST 4: Structured Data Extraction")

# Test JSON-LD extraction
json_ld = scraper.extract_json_ld(html=ECOMMERCE_HTML)
p = print_test("Extract JSON-LD", len(json_ld) >= 1, f"Found {len(json_ld)} JSON-LD block(s)")
all_passed = all_passed and p

if json_ld:
    p = print_test("JSON-LD content valid", json_ld[0].get('@type') == 'Product', f"Type: {json_ld[0].get('@type')}")
    all_passed = all_passed and p

# Test meta tags extraction
meta = scraper.extract_meta_tags(html=ECOMMERCE_HTML)
p = print_test("Extract meta tags", 'og' in meta and 'standard' in meta, f"Meta types: {list(meta.keys())}")
all_passed = all_passed and p

p = print_test("Open Graph title", meta['og'].get('title') == 'Products Page', f"OG title: {meta['og'].get('title')}")
all_passed = all_passed and p

# Test full structured data extraction
structured = scraper.extract_structured_data(html=ECOMMERCE_HTML)
p = print_test("Full structured data", all(k in structured for k in ['json_ld', 'meta_tags', 'microdata']), f"Keys: {list(structured.keys())}")
all_passed = all_passed and p

# ============================================================================
# TEST 5: Pagination Detection
# ============================================================================
print_header("TEST 5: Pagination Detection")

pagination = scraper.detect_pagination(html=PAGINATION_HTML)

p = print_test("Detect pagination", pagination is not None, f"Found pagination data")
all_passed = all_passed and p

p = print_test("Next page link", pagination.get('next') == '/page/3', f"Next: {pagination.get('next')}")
all_passed = all_passed and p

p = print_test("Previous page link", pagination.get('prev') == '/page/1', f"Prev: {pagination.get('prev')}")
all_passed = all_passed and p

p = print_test("Page links detected", len(pagination.get('pages', [])) >= 3, f"Pages: {pagination.get('pages')}")
all_passed = all_passed and p

# ============================================================================
# TEST 6: Regex Extraction
# ============================================================================
print_header("TEST 6: Regex Extraction")

# Test simple regex
prices_regex = scraper.extract_with_regex(r'\$[\d,]+\.\d{2}', html=ECOMMERCE_HTML)
p = print_test("Regex extraction", len(prices_regex) >= 3, f"Found: {prices_regex}")
all_passed = all_passed and p

# Test named groups
pattern = r'(?P<name>\w+)@(?P<domain>[\w.]+)'
named = scraper.extract_with_named_groups(pattern, html=TABLE_HTML)
p = print_test("Named groups extraction", len(named) >= 3, f"Found: {named}")
all_passed = all_passed and p

if named:
    p = print_test("Named group keys", 'name' in named[0] and 'domain' in named[0], f"First match: {named[0]}")
    all_passed = all_passed and p

# ============================================================================
# TEST 7: Text Cleaning
# ============================================================================
print_header("TEST 7: Text Cleaning")

messy_text = "   Hello   World   \n\n\n  Multiple spaces   &amp; entities  "

cleaned = scraper.clean_text(messy_text)
p = print_test("Basic text cleaning", '& entities' in cleaned, f"Cleaned: '{cleaned}'")
all_passed = all_passed and p

cleaned_lower = scraper.clean_text(messy_text, lowercase=True)
p = print_test("Lowercase option", 'hello' in cleaned_lower, f"Lowercase: '{cleaned_lower}'")
all_passed = all_passed and p

# Test extract clean text
clean_page = scraper.extract_clean_text(html=ECOMMERCE_HTML)
p = print_test("Extract clean text", 'iPhone 15' in clean_page and len(clean_page) > 50, f"Length: {len(clean_page)}")
all_passed = all_passed and p

# ============================================================================
# TEST 8: Smart Extract (All-in-One)
# ============================================================================
print_header("TEST 8: Smart Extract (All-in-One)")

result = scraper.smart_extract(html=ECOMMERCE_HTML)

p = print_test("Smart extract returns all types", 
               all(k in result for k in ['data_types', 'patterns', 'structured_data', 'pagination']),
               f"Keys: {list(result.keys())}")
all_passed = all_passed and p

p = print_test("Data types extracted", 'price' in result['data_types'], f"Data types: {list(result['data_types'].keys())}")
all_passed = all_passed and p

p = print_test("Patterns detected", 'cards' in result['patterns'], f"Pattern types: {list(result['patterns'].keys())}")
all_passed = all_passed and p

# ============================================================================
# TEST 9: Direct SmartExtractor Class Usage
# ============================================================================
print_header("TEST 9: Direct SmartExtractor Class Usage")

text = "Contact: john@email.com, Price: $99.99, Date: 2025-01-20, Rating: 4.5 stars"

all_data = SmartExtractor.extract_all(text)
p = print_test("SmartExtractor.extract_all", len(all_data) >= 3, f"Types found: {list(all_data.keys())}")
all_passed = all_passed and p

emails = SmartExtractor.extract_emails(text)
p = print_test("SmartExtractor.extract_emails", 'john@email.com' in emails, f"Emails: {emails}")
all_passed = all_passed and p

price_value = SmartExtractor.parse_price("$1,299.99")
p = print_test("SmartExtractor.parse_price", price_value == 1299.99, f"Parsed: {price_value}")
all_passed = all_passed and p

# ============================================================================
# TEST 10: TextCleaner Class
# ============================================================================
print_header("TEST 10: TextCleaner Class")

sentences = TextCleaner.extract_sentences("Hello world. How are you? I'm fine!")
p = print_test("Extract sentences", len(sentences) == 3, f"Sentences: {sentences}")
all_passed = all_passed and p

truncated = TextCleaner.truncate("This is a very long text that needs to be truncated", max_length=30)
p = print_test("Truncate text", len(truncated) <= 30 and truncated.endswith('...'), f"Truncated: '{truncated}'")
all_passed = all_passed and p

# ============================================================================
# SUMMARY
# ============================================================================
print("\n" + "=" * 70)
print(" TEST SUMMARY")
print("=" * 70)

if all_passed:
    print("\n  🎉 ALL ADVANCED EXTRACTION TESTS PASSED!")
else:
    print("\n  ⚠️  SOME TESTS FAILED")

print("\n" + "=" * 70)
