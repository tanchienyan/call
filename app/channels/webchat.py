"""Webchat channel — interact with hotel website chatbots via Playwright."""

import asyncio
import os
from datetime import datetime


# Common chat widget selectors for major providers
CHAT_TRIGGERS = [
    # Intercom
    "[class*='intercom-launcher']", "#intercom-container iframe",
    # Drift
    "[class*='drift-widget']", "#drift-widget",
    # Tawk.to
    "[class*='tawk-button']", "#tawk-to-chat",
    # LiveChat
    "[id*='livechat']", "[class*='livechat']",
    # Zendesk
    "[class*='zopim']", "iframe[title*='chat']", "[id*='launcher']",
    # HubSpot
    "#hubspot-messages-iframe-container",
    # Tidio
    "#tidio-chat",
    # Crisp
    "[class*='crisp-client']",
    # Generic
    "[class*='chat-trigger']", "[class*='chat-button']", "[class*='chat-widget']",
    "button[aria-label*='chat' i]", "button[aria-label*='Chat' i]",
    "[data-testid*='chat']", "[class*='widget-button']",
]

CHAT_INPUTS = [
    "textarea[class*='chat']", "input[class*='chat']",
    "[contenteditable='true']", "textarea[placeholder*='message' i]",
    "textarea[placeholder*='type' i]", "input[placeholder*='message' i]",
    "input[placeholder*='type' i]",
]


