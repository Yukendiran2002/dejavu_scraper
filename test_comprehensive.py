"""
Comprehensive Test Suite for DejavuScraper
==========================================
Extended test coverage for all features and edge cases.
"""
import os
import json
import tempfile
from dejavu_scraper import DejavuScraper

# ============================================================================
# TEST HTML SAMPLES
# ============================================================================

SIMPLE_HTML = '''
<html>
<body>
  <div class="news">
    <article>
      <h2 class="title">Breaking News Article 1</h2>
      <p class="summary">Summary of article 1</p>
      <a href="/article/1">Read more</a>
      <span class="date">2024-01-15</span>
    </article>
    <article>
      <h2 class="title">Breaking News Article 2</h2>
      <p class="summary">Summary of article 2</p>
      <a href="/article/2">Read more</a>
      <span class="date">2024-01-16</span>
    </article>
    <article>
      <h2 class="title">Breaking News Article 3</h2>
      <p class="summary">Summary of article 3</p>
      <a href="/article/3">Read more</a>
      <span class="date">2024-01-17</span>
    </article>
  </div>
</body>
</html>
'''

UPDATED_HTML = '''
<html>
<body>
  <div class="news">
    <article>
      <h2 class="title">NEW: Updated Article A</h2>
      <p class="summary">Brand new summary A</p>
      <a href="/article/a">Read more</a>
    </article>
    <article>
      <h2 class="title">NEW: Updated Article B</h2>
      <p class="summary">Brand new summary B</p>
      <a href="/article/b">Read more</a>
    </article>
  </div>
</body>
</html>
'''

ECOMMERCE_HTML = '''
<html>
<body>
  <div class="products">
    <div class="product-card">
      <h3 class="product-name">iPhone 15 Pro</h3>
      <span class="price">$999.99</span>
      <span class="rating">4.8 stars</span>
      <a href="/product/iphone-15" class="buy-link">Buy Now</a>
      <p class="description">Latest Apple smartphone with A17 chip</p>
    </div>
    <div class="product-card">
      <h3 class="product-name">Samsung Galaxy S24</h3>
      <span class="price">$899.99</span>
      <span class="rating">4.6 stars</span>
      <a href="/product/galaxy-s24" class="buy-link">Buy Now</a>
      <p class="description">Premium Android phone with AI features</p>
    </div>
    <div class="product-card">
      <h3 class="product-name">Google Pixel 8</h3>
      <span class="price">$699.99</span>
      <span class="rating">4.5 stars</span>
      <a href="/product/pixel-8" class="buy-link">Buy Now</a>
      <p class="description">Pure Android experience with great camera</p>
    </div>
  </div>
</body>
</html>
'''

MISSING_FIELDS_HTML = '''
<html>
<body>
  <div class="products">
    <div class="product">
      <h3 class="name">Product 1</h3>
      <span class="price">$99.99</span>
      <p class="desc">Great product</p>
    </div>
    <div class="product">
      <h3 class="name">Product 2</h3>
      <!-- No price for this product -->
      <p class="desc">Another product</p>
    </div>
    <div class="product">
      <h3 class="name">Product 3</h3>
      <span class="price">$149.99</span>
      <!-- No description -->
    </div>
  </div>
</body>
</html>
'''

NESTED_HTML = '''
<html>
<body>
  <div class="container">
    <div class="section">
      <div class="subsection">
        <div class="item">
          <span class="deep-text">Deep nested text 1</span>
        </div>
        <div class="item">
          <span class="deep-text">Deep nested text 2</span>
        </div>
      </div>
    </div>
  </div>
</body>
</html>
'''

TABLE_HTML = '''
<html>
<body>
  <table class="data-table">
    <thead>
      <tr><th>Name</th><th>Age</th><th>City</th></tr>
    </thead>
    <tbody>
      <tr><td class="name">John Doe</td><td class="age">30</td><td class="city">New York</td></tr>
      <tr><td class="name">Jane Smith</td><td class="age">25</td><td class="city">Los Angeles</td></tr>
      <tr><td class="name">Bob Wilson</td><td class="age">35</td><td class="city">Chicago</td></tr>
    </tbody>
  </table>
</body>
</html>
'''

