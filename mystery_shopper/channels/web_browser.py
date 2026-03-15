"""Website browsing channel — AI visits and analyzes hotel websites."""

import asyncio
import json
import subprocess
import os
from datetime import datetime
from ..orchestrator.journey import StepResult, StepStatus, JourneyStep


async def browse_website(step: JourneyStep, context: dict) -> StepResult:
    """Browse a hotel website, take screenshots, extract info."""
    result = StepResult(
        step_name=step.name,
        step_type=step.step_type,
        started_at=datetime.now(),
    )

    url = step.config.get("url", "")
    if not url:
        result.status = StepStatus.FAILED
        result.notes = "No URL provided"
        return result

    print(f"   🌐 Browsing: {url}")

    try:
        # Use Playwright to browse the website
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )

            # Visit homepage
            await page.goto(url, wait_until="networkidle", timeout=30000)
            print(f"   📸 Taking screenshot of homepage...")

            # Screenshot
            screenshots_dir = "data/screenshots"
            os.makedirs(screenshots_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ss_path = f"{screenshots_dir}/{timestamp}_homepage.png"
            await page.screenshot(path=ss_path, full_page=False)
            result.screenshots.append(ss_path)

            # Extract page content
            content = await page.content()
            text = await page.inner_text("body")

            # Check for chat widget
            chat_selectors = [
                "[class*='chat']", "[id*='chat']", "[class*='livechat']",
                "[class*='intercom']", "[class*='zendesk']", "[class*='tawk']",
                "[class*='drift']", "[class*='crisp']", "iframe[src*='chat']",
            ]
            has_chat = False
            for sel in chat_selectors:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        has_chat = True
                        break
                except Exception:
                    pass

            # Check for booking widget
            booking_selectors = [
                "[class*='booking']", "[id*='booking']", "[class*='reservation']",
                "input[type='date']", "[class*='check-in']", "[class*='checkin']",
            ]
            has_booking = False
            for sel in booking_selectors:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        has_booking = True
                        break
                except Exception:
                    pass

            # Try to find rooms page
            room_links = await page.query_selector_all("a[href*='room'], a[href*='accommodation'], a[href*='suite']")
            if room_links:
                first_link = room_links[0]
                href = await first_link.get_attribute("href")
                if href:
                    if not href.startswith("http"):
                        href = url.rstrip("/") + "/" + href.lstrip("/")
                    print(f"   📸 Visiting rooms page: {href}")
                    await page.goto(href, wait_until="networkidle", timeout=15000)
                    ss_rooms = f"{screenshots_dir}/{timestamp}_rooms.png"
                    await page.screenshot(path=ss_rooms, full_page=False)
                    result.screenshots.append(ss_rooms)

            await browser.close()

            result.status = StepStatus.COMPLETED
            result.completed_at = datetime.now()
            result.data_received = text[:2000]
            result.notes = f"Website browsed. Chat: {'Yes' if has_chat else 'No'}. Booking widget: {'Yes' if has_booking else 'No'}"
            result.context_for_next = {
                "has_chat": has_chat,
                "has_booking": has_booking,
                "website_text": text[:1000],
            }

            print(f"   💬 Live chat widget: {'✅ Found' if has_chat else '❌ Not found'}")
            print(f"   📅 Booking widget: {'✅ Found' if has_booking else '❌ Not found'}")

    except ImportError:
        # Playwright not installed — use web_fetch fallback
        print("   ⚠️  Playwright not installed, using simple fetch...")
        try:
            import httpx
            resp = httpx.get(url, follow_redirects=True, timeout=15)
            result.data_received = resp.text[:2000]
            result.status = StepStatus.COMPLETED
            result.completed_at = datetime.now()
            result.context_for_next = {"has_chat": False, "has_booking": False}
            result.notes = "Fetched via HTTP (no browser). Install playwright for full browsing."
        except Exception as e:
            result.status = StepStatus.FAILED
            result.notes = f"Failed to fetch: {e}"

    except Exception as e:
        result.status = StepStatus.FAILED
        result.notes = str(e)

    return result
