"""
Example: Adaptive Extraction with Intelligent Scraper

This example demonstrates how to use the adaptive extraction feature to find
elements even when website structures change.

Inspired by Scrapling's adaptive feature - this allows your scrapers to survive
website updates by intelligently tracking and relocating elements.
"""

from autoscraper import AutoScraper


def example_basic_adaptive():
    """
    Basic example of adaptive extraction.
    
    1. First, we scrape a page and save element properties
    2. Later, even if the website structure changes, we can find the same elements
    """
    print("=" * 60)
    print("Example 1: Basic Adaptive Extraction")
    print("=" * 60)
    
    # Enable adaptive mode
    scraper = AutoScraper(adaptive=True)
    
    # Sample HTML (representing the original page structure)
    original_html = """
    <html>
    <body>
        <div class="container">
            <section class="products">
                <article class="product" id="p1">
                    <h3 class="title">Product 1</h3>
                    <p class="price">$19.99</p>
                    <p class="description">A great product</p>
                </article>
                <article class="product" id="p2">
                    <h3 class="title">Product 2</h3>
                    <p class="price">$29.99</p>
                    <p class="description">Another great product</p>
                </article>
            </section>
        </div>
    </body>
    </html>
    """
    
    # Parse the page
    soup = scraper._get_soup(html=original_html)
    
    # Find the first product title and save it for later
    product_title = soup.find('h3', class_='title')
    print(f"Original element found: {product_title.text}")
    
    # Save the element's properties with an identifier
    scraper.adaptive_save(product_title, 'product_title', url='https://example.com')
    print("✓ Element properties saved for adaptive matching\n")
    
    # Now simulate a website structure change
    changed_html = """
    <html>
    <body>
        <div class="new-container main-wrapper">
            <div class="product-list">
                <section class="products-grid">
                    <div class="product-card" data-id="p1">
                        <div class="product-info">
                            <h3 class="product-title">Product 1</h3>
                            <span class="product-price">$19.99</span>
                            <p class="product-desc">A great product</p>
                        </div>
                    </div>
                    <div class="product-card" data-id="p2">
                        <div class="product-info">
                            <h3 class="product-title">Product 2</h3>
                            <span class="product-price">$29.99</span>
                            <p class="product-desc">Another great product</p>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    </body>
    </html>
    """
    
    print("Website structure has changed!")
    print("- Container class changed from 'container' to 'new-container main-wrapper'")
    print("- Title class changed from 'title' to 'product-title'")
    print("- Nested structure completely different")
    print()
    
    # Try to find the element using adaptive matching
    element, score, all_matches = scraper.adaptive_find(
        'product_title',
        html=changed_html,
        url='https://example.com'
    )
    
    if element:
        print(f"✓ Element found with {score*100:.1f}% similarity!")
        print(f"  Text: {element.text}")
        print(f"  Tag: {element.name}")
        print(f"  Class: {element.get('class', [])}")
    else:
        print("✗ Element not found")
    
    print()


