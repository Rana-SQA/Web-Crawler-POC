"""
Phase 2: Hotel Price Scraping Script
Scrapes hotel prices using the discovered room profile from Phase 1.
"""

import asyncio
import os
import json
import random
import time
from datetime import date, timedelta
from typing import List, Optional, Dict
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError
from dotenv import load_dotenv

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    LLMConfig,
    LLMExtractionStrategy,
)

# Load environment variables
load_dotenv()

# ============= DATA MODELS =============
class RoomListing(BaseModel):
    """Represents a single room listing with its name and price."""
    name: str = Field(..., description="The name or type of the hotel room")
    price: str = Field(..., description="The price for the room, including currency")

class DailyRate(BaseModel):
    """Represents all room listings for a specific date."""
    date: str = Field(..., description="The check-in date in YYYY-MM-DD format")
    listings: List[RoomListing] = Field(..., description="List of room listings")

class HotelData(BaseModel):
    """The final data structure for the hotel."""
    hotel_name: str = Field(..., description="The name of the hotel")
    daily_rates: List[DailyRate] = Field(..., description="Pricing information for each date")

class HotelProfile(BaseModel):
    """Hotel profile with discovered room types."""
    hotel_name: str
    hotel_url: str
    room_types: List[str]
    last_updated: str
    metadata: Dict = Field(default_factory=dict)

# ============= UTILITY FUNCTIONS =============
def load_hotel_profile(hotel_name: str, profiles_dir: str = "hotel_profiles") -> Optional[HotelProfile]:
    """Load hotel profile from JSON file."""
    filename = f"{profiles_dir}/{hotel_name.replace(' ', '_').lower()}_profile.json"
    if Path(filename).exists():
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return HotelProfile(**data)
    else:
        print(f"❌ Profile not found: {filename}")
        print(f"   Please run discover_rooms.py first to create a hotel profile.")
    return None

def extract_first_json_object(text: str) -> Optional[str]:
    """Extract the first balanced JSON object from text."""
    if not text:
        return None
    s = text.strip()
    start = -1
    brace_count = 0
    in_string = False
    escape = False
    
    for i, ch in enumerate(s):
        if ch == '\\' and not escape:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
        if not in_string:
            if ch == '{':
                if brace_count == 0:
                    start = i
                brace_count += 1
            elif ch == '}':
                if brace_count > 0:
                    brace_count -= 1
                    if brace_count == 0 and start != -1:
                        return s[start:i+1]
        if escape:
            escape = False
    return None

def save_results(hotel_data: HotelData, output_dir: str = "scraped_data"):
    """Save scraped data to JSON file."""
    Path(output_dir).mkdir(exist_ok=True)
    timestamp = date.today().strftime('%Y%m%d')
    filename = f"{output_dir}/{hotel_data.hotel_name.replace(' ', '_').lower()}_prices_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(hotel_data.dict(), f, ensure_ascii=False, indent=4)
    
    print(f"💾 Data saved to {filename}")
    return filename

# ============= ANTI-BOT DETECTION FUNCTIONS =============
def get_random_user_agent() -> str:
    """Get a random realistic user agent string."""
    user_agents = [
        # Chrome on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # Chrome on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        # Firefox on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
        # Firefox on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
        # Safari on macOS
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        # Edge on Windows
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    ]
    return random.choice(user_agents)

def get_random_viewport() -> Dict[str, int]:
    """Get random but realistic viewport dimensions."""
    viewports = [
        {"width": 1920, "height": 1080},  # Full HD
        {"width": 1366, "height": 768},   # Popular laptop
        {"width": 1440, "height": 900},   # MacBook Air
        {"width": 1536, "height": 864},   # Windows laptop
        {"width": 1280, "height": 720},   # HD
        {"width": 1600, "height": 900},   # 16:9 widescreen
        {"width": 2560, "height": 1440},  # 2K
    ]
    return random.choice(viewports)