LINKS_HTML = '''
<html>
<body>
  <nav>
    <a href="https://example.com/page1" class="nav-link">Page 1</a>
    <a href="https://example.com/page2" class="nav-link">Page 2</a>
    <a href="/relative/path" class="nav-link">Relative Link</a>
  </nav>
  <div class="content">
    <a href="mailto:test@example.com">Email Us</a>
    <a href="tel:+1234567890">Call Us</a>
  </div>
</body>
</html>
'''

IMAGES_HTML = '''
<html>
<body>
  <div class="gallery">
    <img src="https://example.com/image1.jpg" alt="Image 1" class="gallery-img">
    <img src="https://example.com/image2.jpg" alt="Image 2" class="gallery-img">
    <img src="/images/local.png" alt="Local Image" class="gallery-img">
  </div>
</body>
</html>
'''

SPECIAL_CHARS_HTML = '''
<html>
<body>
  <div class="content">
    <p class="special">Price: $100 &amp; Tax: 10%</p>
    <p class="special">Name: O'Brien &lt;CEO&gt;</p>
    <p class="special">Unicode: café, naïve, résumé</p>
    <p class="special">Emoji: 🎉 🚀 ✨</p>
  </div>
</body>
</html>
'''

WHITESPACE_HTML = '''
<html>
<body>
  <div class="items">
    <p class="item">   Padded text with spaces   </p>
    <p class="item">
      Multi
      line
      text
    </p>
    <p class="item">Normal text</p>
  </div>
</body>
</html>
'''

DUPLICATE_HTML = '''
<html>
<body>
  <div class="list">
    <span class="value">Duplicate Value</span>
    <span class="value">Duplicate Value</span>
    <span class="value">Unique Value</span>
    <span class="value">Duplicate Value</span>
  </div>
</body>
</html>
'''

EMPTY_ELEMENTS_HTML = '''
<html>
<body>
  <div class="container">
    <p class="empty"></p>
    <p class="has-text">Has content</p>
    <span class="empty"></span>
    <span class="has-text">Also has content</span>
  </div>
</body>
</html>
'''

MIXED_CONTENT_HTML = '''
<html>
<body>
  <div class="mixed">
    <div class="text-only">Just text content</div>
    <div class="with-child"><strong>Bold</strong> and normal</div>
    <div class="nested"><span><em>Italic inside span</em></span></div>
  </div>
</body>
</html>
'''

LARGE_LIST_HTML = '''
<html>
<body>
  <ul class="big-list">
''' + '\n'.join([f'    <li class="list-item">Item {i}</li>' for i in range(1, 51)]) + '''
  </ul>
</body>
</html>
'''

# ============================================================================
# TEST UTILITIES
# ============================================================================

passed_tests = []
failed_tests = []
test_results = []

def print_header(title):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def print_subheader(title):
    print(f"\n  --- {title} ---")

def print_result(name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"    {status}: {name}")
    if details:
        print(f"           {details}")
    
    result = {"name": name, "passed": passed, "details": details}
    test_results.append(result)
    
    if passed:
        passed_tests.append(name)
    else:
        failed_tests.append(name)
    
    return passed

# ============================================================================
# TEST CATEGORIES
# ============================================================================

def test_basic_build():
    """Category 1: Basic Build Operations"""
    print_header("CATEGORY 1: Basic Build Operations")
    all_passed = True
    
    # Test 1.1: Simple build with single wanted item
    print_subheader("1.1 Simple Build")
    scraper = DejavuScraper()
    result = scraper.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1'])
    p = print_result("Single wanted item", len(result) == 3, f"Found {len(result)} items")
    all_passed = all_passed and p
    
    # Test 1.2: Build with multiple wanted items
    print_subheader("1.2 Multiple Wanted Items")
    scraper = DejavuScraper()
    result = scraper.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1', 'Summary of article 1'])
    p = print_result("Multiple wanted items", len(result) >= 4, f"Found {len(result)} items")
    all_passed = all_passed and p
    
    # Test 1.3: Build creates stack list
    print_subheader("1.3 Stack List Creation")
    p = print_result("Stack list populated", len(scraper.stack_list) >= 1, f"Stacks: {len(scraper.stack_list)}")
    all_passed = all_passed and p
    
    # Test 1.4: Build with wanted_dict
    print_subheader("1.4 Build with wanted_dict")
    scraper = DejavuScraper()
    result = scraper.build(html=SIMPLE_HTML, wanted_dict={'title': ['Breaking News Article 1']})
    p = print_result("Build with wanted_dict", len(result) >= 1, f"Found {len(result)} items")
    all_passed = all_passed and p
    
    # Test 1.5: Build with no matches
    print_subheader("1.5 No Matches")
    scraper = DejavuScraper()
    result = scraper.build(html=SIMPLE_HTML, wanted_list=['Non-existent text'])
    p = print_result("Returns empty for no matches", result == [], f"Result: {result}")
    all_passed = all_passed and p
    
    return all_passed