async def detect_chat_widget(url: str) -> dict:
    """Browse a hotel website and detect if it has a chat widget.
    
    Returns: {has_chat, provider, widget_selector, screenshots[]}
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"has_chat": False, "error": "Playwright not installed"}

    result = {
        "has_chat": False,
        "provider": None,
        "widget_selector": None,
        "screenshots": [],
        "page_title": "",
        "load_time_ms": 0,
    }

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = await ctx.new_page()

            start = datetime.now()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            result["load_time_ms"] = (datetime.now() - start).total_seconds() * 1000
            result["page_title"] = await page.title()

            # Screenshot homepage
            os.makedirs("data/screenshots", exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            ss_path = f"data/screenshots/homepage_{ts}.png"
            await page.screenshot(path=ss_path, full_page=False)
            result["screenshots"].append(ss_path)

            # Wait a bit for lazy-loaded widgets
            await asyncio.sleep(3)

            # Detect chat widget
            for selector in CHAT_TRIGGERS:
                try:
                    el = await page.query_selector(selector)
                    if el and await el.is_visible():
                        result["has_chat"] = True
                        result["widget_selector"] = selector

                        # Identify provider
                        if "intercom" in selector:
                            result["provider"] = "Intercom"
                        elif "drift" in selector:
                            result["provider"] = "Drift"
                        elif "tawk" in selector:
                            result["provider"] = "Tawk.to"
                        elif "livechat" in selector:
                            result["provider"] = "LiveChat"
                        elif "zopim" in selector or "zendesk" in selector:
                            result["provider"] = "Zendesk"
                        elif "hubspot" in selector:
                            result["provider"] = "HubSpot"
                        elif "tidio" in selector:
                            result["provider"] = "Tidio"
                        elif "crisp" in selector:
                            result["provider"] = "Crisp"
                        else:
                            result["provider"] = "Unknown"
                        break
                except Exception:
                    continue

            await browser.close()

    except Exception as e:
        result["error"] = str(e)

    return result


async def chat_interaction(
    url: str,
    messages: list[str] = None,
    wait_for_reply_seconds: int = 30,
) -> dict:
    """Open a website's chat widget and have a conversation.
    
    Returns: {success, messages_sent, responses, screenshots, transcript}
    """
    if messages is None:
        messages = [
            "Hi, I'm looking to book a room for next Thursday to Sunday. Do you have availability?",
        ]

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"success": False, "error": "Playwright not installed"}

    result = {
        "success": False,
        "messages_sent": [],
        "responses": [],
        "screenshots": [],
        "transcript": "",
    }

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = await ctx.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)

            # Find and click chat trigger
            chat_opened = False
            for selector in CHAT_TRIGGERS:
                try:
                    el = await page.query_selector(selector)
                    if el and await el.is_visible():
                        await el.click()
                        chat_opened = True
                        await asyncio.sleep(2)
                        break
                except Exception:
                    continue

            if not chat_opened:
                result["error"] = "Could not find or open chat widget"
                await browser.close()
                return result

            # Find input field
            input_el = None
            # Check inside iframes too
            frames = [page] + page.frames
            for frame in frames:
                for selector in CHAT_INPUTS:
                    try:
                        el = await frame.query_selector(selector)
                        if el:
                            input_el = el
                            break
                    except Exception:
                        continue
                if input_el:
                    break

            if not input_el:
                result["error"] = "Could not find chat input field"
                os.makedirs("data/screenshots", exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                ss = f"data/screenshots/chat_noinput_{ts}.png"
                await page.screenshot(path=ss)
                result["screenshots"].append(ss)
                await browser.close()
                return result

            # Send messages and capture responses
            transcript_lines = []
            for msg in messages:
                await input_el.fill(msg)
                await page.keyboard.press("Enter")
                result["messages_sent"].append(msg)
                transcript_lines.append(f"Guest: {msg}")

                # Wait for reply
                await asyncio.sleep(wait_for_reply_seconds)

                # Screenshot after each exchange
                os.makedirs("data/screenshots", exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                ss = f"data/screenshots/chat_{ts}.png"
                await page.screenshot(path=ss)
                result["screenshots"].append(ss)

            result["success"] = True
            result["transcript"] = "\n".join(transcript_lines)
            await browser.close()

    except Exception as e:
        result["error"] = str(e)

    return result


async def browse_website(url: str) -> dict:
    """Browse a hotel website and extract key information.
    
    Returns: {title, screenshots[], has_chat, has_booking, room_info, contact_info}
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"error": "Playwright not installed"}

    result = {
        "title": "",
        "screenshots": [],
        "has_chat": False,
        "has_booking": False,
        "room_info": [],
        "contact_info": {},
        "load_time_ms": 0,
        "pages_visited": [],
    }

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            )
            page = await ctx.new_page()

            start = datetime.now()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            result["load_time_ms"] = (datetime.now() - start).total_seconds() * 1000
            result["title"] = await page.title()

            os.makedirs("data/screenshots", exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Homepage screenshot
            ss = f"data/screenshots/browse_home_{ts}.png"
            await page.screenshot(path=ss, full_page=False)
            result["screenshots"].append(ss)
            result["pages_visited"].append({"url": url, "title": result["title"]})

            await asyncio.sleep(2)

            # Check for chat widget
            for sel in CHAT_TRIGGERS:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        result["has_chat"] = True
                        break
                except Exception:
                    continue

            # Check for booking widget
            booking_selectors = [
                "[class*='booking']", "[id*='booking']", "[class*='reserv']",
                "a[href*='book']", "button:has-text('Book')", "a:has-text('Book Now')",
                "[class*='datepicker']", "input[type='date']",
            ]
            for sel in booking_selectors:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        result["has_booking"] = True
                        break
                except Exception:
                    continue

            # Try to navigate to rooms page
            rooms_links = [
                "a:has-text('Rooms')", "a:has-text('rooms')",
                "a:has-text('Suites')", "a:has-text('Accommodation')",
                "a[href*='room']", "a[href*='suite']",
            ]
            for sel in rooms_links:
                try:
                    link = await page.query_selector(sel)
                    if link:
                        await link.click()
                        await page.wait_for_load_state("networkidle", timeout=10000)
                        ss2 = f"data/screenshots/browse_rooms_{ts}.png"
                        await page.screenshot(path=ss2, full_page=False)
                        result["screenshots"].append(ss2)
                        result["pages_visited"].append({
                            "url": page.url,
                            "title": await page.title()
                        })
                        break
                except Exception:
                    continue

            await browser.close()

    except Exception as e:
        result["error"] = str(e)

    return result
