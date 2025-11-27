import asyncio
import random
import string
import json
import time
import uuid
from urllib.parse import urlparse, parse_qs
from pyppeteer import launch
from pyppeteer.errors import TimeoutError, NetworkError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SHΔDØW_VIEWER")

# ==================== CONFIG ====================
WATCH_TIME_MIN = 300    # 5 à 30 minutes aléatoire
WATCH_TIME_MAX = 1800
VIEWERS_PER_TASK = 1    # Apify scale via concurrent actors
HEADLESS = True
MOBILE_EMULATION = True  # 50% mobile, 50% desktop

# User-Agents 2025 Fresh Pool
MOBILE_UA = [
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 Chrome/131.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
]

DESKTOP_UA = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_6_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
]

# ================================================

async def random_sleep(min_sec, max_sec):
    await asyncio.sleep(random.uniform(min_sec, max_sec))

async def generate_client_context():
    return {
        "clientName": random.choice(["WEB", "ANDROID", "IOS"]),
        "clientVersion": f"{random.randint(18,19)}.{(random.randint(30,45)):02d}.00",
        "hl": "fr",
        "gl": "FR",
        "deviceMake": "" if random.random() > 0.5 else "Google" if "Android" in random.choice(MOBILE_UA) else "Apple",
        "deviceModel": "".join(random.choices(string.ascii_uppercase + string.digits, k=8)),
        "userAgent": random.choice(MOBILE_UA + DESKTOP_UA),
        "clientScreen": random.choice(["WATCH_FULL_SCREEN", "WATCH_MINI_PLAYER", "WATCH_NORMAL"]),
    }

async def watch_stream(live_url: str, proxy: str = None):
    browser_args = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-infobars",
        "--disable-blink-features=AutomationControlled",
        "--disable-web-security",
        "--disable-features=IsolateOrigins,site-per-process",
        "--no-zygote",
        "--single-process",
        "--disable-gpu",
        "--window-size=1920,1080",
        "--user-agent=" + random.choice(MOBILE_UA + DESKTOP_UA),
    ]

    if proxy:
        browser_args.append(f"--proxy-server={proxy}")

    browser = await launch(
        headless=HEADLESS,
        args=browser_args,
        handleSIGINT=False,
        handleSIGTERM=False,
        handleSIGHUP=False,
    )

    context = await browser.createIncognitoBrowserContext()
    page = await context.newPage()

    # === ANTI-DETECTION MAXIMUM ===
    await page.evaluateOnNewDocument("""
        () => {
            delete navigator.__proto__.webdriver;
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
            Object.defineProperty(navigator, 'languages', { get: () => ['fr-FR', 'fr', 'en'] });
            window.chrome = { runtime: {}, loadTimes: () => {}, csi: () => {} };
            Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => random.randint(4,16) });
            Object.defineProperty(navigator, 'deviceMemory', { get: () => random.choice([4,8,16]) });
        }
    """)

    # Random viewport
    if MOBILE_EMULATION and random.random() > 0.5:
        await page.setViewport({"width": 390, "height": 844, "isMobile": True})
    else:
        await page.setViewport({"width": random.randint(1366, 2560), "height": random.randint(768, 1440)})

    try:
        logger.info(f"[SHΔDØW] Connecting → {live_url}")
        await page.goto(live_url, {"waitUntil": "networkidle0", "timeout": 60000})

        # Accept consent if present (YouTube 2025)
        try:
            await page.waitForSelector("form[action*='consent.youtube.com']", timeout=8000)
            await page.click("button[aria-label*='Accepter']")
            await random_sleep(2, 5)
        except:
            pass

        # Wait for player
        await page.waitForSelector("video", timeout=30000)
        await random_sleep(5, 12)

        # Simulate human behavior
        watch_duration = random.randint(WATCH_TIME_MIN, WATCH_TIME_MAX)
        start_time = time.time()

        while time.time() - start_time < watch_duration:
            # Random scroll, mouse move, pause/play
            if random.random() < 0.15:
                await page.mouse.move(
                    random.randint(100, 800),
                    random.randint(100, 600)
                )
            if random.random() < 0.08:
                await page.keyboard.press(" ")
                await random_sleep(3, 15)
                await page.keyboard.press(" ")
            
            if random.random() < 0.05:
                await page.evaluate("() => document.querySelector('video').currentTime += 30")
            
            await random_sleep(15, 45)

        logger.info(f"[SHΔDØW] Viewer completed — Duration: {int(watch_duration/60)} min")

    except Exception as e:
        logger.error(f"[SHΔDØW] Error: {str(e)}")
    finally:
        await browser.close()

# =============== APIFY ACTOR ENTRYPOINT ===============
from apify import Actor

async def main():
    async with Actor:
        input_data = await Actor.get_input() or {}
        
        live_url = input_data.get("liveUrl")
        proxy_list = input_data.get("proxyList", [])
        concurrent_viewers = input_data.get("concurrent", 10)

        if not live_url or "youtube.com/live" not in live_url:
            await Actor.fail("Invalid or missing YouTube Live URL")

        tasks = []
        for i in range(concurrent_viewers):
            proxy = random.choice(proxy_list) if proxy_list else None
            tasks.append(watch_stream(live_url, proxy))

        await asyncio.gather(*tasks)

        await Actor.push_data({
            "status": "completed",
            "viewers": concurrent_viewers,
            "url": live_url,
            "timestamp": time.time()
        })

if __name__ == "__main__":
    asyncio.run(main())