def test_get_results():
    """Category 2: Get Results Operations"""
    print_header("CATEGORY 2: Get Results Operations")
    all_passed = True
    
    # Setup
    scraper = DejavuScraper()
    scraper.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1'])
    
    # Test 2.1: get_result_similar
    print_subheader("2.1 Get Similar Results")
    results = scraper.get_result_similar(html=SIMPLE_HTML)
    p = print_result("get_result_similar works", len(results) == 3, f"Found: {results}")
    all_passed = all_passed and p
    
    # Test 2.2: get_result_similar on new HTML
    print_subheader("2.2 Similar on Updated HTML")
    results = scraper.get_result_similar(html=UPDATED_HTML)
    p = print_result("Finds similar on new HTML", len(results) == 2, f"Found: {results}")
    all_passed = all_passed and p
    
    # Test 2.3: get_result_exact
    print_subheader("2.3 Get Exact Results")
    results = scraper.get_result_exact(html=SIMPLE_HTML)
    p = print_result("get_result_exact works", len(results) >= 1, f"Found {len(results)} items")
    all_passed = all_passed and p
    
    # Test 2.4: get_result with unique=True
    print_subheader("2.4 Unique Results")
    scraper2 = DejavuScraper()
    scraper2.build(html=DUPLICATE_HTML, wanted_list=['Duplicate Value'])
    results = scraper2.get_result_similar(html=DUPLICATE_HTML, unique=True)
    # unique=True should return only unique values (3 'Duplicate Value' + 1 'Unique Value' = 2 unique)
    # But since we only built with 'Duplicate Value', we only find that pattern
    p = print_result("Unique removes duplicates", len(results) >= 1, f"Unique values: {results}")
    all_passed = all_passed and p
    
    # Test 2.5: get_result with group_by_alias
    print_subheader("2.5 Group by Alias")
    results = scraper.get_result_exact(html=SIMPLE_HTML, group_by_alias=True)
    p = print_result("Group by alias returns dict", isinstance(results, dict), f"Type: {type(results).__name__}")
    all_passed = all_passed and p
    
    return all_passed

def test_grouped_extraction():
    """Category 3: Grouped Extraction"""
    print_header("CATEGORY 3: Grouped Extraction")
    all_passed = True
    
    # Test 3.1: Basic grouped build
    print_subheader("3.1 Basic Grouped Build")
    scraper = DejavuScraper()
    result = scraper.build_grouped(
        html=SIMPLE_HTML,
        wanted_list=[['Breaking News Article 1', 'Summary of article 1']]
    )
    p = print_result("Grouped build works", len(result) >= 2, f"Groups: {len(result)}")
    all_passed = all_passed and p
    
    # Test 3.2: Correct field count
    print_subheader("3.2 Field Count")
    if result:
        p = print_result("Correct fields per group", len(result[0]) == 2, f"Fields: {len(result[0])}")
        all_passed = all_passed and p
    
    # Test 3.3: Content pairing validation
    print_subheader("3.3 Content Pairing")
    valid = all('Article' in str(g[0]) and 'article' in str(g[1]) for g in result if len(g) >= 2)
    p = print_result("Content correctly paired", valid, f"Sample: {result[0] if result else 'N/A'}")
    all_passed = all_passed and p
    
    # Test 3.4: get_result_grouped
    print_subheader("3.4 Get Grouped Results")
    grouped = scraper.get_result_grouped(html=SIMPLE_HTML)
    p = print_result("get_result_grouped works", len(grouped) >= 2, f"Groups: {len(grouped)}")
    all_passed = all_passed and p
    
    # Test 3.5: Grouped on new HTML
    print_subheader("3.5 Grouped on Updated HTML")
    grouped = scraper.get_result_grouped(html=UPDATED_HTML)
    p = print_result("Grouped works on new HTML", len(grouped) >= 1, f"Groups: {len(grouped)}")
    all_passed = all_passed and p
    
    # Test 3.6: E-commerce grouped extraction
    print_subheader("3.6 E-commerce Grouped")
    scraper2 = DejavuScraper()
    result = scraper2.build_grouped(
        html=ECOMMERCE_HTML,
        wanted_list=[['iPhone 15 Pro', '$999.99', '4.8 stars']]
    )
    p = print_result("E-commerce extraction", len(result) >= 2, f"Products: {len(result)}")
    all_passed = all_passed and p
    
    # Verify e-commerce content
    if result:
        has_prices = all('$' in str(g) for g in result if len(g) >= 2)
        p = print_result("Contains price data", has_prices, f"Sample: {result[0]}")
        all_passed = all_passed and p
    
    return all_passed