def get_enhanced_browser_args() -> List[str]:
    """Get comprehensive browser arguments to avoid detection."""
    return [
        # Basic anti-detection
        "--disable-blink-features=AutomationControlled",
        "--disable-web-security",
        "--disable-dev-shm-usage",
        "--no-sandbox",
        
        # Memory and performance
        "--memory-pressure-off",
        "--max_old_space_size=4096",
        
        # Audio/video to appear more human
        "--autoplay-policy=no-user-gesture-required",
        "--disable-background-timer-throttling",
        "--disable-backgrounding-occluded-windows",
        "--disable-renderer-backgrounding",
        
        # Remove automation indicators
        "--disable-automation",
        "--disable-extensions",
        "--disable-plugins-discovery",
        "--disable-ipc-flooding-protection",
        
        # Language and locale
        "--lang=en-US,en",
        "--accept-lang=en-US,en;q=0.9",
        
        # Screen and graphics
        "--force-device-scale-factor=1",
        "--disable-gpu-sandbox",
        
        # Network behavior
        "--aggressive-cache-discard",
        "--disable-background-networking",
        
        # Enhanced stealth for Expedia
        "--disable-features=VizDisplayCompositor",
        "--disable-features=TranslateUI",
        "--disable-features=BlinkGenPropertyTrees",
        "--disable-infobars",
        "--disable-logging",
        "--disable-login-animations",
        "--disable-notifications",
        "--disable-permissions-api",
        "--disable-popup-blocking",
        "--disable-print-preview",
        "--disable-prompt-on-repost",
        "--disable-renderer-backgrounding",
        "--disable-save-password-bubble",
        "--disable-spell-checking",
        "--disable-sync",
        "--disable-translate",
        "--disable-web-resources",
        "--hide-scrollbars",
        "--mute-audio",
        "--no-default-browser-check",
        "--no-first-run",
        "--no-pings",
        "--no-zygote",
        "--disable-gpu",
        "--disable-gpu-sandbox",
        "--disable-software-rasterizer",
        
        # Misc stealth
        "--disable-client-side-phishing-detection",
        "--disable-component-extensions-with-background-pages",
        "--disable-default-apps",
        "--disable-hang-monitor",
        "--enable-automation=false",
        "--password-store=basic",
        "--use-mock-keychain",
    ]

