"""
Cross-Site Flexible Extraction Test
====================================
Two e-commerce pages with SAME content but DIFFERENT HTML tags/structure.
Tests that DejavuScraper.get_result_flexible() can learn the SHAPE of data
from Site A and extract matching content from Site B — no LLM needed.
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dejavu_scraper import DejavuScraper

# ============================================================================
# SITE A — Uses: article, h2, span.price, p.desc, a.buy-link, div.rating
# ============================================================================
SITE_A = """
<html>
<head><title>ShopZone - Electronics</title></head>
<body>
<div id="header"><h1>ShopZone</h1></div>
<main class="products-grid">

  <article class="product-card">
    <h2 class="title">Sony WH-1000XM5 Headphones</h2>
    <span class="price">$349.99</span>
    <p class="desc">Industry-leading noise cancellation with 30hr battery life</p>
    <a class="buy-link" href="/products/sony-wh1000xm5">View Details</a>
    <div class="rating">4.8/5 stars</div>
  </article>

  <article class="product-card">
    <h2 class="title">Apple MacBook Air M3</h2>
    <span class="price">$1,099.00</span>
    <p class="desc">Supercharged by M3 chip with 18hr battery and Liquid Retina display</p>
    <a class="buy-link" href="/products/macbook-air-m3">View Details</a>
    <div class="rating">4.9/5 stars</div>
  </article>

  <article class="product-card">
    <h2 class="title">Samsung Galaxy S25 Ultra</h2>
    <span class="price">$1,299.99</span>
    <p class="desc">AI-powered camera system with 200MP sensor and S Pen</p>
    <a class="buy-link" href="/products/galaxy-s25-ultra">View Details</a>
    <div class="rating">4.7/5 stars</div>
  </article>

  <article class="product-card">
    <h2 class="title">Nintendo Switch 2</h2>
    <span class="price">$449.99</span>
    <p class="desc">Next-gen portable gaming with 4K docked output</p>
    <a class="buy-link" href="/products/switch-2">View Details</a>
    <div class="rating">4.6/5 stars</div>
  </article>

  <article class="product-card">
    <h2 class="title">Bose QuietComfort Ultra</h2>
    <span class="price">$429.00</span>
    <p class="desc">Immersive spatial audio with world-class noise cancellation</p>
    <a class="buy-link" href="/products/bose-qc-ultra">View Details</a>
    <div class="rating">4.5/5 stars</div>
  </article>

</main>
</body>
</html>
"""

# ============================================================================
# SITE B — SAME 5 products, COMPLETELY DIFFERENT HTML structure
# Uses: li, h3, div.cost, div.summary, a, span.stars
# ============================================================================
SITE_B = """
<html>
<head><title>TechBuy - Best Electronics Deals</title></head>
<body>
<header><div class="logo">TechBuy</div></header>
<section id="listing">
<ul class="item-list">

  <li class="item-row">
    <div class="item-info">
      <h3 class="item-name">Sony WH-1000XM5 Headphones</h3>
      <div class="cost">$349.99</div>
    </div>
    <div class="summary">Industry-leading noise cancellation with 30hr battery life</div>
    <div class="actions"><a href="/buy/sony-xm5">Buy Now</a></div>
    <span class="stars">4.8/5 stars</span>
  </li>

  <li class="item-row">
    <div class="item-info">
      <h3 class="item-name">Apple MacBook Air M3</h3>
      <div class="cost">$1,099.00</div>
    </div>
    <div class="summary">Supercharged by M3 chip with 18hr battery and Liquid Retina display</div>
    <div class="actions"><a href="/buy/macbook-m3">Buy Now</a></div>
    <span class="stars">4.9/5 stars</span>
  </li>

  <li class="item-row">
    <div class="item-info">
      <h3 class="item-name">Samsung Galaxy S25 Ultra</h3>
      <div class="cost">$1,299.99</div>
    </div>
    <div class="summary">AI-powered camera system with 200MP sensor and S Pen</div>
    <div class="actions"><a href="/buy/galaxy-s25">Buy Now</a></div>
    <span class="stars">4.7/5 stars</span>
  </li>

  <li class="item-row">
    <div class="item-info">
      <h3 class="item-name">Nintendo Switch 2</h3>
      <div class="cost">$449.99</div>
    </div>
    <div class="summary">Next-gen portable gaming with 4K docked output</div>
    <div class="actions"><a href="/buy/switch-2">Buy Now</a></div>
    <span class="stars">4.6/5 stars</span>
  </li>

  <li class="item-row">
    <div class="item-info">
      <h3 class="item-name">Bose QuietComfort Ultra</h3>
      <div class="cost">$429.00</div>
    </div>
    <div class="summary">Immersive spatial audio with world-class noise cancellation</div>
    <div class="actions"><a href="/buy/bose-ultra">Buy Now</a></div>
    <span class="stars">4.5/5 stars</span>
  </li>