def example_find_similar():
    """
    Example of finding similar elements on a page.
    
    When you find one product, you can automatically find all similar products
    on the same page using similarity matching.
    """
    print("=" * 60)
    print("Example 2: Find Similar Elements")
    print("=" * 60)
    
    scraper = AutoScraper(adaptive=True)
    
    html = """
    <html>
    <body>
        <div class="product-grid">
            <div class="product-item" data-id="1">
                <h3>MacBook Pro</h3>
                <p class="price">$1,999</p>
                <span class="category">Laptops</span>
            </div>
            <div class="product-item" data-id="2">
                <h3>MacBook Air</h3>
                <p class="price">$999</p>
                <span class="category">Laptops</span>
            </div>
            <div class="product-item" data-id="3">
                <h3>iPad Pro</h3>
                <p class="price">$799</p>
                <span class="category">Tablets</span>
            </div>
            <div class="sidebar">
                <h3>Featured</h3>
                <p>Check out our deals!</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    soup = scraper._get_soup(html=html)
    
    # Find the first product
    first_product = soup.find('div', class_='product-item')
    product_name = first_product.find('h3')
    print(f"Reference element: {product_name.text}")
    print()
    
    # Find all similar products
    similar = scraper.find_similar_elements(
        first_product,
        soup=soup,
        similarity_threshold=0.5
    )
    
    print(f"Found {len(similar)} similar elements:")
    for element, score in similar:
        title = element.find('h3')
        if title:
            print(f"  - {title.text} (similarity: {score*100:.1f}%)")
    
    print()


def example_build_with_adaptive():
    """
    Example of using adaptive_build() to learn rules AND save element properties
    for future adaptive matching.
    """
    print("=" * 60)
    print("Example 3: Build with Adaptive Saving")
    print("=" * 60)
    
    scraper = AutoScraper(adaptive=True)
    
    html = """
    <html>
    <body>
        <div class="quotes-container">
            <div class="quote">
                <p class="text">"Be yourself; everyone else is already taken."</p>
                <span class="author">Oscar Wilde</span>
            </div>
            <div class="quote">
                <p class="text">"Two things are infinite: the universe and human stupidity."</p>
                <span class="author">Albert Einstein</span>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Use wanted_dict to specify what we want to scrape
    wanted_dict = {
        'quote_text': ['"Be yourself; everyone else is already taken."'],
        'quote_author': ['Oscar Wilde'],
    }
    
    # Build rules and automatically save for adaptive matching
    results = scraper.adaptive_build(
        html=html,
        wanted_dict=wanted_dict,
        auto_save=True
    )
    
    print(f"Found {len(results)} items")
    print(f"Learned {len(scraper.stack_list)} rules")
    print()
    
    # Now the elements are saved for adaptive matching
    # Even if the website structure changes, we can find them again


def example_multiple_adaptive():
    """
    Example of using get_result_adaptive() to find multiple saved elements at once.
    """
    print("=" * 60)
    print("Example 4: Multiple Adaptive Lookups")
    print("=" * 60)
    
    scraper = AutoScraper(adaptive=True)
    
    # First, save some elements
    original_html = """
    <html>
    <body>
        <header>
            <h1 class="site-title">My Store</h1>
        </header>
        <main>
            <div class="product">
                <h2 class="product-name">Widget Pro</h2>
                <span class="product-price">$49.99</span>
            </div>
        </main>
    </body>
    </html>
    """
    
    soup = scraper._get_soup(html=original_html)
    
    # Save multiple elements
    scraper.adaptive_save(soup.find('h1', class_='site-title'), 'site_title', url='https://mystore.com')
    scraper.adaptive_save(soup.find('h2', class_='product-name'), 'product_name', url='https://mystore.com')
    scraper.adaptive_save(soup.find('span', class_='product-price'), 'product_price', url='https://mystore.com')
    
    print("Saved 3 elements for adaptive matching")
    print()
    
    # Simulate page change
    changed_html = """
    <html>
    <body>
        <div class="header-wrapper">
            <h1 class="brand-name">My Store</h1>
        </div>
        <div class="content">
            <article class="product-card">
                <h2 class="title">Widget Pro</h2>
                <div class="pricing">
                    <span class="price-tag">$49.99</span>
                </div>
            </article>
        </div>
    </body>
    </html>
    """
    
    # Find all saved elements at once
    results = scraper.get_result_adaptive(
        html=changed_html,
        url='https://mystore.com',
        group_by_identifier=True
    )
    
    print("Results after structure change:")
    for identifier, matches in results.items():
        for match in matches:
            print(f"  {identifier}: '{match['text']}' (score: {match['score']*100:.1f}%)")
    
    print()


if __name__ == '__main__':
    example_basic_adaptive()
    example_find_similar()
    example_build_with_adaptive()
    example_multiple_adaptive()
    
    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)
