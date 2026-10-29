"""Check the Pages package under a project-repository URL prefix."""

from urllib.parse import urljoin

from playwright.sync_api import sync_playwright


BASE = "http://pages-preview/news-timeline/"

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1280, "height": 720})
    failed = []
    page.on("response", lambda response: failed.append((response.status, response.url)) if response.status >= 400 else None)
    page.goto(BASE, wait_until="networkidle")
    assert page.title() == "PeaceRep news and impact"
    assert page.locator("meta[name=robots]").get_attribute("content") == "noindex,nofollow"
    assert "editorial preview" in page.locator(".header-title .eyebrow").inner_text().lower()
    assert page.locator(".story").count() == 172
    assert page.locator(".rail-dot").count() == 172
    assert page.locator(".brand img").evaluate("image => image.complete && image.naturalWidth > 0")
    assert page.locator(".story-image img").first.evaluate("image => image.complete && image.naturalWidth > 0")
    assert page.locator(".download-link").count() == 3
    for link in page.locator(".download-link").all():
        response = page.request.head(urljoin(BASE, link.get_attribute("href")))
        assert response.ok and "application/pdf" in response.headers.get("content-type", "")
    page.get_by_role("button", name="Research cited or used").click()
    assert page.locator(".story").count() == 19
    page.goto(BASE + "?story=26876", wait_until="networkidle")
    assert page.locator("#post-26876.expanded .article-content").count() == 1
    assert not failed, failed[:5]
    print("Pages preview passed: 172 posts, images, fonts, filters, story link and 3 PDFs under a repository subpath")
    browser.close()
