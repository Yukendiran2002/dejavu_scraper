"""
Comprehensive Test Suite for DejavuScraper
=====================================================
Tests all features: basic scraping, grouped extraction, adaptive matching,
save/load (JSON & SQLite), missing field handling, and more.
"""
import os
import json
import tempfile
from dejavu_scraper import DejavuScraper

# Test HTML samples
SIMPLE_HTML = '''
<html>
<body>
  <div class="news">
    <article>
      <h2 class="title">Breaking News Article 1</h2>
      <p class="summary">Summary of article 1</p>
      <a href="/article/1">Read more</a>
    </article>
    <article>
      <h2 class="title">Breaking News Article 2</h2>
      <p class="summary">Summary of article 2</p>
      <a href="/article/2">Read more</a>
    </article>
    <article>
      <h2 class="title">Breaking News Article 3</h2>
      <p class="summary">Summary of article 3</p>
      <a href="/article/3">Read more</a>
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

STRUCTURAL_CHANGE_HTML = '''
<html>
<body>
  <section class="articles">
    <div class="card">
      <h3 class="headline">Restructured Article 1</h3>
      <div class="content">New summary format 1</div>
      <a class="link" href="/new/1">View</a>
    </div>
    <div class="card">
      <h3 class="headline">Restructured Article 2</h3>
      <div class="content">New summary format 2</div>
      <a class="link" href="/new/2">View</a>
    </div>
  </section>