</ul>
</section>
</body>
</html>
"""

# ============================================================================
# SITE C — Press Release / News page (different domain entirely)
# Uses: div.article, h4.headline, span.date, p.excerpt
# ============================================================================
SITE_C = """
<html>
<head><title>TechWire - Press Releases</title></head>
<body>
<nav><a href="/">TechWire</a></nav>
<div class="feed">

  <div class="article">
    <h4 class="headline">Sony Announces Next-Gen Noise Cancellation Technology</h4>
    <span class="date">2026-02-01</span>
    <p class="excerpt">Sony unveils breakthrough ANC chip that delivers 40% better noise reduction while using less power</p>
  </div>

  <div class="article">
    <h4 class="headline">Apple M4 Chip Enters Mass Production for 2026 MacBooks</h4>
    <span class="date">2026-01-28</span>
    <p class="excerpt">TSMC ramps up 2nm production for Apple next-generation M4 processor family</p>
  </div>

  <div class="article">
    <h4 class="headline">Samsung Q1 2026 Earnings Beat Expectations on AI Chip Demand</h4>
    <span class="date">2026-01-25</span>
    <p class="excerpt">Samsung Electronics reports record quarterly revenue driven by AI accelerator and HBM memory sales</p>
  </div>

  <div class="article">
    <h4 class="headline">Nintendo Switch 2 Pre-Orders Crash Retail Websites Worldwide</h4>
    <span class="date">2026-01-20</span>
    <p class="excerpt">Pre-order demand for Nintendo upcoming console overwhelms online retailers across 15 countries</p>
  </div>

  <div class="article">
    <h4 class="headline">Bose Partners with Spatial Audio Startup for AR Glasses</h4>
    <span class="date">2026-01-15</span>
    <p class="excerpt">Bose announces strategic partnership to bring spatial audio to next-generation augmented reality wearables</p>
  </div>