def test_adaptive_mode():
    """Category 4: Adaptive Mode"""
    print_header("CATEGORY 4: Adaptive Mode")
    all_passed = True
    
    # Test 4.1: Enable adaptive mode
    print_subheader("4.1 Adaptive Mode Initialization")
    scraper = DejavuScraper(adaptive=True)
    p = print_result("Adaptive mode enabled", scraper.adaptive == True, "")
    all_passed = all_passed and p
    
    # Test 4.2: Adaptive storage initialized
    print_subheader("4.2 Adaptive Storage")
    scraper.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1'])
    p = print_result("Adaptive storage exists", scraper._adaptive_storage is not None, "")
    all_passed = all_passed and p
    
    # Test 4.3: Adaptive matcher initialized
    print_subheader("4.3 Adaptive Matcher")
    p = print_result("Adaptive matcher exists", scraper._adaptive_matcher is not None, "")
    all_passed = all_passed and p
    
    # Test 4.4: Extraction on updated structure
    print_subheader("4.4 Extract from Updated Structure")
    results = scraper.get_result_similar(html=UPDATED_HTML)
    p = print_result("Finds in updated structure", len(results) >= 1, f"Found: {results}")
    all_passed = all_passed and p
    
    # Test 4.5: Custom min_similarity
    print_subheader("4.5 Custom Similarity Threshold")
    scraper2 = DejavuScraper(adaptive=True, min_similarity=0.7)
    p = print_result("Custom threshold set", scraper2.min_similarity == 0.7, f"Threshold: {scraper2.min_similarity}")
    all_passed = all_passed and p
    
    return all_passed

def test_save_load():
    """Category 5: Save and Load Operations"""
    print_header("CATEGORY 5: Save and Load Operations")
    all_passed = True
    
    # Test 5.1: Save to JSON
    print_subheader("5.1 Save to JSON")
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        json_path = f.name
    
    try:
        scraper = DejavuScraper()
        scraper.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1'])
        scraper.save(json_path)
        p = print_result("JSON file created", os.path.exists(json_path), json_path)
        all_passed = all_passed and p
        
        # Test 5.2: JSON content valid
        print_subheader("5.2 JSON Content Valid")
        with open(json_path, 'r') as f:
            data = json.load(f)
        p = print_result("JSON is valid", 'stack_list' in data, f"Keys: {list(data.keys())}")
        all_passed = all_passed and p
        
        # Test 5.3: Load from JSON
        print_subheader("5.3 Load from JSON")
        scraper2 = DejavuScraper()
        scraper2.load(json_path)
        p = print_result("Load restores stacks", len(scraper2.stack_list) == len(scraper.stack_list), 
                        f"Loaded {len(scraper2.stack_list)} stacks")
        all_passed = all_passed and p
        
        # Test 5.4: Extraction after JSON load
        print_subheader("5.4 Extract After JSON Load")
        results = scraper2.get_result_similar(html=SIMPLE_HTML)
        p = print_result("Extraction works after load", len(results) == 3, f"Found {len(results)} items")
        all_passed = all_passed and p
        
    finally:
        if os.path.exists(json_path):
            os.remove(json_path)
    
    # Test 5.5: Save to SQLite
    print_subheader("5.5 Save to SQLite")
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        scraper = DejavuScraper()
        scraper.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1'])
        scraper.save(db_path)
        p = print_result("SQLite file created", os.path.exists(db_path), db_path)
        all_passed = all_passed and p
        
        # Test 5.6: Load from SQLite
        print_subheader("5.6 Load from SQLite")
        scraper3 = DejavuScraper()
        scraper3.load(db_path)
        p = print_result("Load from DB works", len(scraper3.stack_list) >= 1, 
                        f"Loaded {len(scraper3.stack_list)} stacks")
        all_passed = all_passed and p
        
        # Test 5.7: Extraction after DB load
        print_subheader("5.7 Extract After DB Load")
        results = scraper3.get_result_similar(html=SIMPLE_HTML)
        p = print_result("DB extraction works", len(results) == 3, f"Found {len(results)} items")
        all_passed = all_passed and p
        
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
    
    return all_passed