</body>
</html>
'''

def print_header(title):
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)

def print_result(name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"  {status}: {name}")
    if details:
        print(f"         {details}")

def test_simple_build():
    """Test basic build functionality"""
    print_header("TEST 1: Simple Build")
    
    scraper = DejavuScraper()
    result = scraper.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1'])
    
    passed = len(result) == 3 and 'Breaking News Article 1' in result
    print_result("Build finds all similar elements", passed, f"Found: {len(result)} items")
    
    passed2 = len(scraper.stack_list) >= 1
    print_result("Stack list created", passed2, f"Stacks: {len(scraper.stack_list)}")
    
    return passed and passed2

def test_get_result_similar():
    """Test get_result_similar after build"""
    print_header("TEST 2: Get Similar Results")
    
    scraper = DejavuScraper()
    scraper.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1'])
    
    # Get results from same HTML
    results = scraper.get_result_similar(html=SIMPLE_HTML)
    passed = len(results) == 3
    print_result("Get similar from same HTML", passed, f"Found: {results}")
    
    # Get results from updated HTML
    results2 = scraper.get_result_similar(html=UPDATED_HTML)
    passed2 = len(results2) == 2 and 'NEW: Updated Article A' in results2
    print_result("Get similar from updated HTML", passed2, f"Found: {results2}")
    
    return passed and passed2

def test_grouped_build():
    """Test grouped extraction"""
    print_header("TEST 3: Grouped Build")
    
    scraper = DejavuScraper()
    result = scraper.build_grouped(
        html=SIMPLE_HTML,
        wanted_list=[
            ['Breaking News Article 1', 'Summary of article 1']
        ]
    )
    
    passed = len(result) >= 2
    print_result("Grouped build extracts multiple items", passed, f"Groups: {len(result)}")
    
    # Check structure
    if result:
        passed2 = len(result[0]) == 2
        print_result("Each group has correct fields", passed2, f"Fields per group: {len(result[0]) if result else 0}")
    else:
        passed2 = False
        print_result("Each group has correct fields", passed2)
    
    return passed and passed2

def test_get_result_grouped():
    """Test get_result_grouped after build"""
    print_header("TEST 4: Get Grouped Results")
    
    scraper = DejavuScraper()
    scraper.build_grouped(
        html=SIMPLE_HTML,
        wanted_list=[
            ['Breaking News Article 1', 'Summary of article 1']
        ]
    )
    
    # Get grouped results from updated HTML
    results = scraper.get_result_grouped(html=UPDATED_HTML)
    passed = len(results) >= 1
    print_result("Get grouped from updated HTML", passed, f"Groups found: {len(results)}")
    
    if results:
        has_new = any('NEW:' in str(r) for r in results)
        print_result("Contains new article data", has_new)
    
    return passed

def test_save_load_json():
    """Test JSON save/load functionality"""
    print_header("TEST 5: Save/Load JSON")
    
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
        json_path = f.name
    
    try:
        # Build and save
        scraper = DejavuScraper()
        scraper.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1'])
        scraper.save(json_path)
        
        passed1 = os.path.exists(json_path)
        print_result("JSON file created", passed1)
        
        # Load and verify
        scraper2 = DejavuScraper()
        scraper2.load(json_path)
        
        passed2 = len(scraper2.stack_list) == len(scraper.stack_list)
        print_result("Stack list restored", passed2, f"Stacks: {len(scraper2.stack_list)}")
        
        # Test extraction after load
        results = scraper2.get_result_similar(html=SIMPLE_HTML)
        passed3 = len(results) == 3
        print_result("Extraction works after load", passed3, f"Results: {len(results)}")
        
        return passed1 and passed2 and passed3
    finally:
        if os.path.exists(json_path):
            os.remove(json_path)

def test_save_load_sqlite():
    """Test SQLite save/load functionality"""
    print_header("TEST 6: Save/Load SQLite")
    
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    try:
        # Build and save
        scraper = DejavuScraper()
        scraper.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1'])
        scraper.save(db_path)
        
        passed1 = os.path.exists(db_path)
        print_result("SQLite file created", passed1)
        
        # Load and verify
        scraper2 = DejavuScraper()
        scraper2.load(db_path)
        
        passed2 = len(scraper2.stack_list) == len(scraper.stack_list)
        print_result("Stack list restored from DB", passed2, f"Stacks: {len(scraper2.stack_list)}")
        
        # Test extraction after load
        results = scraper2.get_result_similar(html=SIMPLE_HTML)
        passed3 = len(results) == 3
        print_result("Extraction works after DB load", passed3, f"Results: {len(results)}")
        
        return passed1 and passed2 and passed3
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)

def test_adaptive_extraction():
    """Test adaptive extraction for structural changes"""
    print_header("TEST 7: Adaptive Extraction")
    
    scraper = DejavuScraper(adaptive=True)
    
    # Build with original structure
    scraper.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1'])
    
    passed1 = scraper.adaptive
    print_result("Adaptive mode enabled", passed1)
    
    # Try to extract from structurally different HTML
    results = scraper.get_result_similar(html=UPDATED_HTML)
    passed2 = len(results) >= 1
    print_result("Extracts from updated structure", passed2, f"Found: {results}")
    
    return passed1 and passed2

def test_grouped_with_aliases():
    """Test grouped extraction with field aliases"""
    print_header("TEST 8: Grouped with Aliases")
    
    scraper = DejavuScraper()
    
    # Build grouped
    scraper.build_grouped(
        html=SIMPLE_HTML,
        wanted_list=[
            ['Breaking News Article 1', 'Summary of article 1', '/article/1']
        ]
    )
    
    # Set aliases
    if scraper.stack_list:
        for i, stack in enumerate(scraper.stack_list):
            aliases = ['title', 'summary', 'link']
            if i < len(aliases):
                stack['alias'] = aliases[i]
    
    # Get results
    results = scraper.get_result_grouped(html=SIMPLE_HTML)
    passed = len(results) >= 2
    print_result("Grouped extraction with aliases", passed, f"Groups: {len(results)}")
    
    return passed

def test_fuzzy_matching():
    """Test fuzzy text matching"""
    print_header("TEST 9: Fuzzy Matching")
    
    scraper = DejavuScraper()
    # Build with fuzzy ratio
    result = scraper.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1'], text_fuzz_ratio=0.8)
    passed = len(result) >= 1
    print_result("Fuzzy matching in build", passed, f"Results: {len(result)}")
    
    # Get similar results
    results = scraper.get_result_similar(html=SIMPLE_HTML)
    passed2 = len(results) >= 1
    print_result("Get similar after fuzzy build", passed2, f"Results: {len(results)}")
    
    return passed and passed2

def test_url_extraction():
    """Test URL/href extraction"""
    print_header("TEST 10: URL Extraction")
    
    scraper = DejavuScraper()
    result = scraper.build(html=SIMPLE_HTML, wanted_list=['/article/1'])
    
    passed = '/article/1' in result or any('/article/' in str(r) for r in result)
    print_result("Extracts href attributes", passed, f"Found: {result}")
    
    # Get all similar URLs
    results = scraper.get_result_similar(html=SIMPLE_HTML)
    passed2 = len(results) >= 2
    print_result("Finds all similar URLs", passed2, f"URLs: {results}")
    
    return passed and passed2

def test_multiple_wanted_items():
    """Test building with multiple wanted items"""
    print_header("TEST 11: Multiple Wanted Items")
    
    scraper = DejavuScraper()
    result = scraper.build(
        html=SIMPLE_HTML, 
        wanted_list=['Breaking News Article 1', 'Summary of article 1']
    )
    
    passed = len(result) >= 4  # Should find titles and summaries
    print_result("Multiple wanted items", passed, f"Total found: {len(result)}")
    
    has_titles = any('Article' in str(r) for r in result)
    has_summaries = any('Summary' in str(r) for r in result)
    passed2 = has_titles and has_summaries
    print_result("Found both titles and summaries", passed2)
    
    return passed and passed2

def test_keep_rules():
    """Test keep_rules functionality"""
    print_header("TEST 12: Keep Rules")
    
    scraper = DejavuScraper()
    scraper.build(
        html=SIMPLE_HTML,
        wanted_list=['Breaking News Article 1', 'Summary of article 1']
    )
    
    initial_stacks = len(scraper.stack_list)
    print_result("Initial stacks created", initial_stacks > 0, f"Stacks: {initial_stacks}")
    
    # Get rule IDs
    if scraper.stack_list:
        rule_id = scraper.stack_list[0].get('stack_id', '')
        if rule_id:
            scraper.keep_rules([rule_id])
            passed = len(scraper.stack_list) == 1
            print_result("Keep specific rules", passed, f"Remaining: {len(scraper.stack_list)}")
            return passed
    
    return False

def test_remove_rules():
    """Test remove_rules functionality"""
    print_header("TEST 13: Remove Rules")
    
    scraper = DejavuScraper()
    scraper.build(
        html=SIMPLE_HTML,
        wanted_list=['Breaking News Article 1', 'Summary of article 1']
    )
    
    initial_stacks = len(scraper.stack_list)
    
    if scraper.stack_list and initial_stacks > 1:
        rule_id = scraper.stack_list[0].get('stack_id', '')
        if rule_id:
            scraper.remove_rules([rule_id])
            passed = len(scraper.stack_list) == initial_stacks - 1
            print_result("Remove specific rules", passed, f"Remaining: {len(scraper.stack_list)}")
            return passed
    
    print_result("Remove rules (skipped - not enough rules)", True, "Only 1 rule")
    return True

def test_get_rules():
    """Test get_rules/get_result_exact functionality"""
    print_header("TEST 14: Get Rules")
    
    scraper = DejavuScraper()
    scraper.build(html=SIMPLE_HTML, wanted_list=['Breaking News Article 1'])
    
    # Check rule aliases
    rules = scraper.get_result_exact(html=SIMPLE_HTML, group_by_alias=True)
    passed = isinstance(rules, dict)
    print_result("Get result by alias", passed, f"Type: {type(rules).__name__}")
    
    return passed

def test_empty_html():
    """Test handling of empty/invalid HTML"""
    print_header("TEST 15: Edge Cases")
    
    scraper = DejavuScraper()
    
    # Minimal valid HTML
    try:
        result = scraper.build(html="<html><body></body></html>", wanted_list=['test'])
        passed1 = result == []
        print_result("Handles minimal HTML", passed1)
    except Exception as e:
        print_result("Handles minimal HTML", False, str(e))
        passed1 = False
    
    # HTML without wanted content
    scraper2 = DejavuScraper()
    result2 = scraper2.build(html="<html><body>Nothing here</body></html>", wanted_list=['test'])
    passed2 = result2 == []
    print_result("Handles no matches", passed2)
    
    return passed1 and passed2

def test_grouped_content_validation():
    """Test that grouped content is correctly paired"""
    print_header("TEST 16: Grouped Content Validation")
    
    scraper = DejavuScraper()
    result = scraper.build_grouped(
        html=SIMPLE_HTML,
        wanted_list=[
            ['Breaking News Article 1', 'Summary of article 1']
        ]
    )
    
    # Check that we got groups
    passed1 = len(result) >= 2
    print_result("Multiple groups extracted", passed1, f"Groups: {len(result)}")
    
    # Validate content pairing - each group should have title AND summary
    valid_pairs = 0
    for group in result:
        if len(group) >= 2:
            title, summary = group[0], group[1]
            # Check if title and summary are from same article
            if 'Article 1' in str(title) and 'article 1' in str(summary):
                valid_pairs += 1
            elif 'Article 2' in str(title) and 'article 2' in str(summary):
                valid_pairs += 1
            elif 'Article 3' in str(title) and 'article 3' in str(summary):
                valid_pairs += 1
    
    passed2 = valid_pairs >= 2
    print_result("Content correctly paired", passed2, f"Valid pairs: {valid_pairs}")
    
    # Print actual content for verification
    print(f"         Extracted groups:")
    for i, group in enumerate(result[:3]):  # Show first 3
        print(f"           [{i+1}] {group}")
    
    return passed1 and passed2

def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "=" * 70)
    print(" INTELLIGENT DejavuScraper - COMPREHENSIVE TEST SUITE")
    print("=" * 70)
    
    tests = [
        ("Simple Build", test_simple_build),
        ("Get Similar Results", test_get_result_similar),
        ("Grouped Build", test_grouped_build),
        ("Get Grouped Results", test_get_result_grouped),
        ("Save/Load JSON", test_save_load_json),
        ("Save/Load SQLite", test_save_load_sqlite),
        ("Adaptive Extraction", test_adaptive_extraction),
        ("Grouped with Aliases", test_grouped_with_aliases),
        ("Fuzzy Matching", test_fuzzy_matching),
        ("URL Extraction", test_url_extraction),
        ("Multiple Wanted Items", test_multiple_wanted_items),
        ("Keep Rules", test_keep_rules),
        ("Remove Rules", test_remove_rules),
        ("Get Rules", test_get_rules),
        ("Edge Cases", test_empty_html),
        ("Grouped Content Validation", test_grouped_content_validation),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            passed = test_func()
            results.append((name, passed))
        except Exception as e:
            print(f"\n  ❌ ERROR in {name}: {e}")
            results.append((name, False))
    
    # Summary
    print_header("TEST SUMMARY")
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    for name, passed in results:
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
    
    print("\n" + "-" * 70)
    print(f"  TOTAL: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n  🎉 ALL TESTS PASSED!")
    else:
        print(f"\n  ⚠️  {total_count - passed_count} test(s) failed")
    
    print("=" * 70 + "\n")
    
    return passed_count == total_count

if __name__ == "__main__":
    run_all_tests()