</div>
</body>
</html>
"""

EXPECTED_NAMES = [
    "Sony WH-1000XM5 Headphones",
    "Apple MacBook Air M3",
    "Samsung Galaxy S25 Ultra",
    "Nintendo Switch 2",
    "Bose QuietComfort Ultra",
]

EXPECTED_PRICES = ["$349.99", "$1,099.00", "$1,299.99", "$449.99", "$429.00"]

passed = 0
failed = 0
total = 0


def test(name, condition, detail=""):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print(f"  \u2705 {name}")
    else:
        failed += 1
        print(f"  \u274c {name}")
    if detail:
        print(f"       {detail}")


# ======================================================================
print("=" * 70)
print(" TEST 1: Learn NAMES on Site A  ->  flexible extract from Site B")
print("=" * 70)

scraper = DejavuScraper()
result_a = scraper.build(html=SITE_A, wanted_list=["Sony WH-1000XM5 Headphones"])

test("build() finds all 5 names on Site A",
     len(result_a) == 5,
     f"Found {len(result_a)}: {result_a}")

# Old rule-based: should return 0 (tags differ)
old_result = scraper.get_result_similar(html=SITE_B)
test("get_result_similar on Site B returns 0 (tag-bound)",
     len(old_result) == 0,
     f"Found {len(old_result)}")

# NEW flexible: should return all 5 names!
flex_result = scraper.get_result_flexible(html=SITE_B)
test("get_result_flexible finds names on Site B",
     len(flex_result) == 5,
     f"Found {len(flex_result)}: {flex_result}")

names_matched = [n for n in EXPECTED_NAMES if n in flex_result]
test("All 5 product names matched cross-site",
     len(names_matched) == 5,
     f"Matched {len(names_matched)}/5: {names_matched}")


# ======================================================================
print()
print("=" * 70)
print(" TEST 2: Learn PRICES on Site A  ->  flexible extract from Site B")
print("=" * 70)

scraper2 = DejavuScraper()
prices_a = scraper2.build(html=SITE_A, wanted_list=["$349.99"])

test("build() finds all 5 prices on Site A",
     len(prices_a) == 5,
     f"Found {len(prices_a)}: {prices_a}")

flex_prices = scraper2.get_result_flexible(html=SITE_B)
test("get_result_flexible finds prices on Site B",
     len(flex_prices) == 5,
     f"Found {len(flex_prices)}: {flex_prices}")

prices_matched = [p for p in EXPECTED_PRICES if p in flex_prices]
test("All 5 prices matched cross-site",
     len(prices_matched) == 5,
     f"Matched {len(prices_matched)}/5: {prices_matched}")


# ======================================================================
print()
print("=" * 70)
print(" TEST 3: Learn NEWS HEADLINES on Site C  ->  same-site flexible")
print("=" * 70)

scraper3 = DejavuScraper()
headlines_c = scraper3.build(
    html=SITE_C,
    wanted_list=["Sony Announces Next-Gen Noise Cancellation Technology"],
)

test("build() finds all 5 headlines on Site C",
     len(headlines_c) == 5,
     f"Found {len(headlines_c)}: {headlines_c}")

flex_headlines = scraper3.get_result_flexible(html=SITE_C)
test("Flexible extract same-site still works",
     len(flex_headlines) == 5,
     f"Found {len(flex_headlines)}: {flex_headlines}")


# ======================================================================
print()
print("=" * 70)
print(" TEST 4: Save model with fingerprints, load, cross-site extract")
print("=" * 70)

scraper4 = DejavuScraper()
scraper4.build(html=SITE_A, wanted_list=["Sony WH-1000XM5 Headphones"])

tmp_json = os.path.join(tempfile.gettempdir(), "flex_test.json")
scraper4.save(tmp_json)
test("Saved model (JSON) with fingerprints", os.path.exists(tmp_json))

loaded = DejavuScraper()
loaded.load(tmp_json)
test("Loaded model has fingerprints",
     len(loaded._content_fingerprints) > 0,
     f"Fingerprints: {len(loaded._content_fingerprints)}")

loaded_flex = loaded.get_result_flexible(html=SITE_B)
test("Loaded model flexible-extracts from Site B",
     len(loaded_flex) == 5,
     f"Found {len(loaded_flex)}: {loaded_flex}")

os.remove(tmp_json)

# Also test SQLite save/load
tmp_db = os.path.join(tempfile.gettempdir(), "flex_test.db")
scraper4.save(tmp_db)
test("Saved model (SQLite) with fingerprints", os.path.exists(tmp_db))

loaded_db = DejavuScraper()
loaded_db.load(tmp_db)
test("DB-loaded model has fingerprints",
     len(loaded_db._content_fingerprints) > 0,
     f"Fingerprints: {len(loaded_db._content_fingerprints)}")

db_flex = loaded_db.get_result_flexible(html=SITE_B)
test("DB-loaded model flexible-extracts from Site B",
     len(db_flex) == 5,
     f"Found {len(db_flex)}: {db_flex}")

os.remove(tmp_db)


# ======================================================================
print()
print("=" * 70)
print(" TEST 5: SmartExtractor still works on both (structure-agnostic)")
print("=" * 70)

scraper5 = DejavuScraper()
data_a = scraper5.extract_data_types(html=SITE_A)
data_b = scraper5.extract_data_types(html=SITE_B)

test("SmartExtractor finds prices on Site A",
     'price' in data_a and len(data_a['price']) == 5,
     f"Prices: {data_a.get('price', [])}")

test("SmartExtractor finds prices on Site B",
     'price' in data_b and len(data_b['price']) == 5,
     f"Prices: {data_b.get('price', [])}")

data_c = scraper5.extract_data_types(html=SITE_C)
test("SmartExtractor finds dates on Site C",
     'date' in data_c and len(data_c['date']) == 5,
     f"Dates: {data_c.get('date', [])}")


# ======================================================================
print()
print("=" * 70)
print(" TEST 6: Existing tests still pass (no regression)")
print("=" * 70)

# Same-site rule-based extraction still works
scraper6 = DejavuScraper()
scraper6.build(html=SITE_A, wanted_list=["Sony WH-1000XM5 Headphones"])
same_site = scraper6.get_result_similar(html=SITE_A)
test("Same-site get_result_similar still works",
     len(same_site) == 5,
     f"Found {len(same_site)}: {same_site}")

# Grouped extraction still works
scraper7 = DejavuScraper()
grouped = scraper7.build_grouped(
    html=SITE_A,
    wanted_list=[
        ["Sony WH-1000XM5 Headphones", "$349.99"],
        ["Apple MacBook Air M3", "$1,099.00"],
    ],
)
test("Grouped extraction still works",
     grouped is not None and len(grouped) >= 2,
     f"Found {len(grouped) if grouped else 0} groups")


# ======================================================================
print()
print("=" * 70)
print(" TEST 7: Content fingerprint quality checks")
print("=" * 70)

scraper8 = DejavuScraper()
scraper8.build(html=SITE_A, wanted_list=["$349.99"])

fp_key = list(scraper8._content_fingerprints.keys())[0]
fp = scraper8._content_fingerprints[fp_key]

test("Fingerprint detects 'price' content type",
     fp['content_type'] == 'price',
     f"Type: {fp['content_type']}")

test("Fingerprint has_currency is True",
     fp['has_currency'] is True,
     f"has_currency: {fp['has_currency']}")

test("Fingerprint count matches (5 prices)",
     fp['count'] == 5,
     f"count: {fp['count']}")


scraper9 = DejavuScraper()
scraper9.build(html=SITE_A, wanted_list=["Sony WH-1000XM5 Headphones"])
fp_key2 = list(scraper9._content_fingerprints.keys())[0]
fp2 = scraper9._content_fingerprints[fp_key2]

test("Name fingerprint detects 'text' content type",
     fp2['content_type'] == 'text',
     f"Type: {fp2['content_type']}")

test("Name fingerprint has_currency is False",
     fp2['has_currency'] is False,
     f"has_currency: {fp2['has_currency']}")


# ============================================================================
# FINAL SUMMARY
# ============================================================================
print()
print("=" * 70)
print(" CROSS-SITE FLEXIBLE EXTRACTION TEST SUMMARY")
print("=" * 70)
print()
print(f"  Total tests:  {total}")
print(f"  Passed:       {passed} \u2705")
print(f"  Failed:       {failed} \u274c")
print(f"  Pass rate:    {passed / total * 100:.1f}%")
print()
print("  HOW IT WORKS:")
print("  " + "-" * 50)
print("  1. build() learns rules AND builds a content")
print("     fingerprint (text length, word count, type,")
print("     digit ratio, currency presence, etc.)")
print("  2. get_result_similar() uses tag+attr rules")
print("     -> same-site only (high precision)")
print("  3. get_result_flexible() uses content fingerprint")
print("     -> works across ANY HTML structure!")
print("  4. No LLM needed. No per-page training.")
print("     Learn once, extract everywhere.")
print()
print("=" * 70)