def get_stealth_js_code() -> List[str]:
    """Get JavaScript code to make the browser appear more human."""
    return [
        # Comprehensive webdriver removal
        """
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
        });
        delete navigator.__proto__.webdriver;
        delete navigator.webdriver;
        """,
        
        # Override automation properties with realistic values
        """
        Object.defineProperty(navigator, 'plugins', {
            get: () => ({
                0: {name: "Chrome PDF Plugin", filename: "internal-pdf-viewer"},
                1: {name: "Chrome PDF Viewer", filename: "mhjfbmdgcfjbbpaeojofohoefgiehjai"},
                2: {name: "Native Client", filename: "internal-nacl-plugin"},
                length: 3
            }),
        });
        """,
        
        # Enhanced Chrome object spoofing
        """
        window.chrome = {
            runtime: {
                onConnect: undefined,
                onMessage: undefined
            },
            loadTimes: function() {
                return {
                    commitLoadTime: Date.now() - Math.random() * 1000,
                    finishDocumentLoadTime: Date.now() - Math.random() * 500,
                    finishLoadTime: Date.now() - Math.random() * 200,
                    firstPaintAfterLoadTime: Date.now() - Math.random() * 100,
                    firstPaintTime: Date.now() - Math.random() * 50,
                    navigationType: "Other",
                    npnNegotiatedProtocol: "h2",
                    requestTime: Date.now() - Math.random() * 2000,
                    startLoadTime: Date.now() - Math.random() * 1500,
                    wasAlternateProtocolAvailable: false,
                    wasFetchedViaSpdy: true,
                    wasNpnNegotiated: true
                };
            },
            csi: function() {
                return {
                    pageT: Date.now() - Math.random() * 1000,
                    startE: Date.now() - Math.random() * 2000,
                    tran: 15
                };
            },
            app: {
                isInstalled: false
            }
        };
        """,
        
        # Override permissions API
        """
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );
        """,
        
        # Spoof language properties
        """
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
        });
        Object.defineProperty(navigator, 'language', {
            get: () => 'en-US',
        });
        """,
        
        # Override screen properties to look realistic
        """
        Object.defineProperty(screen, 'colorDepth', {
            get: () => 24,
        });
        Object.defineProperty(screen, 'pixelDepth', {
            get: () => 24,
        });
        """,
        
        # Mask automation detection techniques
        """
        // Remove common automation indicators
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        
        // Override iframe detection
        if (window.top !== window.self) {
            Object.defineProperty(window, 'top', {
                get: () => window,
            });
        }
        """,
        
        # Simulate real browser timing
        """
        // Override performance timing to look realistic
        const originalGetEntries = performance.getEntries;
        performance.getEntries = function() {
            const entries = originalGetEntries.call(this);
            // Add some realistic timing variations
            entries.forEach(entry => {
                if (entry.connectEnd) entry.connectEnd += Math.random() * 10;
                if (entry.domainLookupEnd) entry.domainLookupEnd += Math.random() * 5;
            });
            return entries;
        };
        """,
        
        # Random mouse movements to simulate human behavior (enhanced)
        """
        let mouseMovementInterval;
        function startMouseMovement() {
            if (mouseMovementInterval) clearInterval(mouseMovementInterval);
            mouseMovementInterval = setInterval(() => {
                const x = Math.random() * window.innerWidth;
                const y = Math.random() * window.innerHeight;
                const event = new MouseEvent('mousemove', {
                    clientX: x,
                    clientY: y,
                    bubbles: true
                });
                document.dispatchEvent(event);
            }, Math.random() * 3000 + 1000);
        }
        startMouseMovement();
        """,
        
        # Random scrolling with realistic patterns
        """
        function humanScroll() {
            const scrollAmount = Math.random() * 200 - 100; // Can scroll up or down
            const currentScroll = window.pageYOffset;
            const maxScroll = document.body.scrollHeight - window.innerHeight;
            
            if ((scrollAmount > 0 && currentScroll < maxScroll) || 
                (scrollAmount < 0 && currentScroll > 0)) {
                window.scrollBy(0, scrollAmount);
                
                // Sometimes scroll back a bit (human behavior)
                if (Math.random() < 0.3) {
                    setTimeout(() => {
                        window.scrollBy(0, -scrollAmount * 0.3);
                    }, 100 + Math.random() * 200);
                }
            }
        }
        
        setInterval(humanScroll, Math.random() * 8000 + 2000);
        """,
        
        # Simulate realistic keyboard events occasionally
        """
        function simulateKeyPress() {
            const keys = ['ArrowDown', 'ArrowUp', 'PageDown', 'PageUp', 'Tab'];
            const key = keys[Math.floor(Math.random() * keys.length)];
            
            const event = new KeyboardEvent('keydown', {
                key: key,
                bubbles: true
            });
            document.dispatchEvent(event);
        }
        
        // Random key presses
        setInterval(simulateKeyPress, Math.random() * 30000 + 10000);
        """,
    ]

async def human_like_delay(min_seconds: float = 2.0, max_seconds: float = 8.0) -> None:
    """Implement human-like delays with randomization."""
    base_delay = random.uniform(min_seconds, max_seconds)
    
    # Add occasional longer delays (10% chance)
    if random.random() < 0.1:
        base_delay += random.uniform(5, 15)
        print(f"   Taking a longer break ({base_delay:.1f}s) to appear more human...")
    
    # Add micro-delays to simulate thinking
    thinking_delays = [0.1, 0.3, 0.5, 0.8]
    for _ in range(random.randint(1, 3)):
        await asyncio.sleep(random.choice(thinking_delays))
    
    print(f"   Waiting {base_delay:.1f} seconds...")
    await asyncio.sleep(base_delay)

async def warm_up_session(crawler, base_url: str) -> bool:
    """Warm up the session by visiting the main site first."""
    print("🔥 Warming up session by visiting main site...")
    
    # Visit main Expedia page first
    main_url = "https://www.expedia.co.jp/"
    
    warmup_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        wait_until="load",
        page_timeout=60000,
        js_code=[
            # Just basic browsing behavior
            "await new Promise(r => setTimeout(r, 2000));",
            "window.scrollTo(0, 300);",
            "await new Promise(r => setTimeout(r, 1000));",
            "window.scrollTo(0, 0);",
            "await new Promise(r => setTimeout(r, 1000));",
        ]
    )
    
    try:
        result = await crawler.arun(url=main_url, config=warmup_config)
        if result.success:
            print("   ✓ Warmup successful")
            await asyncio.sleep(random.uniform(3, 7))  # Natural delay
            return True
        else:
            print("   ⚠️ Warmup failed, continuing anyway...")
            return False
    except Exception as e:
        print(f"   ⚠️ Warmup error: {e}")
        return False

