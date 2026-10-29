"""Exercise the local timeline and A4 print layout in Chromium."""

import os
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1)
    page.goto("http://site/", wait_until="networkidle")
    page.evaluate("document.fonts.ready")
    assert page.locator("body").evaluate("node => getComputedStyle(node).fontFamily.startsWith('Montserrat')")
    assert page.evaluate("document.fonts.check('700 16px Montserrat')")
    assert page.get_by_role("heading", name="PeaceRep news and impact.").count() == 1
    assert page.locator(".header-title h1").evaluate("node => getComputedStyle(node).fontFamily.startsWith('Montserrat')")
    assert page.locator(".site-nav").count() == 0
    assert page.locator(".brand img").evaluate("image => image.complete && image.naturalWidth > 0")
    assert page.evaluate("document.documentElement.scrollHeight <= innerHeight + 2"), "Desktop page needs an outer scroll"
    assert page.locator("#timeline").evaluate("node => node.scrollHeight > node.clientHeight")
    rail_box = page.locator("#timeline-rail").bounding_box()
    page.mouse.move(rail_box["x"] + 20, rail_box["y"] + 100)
    page.mouse.wheel(0, 250)
    page.wait_for_timeout(100)
    assert page.locator("#timeline").evaluate("node => node.scrollTop > 0"), "Wheel over date rail did not scroll stories"
    page.locator("#timeline").evaluate("node => node.scrollTop = 0")
    assert page.locator(".download-link").count() == 3
    for link in page.locator(".download-link").all():
        response = page.request.head(urljoin(page.url, link.get_attribute("href")))
        assert response.ok and "application/pdf" in response.headers.get("content-type", "")
    assert page.locator(".story").count() == 172
    assert page.locator(".rail-dot").count() == 172
    assert page.locator(".connector").count() > 0
    visible_cards = page.locator(".story").evaluate_all("nodes => { const viewport = document.querySelector('#timeline').getBoundingClientRect(); return nodes.filter(node => { const rect = node.getBoundingClientRect(); return rect.top < viewport.bottom && rect.bottom > viewport.top; }).length; }")
    assert visible_cards >= 2, f"Only {visible_cards} story cards visible"
    assert page.locator(".filter-chip.type-recognition").evaluate("node => getComputedStyle(node).getPropertyValue('--type-color').trim()") == page.locator(".story.type-recognition").first.evaluate("node => getComputedStyle(node).getPropertyValue('--type-color').trim()")
    swatches = page.locator(".filter-chip[class*='type-']").evaluate_all("nodes => nodes.map(node => getComputedStyle(node).getPropertyValue('--type-color').trim())")
    assert len(swatches) == len(set(swatches)) == 10
    page.locator(".filter-chip.type-recognition").hover()
    assert page.locator(".rail-dot.type-preview").count() == 15
    assert page.locator(".rail-dots.previewing").count() == 1
    page.get_by_role("button", name="All stories").hover()
    assert page.locator(".rail-dot.type-preview").count() == 0
    first_image = page.locator(".story-image img").first
    first_image.scroll_into_view_if_needed()
    assert first_image.evaluate("image => image.complete && image.naturalWidth > 0")
    page.screenshot(path=os.getenv("SCREENSHOT_PATH", "/tmp/timeline-check.png"), full_page=True)

    first_id = page.locator(".story").first.get_attribute("data-id")
    page.locator(".story h2").first.click()
    assert page.locator(".story.expanded").count() == 1
    assert page.locator(".story.expanded .article-content p").count() > 0
    assert page.evaluate("new URL(location.href).searchParams.get('story')") == first_id
    if os.getenv("FOCUSED_SCREENSHOT_PATH"):
        page.screenshot(path=os.environ["FOCUSED_SCREENSHOT_PATH"], full_page=True)
    page.locator(".story.expanded [data-open-story]").click()
    assert page.locator(".story.expanded").count() == 0

    focused = browser.new_page(viewport={"width": 1440, "height": 900})
    focused.goto("http://site/?story=26876", wait_until="networkidle")
    assert focused.locator("#post-26876.expanded").count() == 1
    inline_image = focused.locator("#post-26876 .article-content img").first
    inline_image.scroll_into_view_if_needed()
    assert inline_image.evaluate("image => image.complete && image.naturalWidth > 0")
    focused.emulate_media(media="print")
    assert focused.locator(".story:not(.expanded)").first.evaluate("node => getComputedStyle(node).display === 'none'")
    if not os.getenv("SKIP_PDF"):
        focused_pdf = focused.pdf(format="A4", print_background=True)
        assert focused_pdf.startswith(b"%PDF-") and len(focused_pdf) > 10_000
    focused.close()

    linked = browser.new_page(viewport={"width": 1440, "height": 900})
    linked.goto("http://site/?story=26639", wait_until="networkidle")
    linked.locator(".article-content a[data-local-story='25780']").first.click()
    assert linked.locator("#post-25780.expanded").count() == 1
    assert linked.evaluate("new URL(location.href).searchParams.get('story')") == "25780"
    linked.close()

    mobile = browser.new_page(viewport={"width": 390, "height": 844})
    mobile.goto("http://site/", wait_until="networkidle")
    assert mobile.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
    mobile.locator(".story [data-open-story]").first.click()
    assert mobile.locator(".story.expanded .article-content p").count() > 0
    mobile.close()

    for width, height in ((1280, 720), (1024, 768)):
        desktop = browser.new_page(viewport={"width": width, "height": height})
        desktop.goto("http://site/", wait_until="networkidle")
        assert desktop.evaluate("document.documentElement.scrollHeight <= innerHeight + 2")
        assert desktop.locator("#timeline").evaluate("node => node.clientHeight >= 280")
        desktop.close()

    last_dot = page.locator(".rail-dot").last
    target = last_dot.get_attribute("data-id")
    last_dot.click()
    page.wait_for_timeout(800)
    assert page.locator(f"#post-{target}").evaluate("node => { const r = node.getBoundingClientRect(); const t = document.querySelector('#timeline').getBoundingClientRect(); return r.top < t.bottom && r.bottom > t.top; }")
    assert page.locator(f"#post-{target}.active").count() == 1
    assert page.locator(".connector.active").count() == 1
    page.mouse.move(5, 5)
    assert page.locator(f"#post-{target}.active").count() == 1
    assert page.locator(".connector.active").count() == 1
    if os.getenv("SELECTED_SCREENSHOT_PATH"):
        page.screenshot(path=os.environ["SELECTED_SCREENSHOT_PATH"], full_page=True)

    page.get_by_role("button", name="Media engagements").click()
    assert 0 < page.locator(".story").count() < 172
    page.get_by_role("button", name="Research responses to current events").click()
    assert page.locator(".story").count() == 8
    page.get_by_role("button", name="All stories").click()
    assert page.locator(".story").count() == 172
    page.evaluate("window.print = () => { window.__printCalled = true; }")
    page.get_by_role("button", name="Print current view").click()
    assert page.evaluate("window.__printCalled === true")

    page.emulate_media(media="print")
    assert page.locator(".story").count() == 172
    assert page.locator("#timeline").evaluate("node => getComputedStyle(node).overflowY === 'visible'")
    assert page.locator("#timeline-shell").evaluate("node => node.clientHeight > innerHeight && getComputedStyle(node).overflow === 'visible'")
    if not os.getenv("SKIP_PDF"):
        pdf = page.pdf(format="A4", print_background=True)
        assert pdf.startswith(b"%PDF-") and len(pdf) > 100_000
        print(f"Browser check passed: 172 cards, 172 dots, connected navigation, images, filters, print action, A4 PDF ({len(pdf)} bytes)")
    else:
        print(f"Browser check passed: {visible_cards} visible cards, category hover, 172 dots, navigation, images, filters and print layout")
    browser.close()