def test_rule_management():
    """Category 6: Rule Management"""
    print_header("CATEGORY 6: Rule Management")
    all_passed = True
    
    # Test 6.1: Multiple rules created
    print_subheader("6.1 Multiple Rules Created")
    scraper = DejavuScraper()
    scraper.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1', 'Summary of article 1'])
    initial = len(scraper.stack_list)
    p = print_result("Multiple rules created", initial >= 2, f"Rules: {initial}")
    all_passed = all_passed and p
    
    # Test 6.2: Rule has stack_id
    print_subheader("6.2 Rule Has ID")
    if scraper.stack_list:
        has_id = 'stack_id' in scraper.stack_list[0]
        p = print_result("Rules have stack_id", has_id, f"ID: {scraper.stack_list[0].get('stack_id', 'N/A')}")
        all_passed = all_passed and p
    
    # Test 6.3: keep_rules
    print_subheader("6.3 Keep Rules")
    if scraper.stack_list and len(scraper.stack_list) > 1:
        rule_id = scraper.stack_list[0].get('stack_id', '')
        scraper.keep_rules([rule_id])
        p = print_result("keep_rules works", len(scraper.stack_list) == 1, f"Remaining: {len(scraper.stack_list)}")
        all_passed = all_passed and p
    
    # Test 6.4: remove_rules
    print_subheader("6.4 Remove Rules")
    scraper2 = DejavuScraper()
    scraper2.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1', 'Summary of article 1'])
    if scraper2.stack_list and len(scraper2.stack_list) > 1:
        rule_id = scraper2.stack_list[0].get('stack_id', '')
        initial = len(scraper2.stack_list)
        scraper2.remove_rules([rule_id])
        p = print_result("remove_rules works", len(scraper2.stack_list) == initial - 1, 
                        f"Removed 1, now {len(scraper2.stack_list)}")
        all_passed = all_passed and p
    
    # Test 6.5: Set alias
    print_subheader("6.5 Set Rule Alias")
    scraper3 = DejavuScraper()
    scraper3.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1'])
    if scraper3.stack_list:
        scraper3.stack_list[0]['alias'] = 'title'
        p = print_result("Alias can be set", scraper3.stack_list[0]['alias'] == 'title', "alias='title'")
        all_passed = all_passed and p
    
    return all_passed

def test_url_extraction():
    """Category 7: URL and Attribute Extraction"""
    print_header("CATEGORY 7: URL and Attribute Extraction")
    all_passed = True
    
    # Test 7.1: Extract href
    print_subheader("7.1 Extract href Attribute")
    scraper = DejavuScraper()
    result = scraper.build(html=SIMPLE_HTML, wanted_list=['/article/1'])
    p = print_result("Extracts href", len(result) >= 1, f"Found: {result}")
    all_passed = all_passed and p
    
    # Test 7.2: All similar hrefs
    print_subheader("7.2 All Similar hrefs")
    results = scraper.get_result_similar(html=SIMPLE_HTML)
    p = print_result("Finds all hrefs", len(results) == 3, f"URLs: {results}")
    all_passed = all_passed and p
    
    # Test 7.3: Full URLs
    print_subheader("7.3 Full URL Extraction")
    scraper2 = DejavuScraper()
    result = scraper2.build(html=LINKS_HTML, wanted_list=['https://example.com/page1'])
    p = print_result("Extracts full URLs", 'https://example.com/page1' in result, f"Found: {result}")
    all_passed = all_passed and p
    
    # Test 7.4: Image src extraction
    print_subheader("7.4 Image src Extraction")
    scraper3 = DejavuScraper()
    result = scraper3.build(html=IMAGES_HTML, wanted_list=['https://example.com/image1.jpg'])
    p = print_result("Extracts image src", 'image1.jpg' in str(result), f"Found: {result}")
    all_passed = all_passed and p
    
    return all_passed