def get_realistic_headers() -> Dict[str, str]:
    """Get realistic HTTP headers."""
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
        "Cache-Control": "no-cache",
        "DNT": "1",
        "Pragma": "no-cache",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }

class SessionManager:
    """Manages sessions to maintain consistency across requests."""
    
    def __init__(self):
        self.session_id = f"session_{int(time.time())}_{random.randint(1000, 9999)}"
        self.user_agent = get_random_user_agent()
        self.viewport = get_random_viewport()
        self.request_count = 0
        self.start_time = time.time()
        self.cleanup_browser_data()
        
    def should_rotate_session(self) -> bool:
        """Determine if session should be rotated based on usage patterns."""
        # Rotate after too many requests or too much time
        time_limit = 20 * 60  # 20 minutes (reduced)
        request_limit = 10     # 10 requests (reduced)
        
        elapsed = time.time() - self.start_time
        return (self.request_count >= request_limit or elapsed >= time_limit)
    
    def increment_request(self):
        """Track request count."""
        self.request_count += 1
    
    def cleanup_browser_data(self):
        """Clean up any temporary files if needed."""
        try:
            # Clean up any temporary files that might exist
            print(f"   🧹 Session cleanup completed")
        except Exception as e:
            print(f"   ⚠️ Cleanup warning: {e}")
    
    def rotate_session(self):
        """Create new session parameters."""
        print("🔄 Rotating session for better stealth...")
        self.cleanup_browser_data()
        self.__init__()  # Reset all parameters