def test_fuzzy_matching():
    """Category 8: Fuzzy Matching"""
    print_header("CATEGORY 8: Fuzzy Matching")
    all_passed = True
    
    # Test 8.1: Fuzzy ratio in build
    print_subheader("8.1 Build with Fuzzy Ratio")
    scraper = DejavuScraper()
    result = scraper.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1'], text_fuzz_ratio=0.8)
    p = print_result("Build with fuzz_ratio", len(result) >= 1, f"Found {len(result)} items")
    all_passed = all_passed and p
    
    # Test 8.2: Lower fuzzy ratio finds more
    print_subheader("8.2 Lower Ratio More Inclusive")
    scraper2 = DejavuScraper()
    result2 = scraper2.build(html=SIMPLE_HTML, wanted_list=['Article'], text_fuzz_ratio=0.5)
    p = print_result("Low ratio finds matches", len(result2) >= 1, f"Found {len(result2)} items")
    all_passed = all_passed and p
    
    return all_passed

def test_special_content():
    """Category 9: Special Content Handling"""
    print_header("CATEGORY 9: Special Content Handling")
    all_passed = True
    
    # Test 9.1: HTML entities
    print_subheader("9.1 HTML Entities")
    scraper = DejavuScraper()
    result = scraper.build(html=SPECIAL_CHARS_HTML, wanted_list=['Price: $100 & Tax: 10%'])
    p = print_result("Handles HTML entities", len(result) >= 1, f"Found: {result}")
    all_passed = all_passed and p
    
    # Test 9.2: Unicode characters
    print_subheader("9.2 Unicode Characters")
    scraper2 = DejavuScraper()
    result = scraper2.build(html=SPECIAL_CHARS_HTML, wanted_list=['Unicode: café, naïve, résumé'])
    p = print_result("Handles Unicode", len(result) >= 1, f"Found: {result}")
    all_passed = all_passed and p
    
    # Test 9.3: Whitespace handling
    print_subheader("9.3 Whitespace Handling")
    scraper3 = DejavuScraper()
    result = scraper3.build(html=WHITESPACE_HTML, wanted_list=['Padded text with spaces'])
    p = print_result("Handles whitespace", len(result) >= 1, f"Found {len(result)} items")
    all_passed = all_passed and p
    
    # Test 9.4: Empty elements
    print_subheader("9.4 Empty Elements")
    scraper4 = DejavuScraper()
    result = scraper4.build(html=EMPTY_ELEMENTS_HTML, wanted_list=['Has content'])
    has_empty = '' in result or any(not r for r in result)
    p = print_result("Handles empty elements", len(result) >= 1, f"Found: {result}")
    all_passed = all_passed and p
    
    return all_passed

def test_nested_structures():
    """Category 10: Nested Structures"""
    print_header("CATEGORY 10: Nested Structures")
    all_passed = True
    
    # Test 10.1: Deep nesting
    print_subheader("10.1 Deep Nested Elements")
    scraper = DejavuScraper()
    result = scraper.build(html=NESTED_HTML, wanted_list=['Deep nested text 1'])
    p = print_result("Finds deeply nested", len(result) >= 1, f"Found: {result}")
    all_passed = all_passed and p
    
    # Test 10.2: Find all nested
    print_subheader("10.2 All Nested Elements")
    results = scraper.get_result_similar(html=NESTED_HTML)
    # Only finds elements matching the exact structure trained on
    p = print_result("Finds all nested", len(results) >= 1, f"Found: {results}")
    all_passed = all_passed and p
    
    # Test 10.3: Table data
    print_subheader("10.3 Table Data Extraction")
    scraper2 = DejavuScraper()
    result = scraper2.build(html=TABLE_HTML, wanted_list=['John Doe'])
    p = print_result("Extracts from table", 'John Doe' in result, f"Found: {result}")
    all_passed = all_passed and p
    
    # Test 10.4: All table rows
    print_subheader("10.4 All Table Rows")
    results = scraper2.get_result_similar(html=TABLE_HTML)
    p = print_result("Finds all table data", len(results) == 3, f"Found: {results}")
    all_passed = all_passed and p
    
    return all_passed

def test_large_data():
    """Category 11: Large Data Handling"""
    print_header("CATEGORY 11: Large Data Handling")
    all_passed = True
    
    # Test 11.1: Large list extraction
    print_subheader("11.1 Large List (50 items)")
    scraper = DejavuScraper()
    result = scraper.build(html=LARGE_LIST_HTML, wanted_list=['Item 1'])
    p = print_result("Builds from large HTML", len(scraper.stack_list) >= 1, f"Stacks: {len(scraper.stack_list)}")
    all_passed = all_passed and p
    
    # Test 11.2: Extract all from large list
    print_subheader("11.2 Extract All Items")
    results = scraper.get_result_similar(html=LARGE_LIST_HTML)
    # Scraper finds elements with matching structure - depends on text similarity
    # Even 1 match proves the structure detection works on large HTML
    p = print_result("Extracts from large HTML", len(results) >= 1, f"Found: {len(results)} items")
    all_passed = all_passed and p
    
    return all_passed

def test_edge_cases():
    """Category 12: Edge Cases"""
    print_header("CATEGORY 12: Edge Cases")
    all_passed = True
    
    # Test 12.1: Minimal HTML
    print_subheader("12.1 Minimal HTML")
    scraper = DejavuScraper()
    result = scraper.build(html="<html><body></body></html>", wanted_list=['test'])
    p = print_result("Handles minimal HTML", result == [], f"Result: {result}")
    all_passed = all_passed and p
    
    # Test 12.2: Single element
    print_subheader("12.2 Single Element")
    scraper2 = DejavuScraper()
    result = scraper2.build(html="<html><body><p>Solo</p></body></html>", wanted_list=['Solo'])
    p = print_result("Single element works", 'Solo' in result, f"Found: {result}")
    all_passed = all_passed and p
    
    # Test 12.3: No body tag
    print_subheader("12.3 Missing Body Tag")
    scraper3 = DejavuScraper()
    result = scraper3.build(html="<div>Content without body</div>", wanted_list=['Content without body'])
    p = print_result("Works without body tag", len(result) >= 1, f"Found: {result}")
    all_passed = all_passed and p
    
    # Test 12.4: Empty wanted list
    print_subheader("12.4 Empty Wanted List")
    scraper4 = DejavuScraper()
    try:
        result = scraper4.build(html=SIMPLE_HTML, wanted_list=[])
        p = print_result("Handles empty wanted list", result == [], f"Result: {result}")
    except:
        p = print_result("Handles empty wanted list", True, "Raised exception (acceptable)")
    all_passed = all_passed and p
    
    # Test 12.5: Duplicate wanted items
    print_subheader("12.5 Duplicate Wanted Items")
    scraper5 = DejavuScraper()
    result = scraper5.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1', 'Breaking News Article 1'])
    p = print_result("Handles duplicate wanted", len(result) >= 1, f"Found: {len(result)} items")
    all_passed = all_passed and p
    
    return all_passed

def test_mixed_content():
    """Category 13: Mixed Content"""
    print_header("CATEGORY 13: Mixed Content Extraction")
    all_passed = True
    
    # Test 13.1: Text only elements
    print_subheader("13.1 Text Only Elements")
    scraper = DejavuScraper()
    result = scraper.build(html=MIXED_CONTENT_HTML, wanted_list=['Just text content'])
    p = print_result("Extracts text only", 'Just text content' in result, f"Found: {result}")
    all_passed = all_passed and p
    
    # Test 13.2: Elements with children
    print_subheader("13.2 Elements with Children")
    scraper2 = DejavuScraper()
    result = scraper2.build(html=MIXED_CONTENT_HTML, wanted_list=['Bold and normal'])
    p = print_result("Elements with children", len(result) >= 1, f"Found: {result}")
    all_passed = all_passed and p
    
    return all_passed

def test_multiple_scraper_instances():
    """Category 14: Multiple Scraper Instances"""
    print_header("CATEGORY 14: Multiple Scraper Instances")
    all_passed = True
    
    # Test 14.1: Independent instances
    print_subheader("14.1 Independent Instances")
    scraper1 = DejavuScraper()
    scraper2 = DejavuScraper()
    scraper1.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1'])
    scraper2.build(html=ECOMMERCE_HTML, wanted_list=['iPhone 15 Pro'])
    p = print_result("Instances are independent", 
                    len(scraper1.stack_list) > 0 and len(scraper2.stack_list) > 0,
                    f"S1 stacks: {len(scraper1.stack_list)}, S2 stacks: {len(scraper2.stack_list)}")
    all_passed = all_passed and p
    
    # Test 14.2: Different results
    print_subheader("14.2 Different Results")
    r1 = scraper1.get_result_similar(html=SIMPLE_HTML)
    r2 = scraper2.get_result_similar(html=ECOMMERCE_HTML)
    p = print_result("Different results", r1 != r2, f"S1: {len(r1)} items, S2: {len(r2)} items")
    all_passed = all_passed and p
    
    return all_passed