# ============= PRICE SCRAPING FUNCTION =============
async def scrape_hotel_prices(
    hotel_profile: HotelProfile,
    start_date: date,
    num_days_to_scrape: int = 1,
    target_selector: str = "div[data-stid='section-room-list']",
    save_data: bool = True
) -> Optional[HotelData]:
    """
    Scrape hotel prices using the discovered hotel profile with enhanced anti-bot measures.
    
    Args:
        hotel_profile: Hotel profile with room types from Phase 1
        start_date: Starting date for price scraping
        num_days_to_scrape: Number of consecutive days to scrape
        target_selector: CSS selector for room list container
        save_data: Whether to save the results to disk
    
    Returns:
        HotelData with all scraped prices, or None if failed
    """
    print(f"\n{'='*60}")
    print(f"💰 SCRAPING PRICES FOR {hotel_profile.hotel_name}")
    print(f"{'='*60}\n")
    print(f"Configuration:")
    print(f"  - Profile has {len(hotel_profile.room_types)} room types")
    print(f"  - Scraping {num_days_to_scrape} consecutive days")
    print(f"  - Starting from: {start_date}")
    print(f"  - Enhanced anti-bot measures: ENABLED")
    print(f"\nKnown room types:")
    for i, room in enumerate(hotel_profile.room_types, 1):
        print(f"  {i}. {room}")
    print()
    
    # Initialize session manager
    session_manager = SessionManager()
    print(f"🛡️ Initialized stealth session: {session_manager.session_id}")
    print(f"   User Agent: {session_manager.user_agent[:50]}...")
    print(f"   Viewport: {session_manager.viewport['width']}x{session_manager.viewport['height']}")
    
    # Generate URLs for each day
    urls_and_dates = []
    for i in range(num_days_to_scrape):
        checkin_date = start_date + timedelta(days=i)
        checkout_date = checkin_date + timedelta(days=1)
        
        checkin_str = checkin_date.strftime('%Y-%m-%d')
        checkout_str = checkout_date.strftime('%Y-%m-%d')
        
        url = f"{hotel_profile.hotel_url}?chkin={checkin_str}&chkout={checkout_str}&x_pwa=1&rfrr=HSR"
        urls_and_dates.append({"url": url, "date": checkin_str})
    
    all_daily_rates = []
    
    for idx, item in enumerate(urls_and_dates, 1):
        url = item["url"]
        current_date_str = item["date"]
        print(f"📅 Day {idx}/{num_days_to_scrape}: {current_date_str}")
        
        # Check if session should be rotated
        if session_manager.should_rotate_session():
            session_manager.rotate_session()
        
        session_manager.increment_request()
        
        # Enhanced browser config with stealth measures
        browser_config = BrowserConfig(
            browser_type="undetected",
            headless=False,  # Visible browser for better stealth
            user_agent=session_manager.user_agent,
            viewport_width=session_manager.viewport["width"],
            viewport_height=session_manager.viewport["height"],
            extra_args=get_enhanced_browser_args(),
            headers=get_realistic_headers()
        )
        
        # Human-like delay between requests
        if idx > 1:
            await human_like_delay(8, 20)  # Longer delays to avoid detection
        
        # Enhanced browser configuration with anti-detection
        async with AsyncWebCrawler(config=browser_config) as crawler:
            
            # Warm up session on first request
            if idx == 1:
                await warm_up_session(crawler, hotel_profile.hotel_url)
            
            # Create extraction prompt using hotel profile
            room_list_formatted = '\n'.join([f"   {i}. {room}" 
                                            for i, room in enumerate(hotel_profile.room_types, 1)])
            
            extraction_prompt = f"""
            Extract room prices for {hotel_profile.hotel_name} on {current_date_str}.
            
            This hotel has EXACTLY {len(hotel_profile.room_types)} room types:
            {room_list_formatted}
            
            CRITICAL INSTRUCTIONS:
            1. You MUST find ALL {len(hotel_profile.room_types)} room types listed above
            2. For each room, extract:
               - The EXACT room name as listed above
               - The price (e.g., "¥14,618 total", "$150 total")
               - For price extract only the price and currency value without total text
               - If sold out: use "Sold Out"
               - If no price shown: use "Price Not Available"
               - If room not found: use "Sold Out"
            
            3. Check the ENTIRE page content thoroughly
            4. Your response MUST include ALL {len(hotel_profile.room_types)} rooms
            
            Output format:
            {{
                "date": "{current_date_str}",
                "listings": [
                    {{"name": "exact room name", "price": "price or status"}},
                    ... (ALL {len(hotel_profile.room_types)} rooms must be included)
                ]
            }}
            
            Return ONLY the JSON object, no explanations.
            """
            
            # Configure LLM
            llm_config = LLMConfig(
                provider="gemini/gemini-1.5-flash",
                api_token=os.getenv("GEMINI_API_KEY")
            )
            
            extraction_strategy = LLMExtractionStrategy(
                llm_config=llm_config,
                schema=DailyRate.model_json_schema(),
                instruction=extraction_prompt,
                input_format="markdown",
                extraction_type="schema"
            )
            
            # Enhanced crawler config with stealth measures
            stealth_js = get_stealth_js_code()
            
            crawler_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                wait_until="load",
                wait_for=(
                    "js:() => {"
                    "// Check for CAPTCHA or bot detection"
                    "const captchaIndicators = ["
                    "  'Show us your human side',"
                    "  'prove you are human',"
                    "  'captcha',"
                    "  'robot',"
                    "  'Start Puzzle'"
                    "];"
                    "const pageText = document.body.innerText.toLowerCase();"
                    "const hasCaptcha = captchaIndicators.some(indicator => pageText.includes(indicator.toLowerCase()));"
                    "if (hasCaptcha) {"
                    "  console.log('CAPTCHA detected');"
                    "  return false;"
                    "}"
                    "const c = document.querySelector(\"div[data-stid='section-room-list']\");"
                    "if (!c) return false;"
                    "const hasPriceEls = c.querySelectorAll(\"[data-test-id='price-summary']\").length > 0;"
                    "const hasYen = /¥|￥/.test(c.innerText);"
                    "const hasDollar = /\\$/.test(c.innerText);"
                    "return hasPriceEls || hasYen || hasDollar;"
                    "}"
                ),
                page_timeout=180000,
                locale="en-US",
                css_selector=target_selector,
                js_code=stealth_js + [
                    # Initial delay and setup
                    "await new Promise(r => setTimeout(r, 2000));",
                    
                    # Check for CAPTCHA immediately
                    """
                    const captchaKeywords = ['Show us your human side', 'prove you are human', 'captcha', 'robot', 'Start Puzzle'];
                    const pageContent = document.body.innerText.toLowerCase();
                    const hasCaptcha = captchaKeywords.some(keyword => pageContent.includes(keyword.toLowerCase()));
                    if (hasCaptcha) {
                        console.log('CAPTCHA page detected, stopping execution');
                        throw new Error('CAPTCHA_DETECTED');
                    }
                    """,
                    
                    # Enhanced human-like scrolling with pauses
                    """
                    // Simulate realistic reading and browsing behavior
                    async function humanBrowsing() {
                        const scrollHeight = document.body.scrollHeight;
                        const viewportHeight = window.innerHeight;
                        const steps = Math.min(10, Math.floor(scrollHeight / (viewportHeight * 0.8)));
                        
                        for (let i = 0; i < steps; i++) {
                            const scrollTo = (i * scrollHeight) / steps;
                            window.scrollTo({
                                top: scrollTo,
                                behavior: 'smooth'
                            });
                            
                            // Random pause to simulate reading
                            await new Promise(r => setTimeout(r, Math.random() * 1000 + 500));
                            
                            // Sometimes pause longer (like reading something interesting)
                            if (Math.random() < 0.3) {
                                await new Promise(r => setTimeout(r, Math.random() * 2000 + 1000));
                            }
                        }
                        
                        // Scroll back to top
                        window.scrollTo({top: 0, behavior: 'smooth'});
                        await new Promise(r => setTimeout(r, 1000));
                    }
                    
                    await humanBrowsing();
                    """,
                    
                    # Simulate mouse movement over elements with realistic timing
                    """
                    const roomElements = document.querySelectorAll('[data-stid="section-room-list"] > div, .room-item, .listing');
                    if (roomElements.length > 0) {
                        for (let i = 0; i < Math.min(roomElements.length, 5); i++) {
                            const el = roomElements[i];
                            const rect = el.getBoundingClientRect();
                            
                            // Move mouse to element
                            const moveEvent = new MouseEvent('mousemove', {
                                clientX: rect.left + rect.width / 2 + (Math.random() - 0.5) * 20,
                                clientY: rect.top + rect.height / 2 + (Math.random() - 0.5) * 20,
                                bubbles: true
                            });
                            el.dispatchEvent(moveEvent);
                            
                            // Hover
                            const hoverEvent = new MouseEvent('mouseover', {
                                clientX: rect.left + rect.width / 2,
                                clientY: rect.top + rect.height / 2,
                                bubbles: true
                            });
                            el.dispatchEvent(hoverEvent);
                            
                            await new Promise(r => setTimeout(r, Math.random() * 800 + 200));
                        }
                    }
                    """,
                    
                    # Final pause
                    "await new Promise(r => setTimeout(r, 2000));",
                ],
                extraction_strategy=extraction_strategy
            )
            
            # Execute crawl with enhanced configuration
            print(f"   🤖 Using browser config: {browser_config.browser_type}, headless={browser_config.headless}")
            result = await crawler.arun(url=url, config=crawler_config)
            
            # Check for CAPTCHA in the response
            if result.success and result.extracted_content:
                content_lower = result.extracted_content.lower()
                captcha_indicators = ['show us your human side', 'prove you are human', 'captcha', 'start puzzle']
                
                if any(indicator in content_lower for indicator in captcha_indicators):
                    print(f"   🚫 CAPTCHA detected! Need to implement CAPTCHA solving or wait longer")
                    print(f"   💡 Suggestion: Try again with longer delays or different user agent")
                    
                    # Save CAPTCHA page for debugging
                    captcha_file = f"captcha_page_{current_date_str}.html"
                    with open(captcha_file, 'w', encoding='utf-8') as f:
                        f.write(result.extracted_content)
                    print(f"   📄 CAPTCHA page saved to {captcha_file}")
                    
                    # Force session rotation and longer delay
                    session_manager.rotate_session()
                    await human_like_delay(30, 60)  # Much longer delay
                    continue
            
            if result.success and result.extracted_content:
                try:
                    # Parse and validate the extracted data
                    raw_output = result.extracted_content
                    json_candidate = extract_first_json_object(raw_output)
                    to_parse = json_candidate if json_candidate else raw_output
                    daily_rate_data = json.loads(to_parse)
                    
                    if isinstance(daily_rate_data, dict):
                        validated_data = DailyRate.model_validate(daily_rate_data)
                        all_daily_rates.append(validated_data.dict())
                        
                        # Analysis of extraction
                        total_expected = len(hotel_profile.room_types)
                        total_extracted = len(validated_data.listings)
                        
                        # Count different statuses
                        with_prices = len([l for l in validated_data.listings 
                                         if l.price not in ["Not Listed", "Price Not Available", "Sold Out"]])
                        sold_out = len([l for l in validated_data.listings 
                                      if l.price == "Sold Out"])
                        not_listed = len([l for l in validated_data.listings 
                                        if l.price == "Not Listed"])
                        
                        print(f"   ✓ Extracted {total_extracted}/{total_expected} rooms")
                        print(f"      • With prices: {with_prices}")
                        print(f"      • Sold out: {sold_out}")
                        print(f"      • Not listed: {not_listed}")
                        print(f"   🛡️ Session stats: {session_manager.request_count} requests")
                        
                        # Warning if not all rooms found
                        if total_extracted < total_expected:
                            print(f"   ⚠️ Warning: Only found {total_extracted} of {total_expected} expected rooms")
                            missing = set(hotel_profile.room_types) - set([l.name for l in validated_data.listings])
                            if missing:
                                print(f"      Missing: {', '.join(missing)}")
                        
                    else:
                        print(f"   ✗ Unexpected data format: {type(daily_rate_data)}")
                        
                except (json.JSONDecodeError, ValidationError) as e:
                    print(f"   ✗ Failed to parse data: {e}")
                    print(f"      Raw output: {result.extracted_content[:200]}...")
                    
                    # Save debug output
                    debug_file = f"debug_{current_date_str}.txt"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(result.extracted_content)
                    print(f"      Debug output saved to {debug_file}")
            else:
                print(f"   ✗ Failed to scrape data")
                if result.error_message:
                    print(f"      Error: {result.error_message}")
                
                # Implement retry logic with different stealth parameters
                print(f"   🔄 Retrying with different stealth parameters...")
                session_manager.rotate_session()
                await human_like_delay(5, 10)  # Longer delay before retry
    
    # Create final data structure
    if all_daily_rates:
        final_data = HotelData(
            hotel_name=hotel_profile.hotel_name,
            daily_rates=all_daily_rates
        )
        
        # Summary statistics
        print(f"\n{'='*60}")
        print(f"📊 SCRAPING SUMMARY")
        print(f"{'='*60}")
        print(f"Hotel: {hotel_profile.hotel_name}")
        print(f"Days scraped: {len(all_daily_rates)}")
        
        # Calculate average prices per room type
        room_prices = {}
        for daily_rate in all_daily_rates:
            for listing in daily_rate['listings']:
                if listing['name'] not in room_prices:
                    room_prices[listing['name']] = []
                room_prices[listing['name']].append(listing['price'])
        
        print(f"\nRoom availability summary:")
        for room_name in hotel_profile.room_types:
            if room_name in room_prices:
                prices = room_prices[room_name]
                available = len([p for p in prices if p not in ["Sold Out", "Not Listed", "Price Not Available"]])
                print(f"  • {room_name}: {available}/{len(prices)} days available")
        
        # Save data if requested
        if save_data:
            filepath = save_results(final_data)
            print(f"\n✅ Scraping complete! Results saved to: {filepath}")
        
        return final_data
    else:
        print("\n❌ No data was extracted")
        return None

# ============= MAIN FUNCTION =============
async def main():
    """
    Main function to run the price scraping process.
    """
    # Configuration - modify these for your hotel
    HOTEL_NAME = "Minn Juso"
    START_DATE = date(2025, 8, 26)
    NUM_DAYS = 2
    
    # Load hotel profile from Phase 1
    print(f"📁 Loading profile for {HOTEL_NAME}...")
    hotel_profile = load_hotel_profile(HOTEL_NAME)
    
    if not hotel_profile:
        print("\n❌ Cannot proceed without hotel profile.")
        print("   Please run discover_rooms.py first to create the hotel profile.")
        return
    
    print(f"✅ Profile loaded successfully")
    print(f"   Last updated: {hotel_profile.last_updated}")
    print(f"   Room types: {len(hotel_profile.room_types)}")
    
    # Run price scraping
    result = await scrape_hotel_prices(
        hotel_profile=hotel_profile,
        start_date=START_DATE,
        num_days_to_scrape=NUM_DAYS,
        save_data=True
    )
    
    return result

if __name__ == "__main__":
    # Run the price scraping
    asyncio.run(main())