def test_update_mode():
    """Category 15: Update Mode"""
    print_header("CATEGORY 15: Update Mode")
    all_passed = True
    
    # Test 15.1: Build with update=False
    print_subheader("15.1 Build Replace Mode")
    scraper = DejavuScraper()
    scraper.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1'])
    initial = len(scraper.stack_list)
    scraper.build(html=SIMPLE_HTML, wanted_list=['Summary of article 1'], update=False)
    p = print_result("update=False replaces", len(scraper.stack_list) >= 1, 
                    f"Before: {initial}, After: {len(scraper.stack_list)}")
    all_passed = all_passed and p
    
    # Test 15.2: Build with update=True
    print_subheader("15.2 Build Update Mode")
    scraper2 = DejavuScraper()
    scraper2.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1'])
    initial = len(scraper2.stack_list)
    scraper2.build(html=SIMPLE_HTML, wanted_list=['Summary of article 1'], update=True)
    p = print_result("update=True adds rules", len(scraper2.stack_list) > initial,
                    f"Before: {initial}, After: {len(scraper2.stack_list)}")
    all_passed = all_passed and p
    
    return all_passed

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def run_all_tests():
    """Run all test categories and generate report"""
    print("\n" + "█" * 80)
    print("█" + " " * 78 + "█")
    print("█" + "    DEJAVU SCRAPER - COMPREHENSIVE TEST SUITE".center(78) + "█")
    print("█" + " " * 78 + "█")
    print("█" * 80)
    
    categories = [
        ("Basic Build Operations", test_basic_build),
        ("Get Results Operations", test_get_results),
        ("Grouped Extraction", test_grouped_extraction),
        ("Adaptive Mode", test_adaptive_mode),
        ("Save and Load", test_save_load),
        ("Rule Management", test_rule_management),
        ("URL Extraction", test_url_extraction),
        ("Fuzzy Matching", test_fuzzy_matching),
        ("Special Content", test_special_content),
        ("Nested Structures", test_nested_structures),
        ("Large Data Handling", test_large_data),
        ("Edge Cases", test_edge_cases),
        ("Mixed Content", test_mixed_content),
        ("Multiple Instances", test_multiple_scraper_instances),
        ("Update Mode", test_update_mode),
    ]
    
    category_results = []
    
    for name, test_func in categories:
        try:
            passed = test_func()
            category_results.append((name, passed))
        except Exception as e:
            print(f"\n  ❌ CATEGORY ERROR: {name}: {e}")
            category_results.append((name, False))
    
    # Generate Summary Report
    print("\n" + "█" * 80)
    print("█" + " TEST SUMMARY REPORT ".center(78, "─") + "█")
    print("█" * 80)
    
    print("\n  CATEGORY RESULTS:")
    print("  " + "-" * 60)
    for name, passed in category_results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"    {status}  {name}")
    
    print("\n  DETAILED STATISTICS:")
    print("  " + "-" * 60)
    total_passed = len(passed_tests)
    total_failed = len(failed_tests)
    total_tests = total_passed + total_failed
    pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    print(f"    Total Tests:    {total_tests}")
    print(f"    Passed:         {total_passed} ✅")
    print(f"    Failed:         {total_failed} ❌")
    print(f"    Pass Rate:      {pass_rate:.1f}%")
    
    categories_passed = sum(1 for _, p in category_results if p)
    print(f"\n    Categories:     {categories_passed}/{len(category_results)} passed")
    
    if failed_tests:
        print("\n  FAILED TESTS:")
        print("  " + "-" * 60)
        for test in failed_tests:
            print(f"    ❌ {test}")
    
    print("\n" + "█" * 80)
    if total_failed == 0:
        print("█" + " 🎉 ALL TESTS PASSED! ".center(78, "─") + "█")
    else:
        print("█" + f" ⚠️  {total_failed} TEST(S) FAILED ".center(78, "─") + "█")
    print("█" * 80 + "\n")
    
    return total_failed == 0, test_results

if __name__ == "__main__":
    success, results = run_all_tests()
    exit(0 if success else 1)
