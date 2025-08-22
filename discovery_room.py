"""
Phase 1: Hotel Room Discovery Script
Discovers all unique room types for a hotel by sampling multiple dates.
"""

import asyncio
import os
import json
import random
from datetime import date, timedelta
from typing import Set, Dict, Optional
from pathlib import Path

from pydantic import BaseModel, Field
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
class HotelProfile(BaseModel):
    """Hotel profile with discovered room types."""
    hotel_name: str
    hotel_url: str
    room_types: list[str]
    last_updated: str
    metadata: Dict = Field(default_factory=dict)

# ============= UTILITY FUNCTIONS =============
def save_hotel_profile(profile: HotelProfile, profiles_dir: str = "hotel_profiles"):
    """Save hotel profile to JSON file."""
    Path(profiles_dir).mkdir(exist_ok=True)
    filename = f"{profiles_dir}/{profile.hotel_name.replace(' ', '_').lower()}_profile.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(profile.dict(), f, ensure_ascii=False, indent=2)
    print(f"✅ Hotel profile saved to {filename}")
    return filename

def load_hotel_profile(hotel_name: str, profiles_dir: str = "hotel_profiles") -> Optional[HotelProfile]:
    """Load hotel profile from JSON file."""
    filename = f"{profiles_dir}/{hotel_name.replace(' ', '_').lower()}_profile.json"
    if Path(filename).exists():
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return HotelProfile(**data)
    return None

# ============= DISCOVERY FUNCTION =============
async def discover_hotel_rooms(
    hotel_name: str,
    base_url: str,
    start_date: date,
    num_days_to_check: int = 5,
    sample_interval: int = 7,  # Days between samples
    target_selector: str = "div[data-stid='section-room-list']",
    save_profile: bool = True
) -> HotelProfile:
    """
    Discover all unique room types for a hotel by sampling multiple dates.
    
    Args:
        hotel_name: Name of the hotel
        base_url: Base URL of the hotel page
        start_date: Starting date for discovery
        num_days_to_check: Number of different dates to sample
        sample_interval: Days between each sample (default: weekly)
        target_selector: CSS selector for room list container
        save_profile: Whether to save the profile to disk
    
    Returns:
        HotelProfile with discovered room types
    """
    print(f"\n{'='*60}")
    print(f"🔍 DISCOVERING ROOM TYPES FOR {hotel_name}")
    print(f"{'='*60}\n")
    print(f"Configuration:")
    print(f"  - Sampling {num_days_to_check} dates")
    print(f"  - Interval: {sample_interval} days between samples")
    print(f"  - Starting from: {start_date}")
    print()
    
    discovered_rooms: Set[str] = set()
    sample_dates = []
    
    # Configure browser for stealth mode
    browser_config = BrowserConfig(
        browser_type="undetected",
        headless=False,  # Set to True for production
        extra_args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security"
        ]
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        for day_offset in range(num_days_to_check):
            # Calculate sample date with interval
            checkin_date = start_date + timedelta(days=day_offset * sample_interval)
            checkout_date = checkin_date + timedelta(days=1)
            
            checkin_str = checkin_date.strftime('%Y-%m-%d')
            checkout_str = checkout_date.strftime('%Y-%m-%d')
            sample_dates.append(checkin_str)
            
            # Build URL with dates
            url = f"{base_url}?chkin={checkin_str}&chkout={checkout_str}&x_pwa=1&rfrr=HSR"
            print(f"🔍 Sampling date {day_offset + 1}/{num_days_to_check}: {checkin_str}")
            
            # Random delay to mimic human behavior
            if day_offset > 0:  # Skip delay for first request
                delay = random.uniform(3, 7)
                print(f"   Waiting {delay:.1f} seconds...")
                await asyncio.sleep(delay)
            
            # Discovery prompt - generic and comprehensive
            discovery_prompt = f"""
            Extract ALL unique room types/names from this hotel listing page.
            
            Instructions:
            1. Find EVERY distinct room type mentioned anywhere on the page
            2. Look for room names in:
               - Headers and titles
               - Room cards or sections
               - Price listings
               - Dropdown menus or filters
            3. Extract the EXACT room name as it appears
            4. Include ALL rooms, even if:
               - Sold out
               - No price shown
               - Marked as unavailable
            5. Do NOT include:
               - Prices
               - Descriptions
               - Amenities
            
            Output format:
            Return ONLY a JSON array of unique room names, like:
            ["Room Type 1", "Room Type 2", "Room Type 3"]
            
            No explanations, no additional text, just the JSON array.
            """
            
            # Configure LLM for extraction
            llm_config = LLMConfig(
                provider="gemini/gemini-1.5-flash",
                api_token=os.getenv("GEMINI_API_KEY")
            )
            
            extraction_strategy = LLMExtractionStrategy(
                llm_config=llm_config,
                instruction=discovery_prompt,
                input_format="markdown",
                extraction_type="json"
            )
            
            # Configure crawler for this request
            crawler_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,  # Always get fresh data
                wait_until="load",
                wait_for=(
                    "js:() => {"
                    "const c = document.querySelector(\"div[data-stid='section-room-list']\");"
                    "return c !== null && c.children.length > 0;"
                    "}"
                ),
                page_timeout=60000,
                css_selector=target_selector,
                js_code=[
                    # Scroll to load dynamic content
                    "window.scrollTo(0, document.body.scrollHeight);",
                    "await new Promise(r => setTimeout(r, 1000));",
                    "window.scrollTo(0, 0);"
                ],
                extraction_strategy=extraction_strategy
            )
            
            # Execute crawl
            result = await crawler.arun(url=url, config=crawler_config)
            
            if result.success and result.extracted_content:
                try:
                    # Parse the room list
                    room_list = json.loads(result.extracted_content)
                    if isinstance(room_list, list):
                        current_sample_rooms = set(str(item) for item in room_list if isinstance(item, (str, dict)))
                        new_rooms = current_sample_rooms - discovered_rooms
                        discovered_rooms.update(current_sample_rooms)
                        
                        print(f"   ✓ Found {len(room_list)} rooms total")
                        if new_rooms:
                            print(f"   📦 New room types discovered:")
                            for room in sorted(new_rooms):
                                print(f"      + {room}")
                    else:
                        print(f"   ⚠️ Unexpected response format: {type(room_list)}")
                        
                except json.JSONDecodeError as e:
                    print(f"   ✗ Failed to parse results: {e}")
                    print(f"   Raw response: {result.extracted_content[:200]}...")
            else:
                print(f"   ✗ Failed to extract data")
                if result.error_message:
                    print(f"   Error: {result.error_message}")
    
    # Create hotel profile
    profile = HotelProfile(
        hotel_name=hotel_name,
        hotel_url=base_url,
        room_types=sorted(list(discovered_rooms)),
        last_updated=date.today().isoformat(),
        metadata={
            "discovery_dates_checked": num_days_to_check,
            "sample_dates": sample_dates,
            "sample_interval_days": sample_interval,
            "total_rooms_discovered": len(discovered_rooms)
        }
    )
    
    # Summary
    print(f"\n{'='*60}")
    print(f"📊 DISCOVERY COMPLETE")
    print(f"{'='*60}")
    print(f"Hotel: {hotel_name}")
    print(f"Total unique room types: {len(discovered_rooms)}")
    print(f"\nDiscovered room types:")
    for i, room in enumerate(sorted(discovered_rooms), 1):
        print(f"  {i}. {room}")
    
    # Save profile if requested
    if save_profile:
        filepath = save_hotel_profile(profile)
        print(f"\n💾 Profile saved: {filepath}")
    
    return profile

# ============= MAIN FUNCTION =============
async def main():
    """
    Main function to run the discovery process.
    """
    # Configuration - modify these for your hotel
    HOTEL_NAME = "Minn Juso"
    BASE_URL = "https://www.expedia.co.jp/en/Osaka-Hotels-Minn-Juso.h18638909.Hotel-Information"
    START_DATE = date(2025, 8, 26)
    
    # Check for existing profile
    existing_profile = load_hotel_profile(HOTEL_NAME)
    
    if existing_profile:
        print(f"\n📁 Found existing profile for {HOTEL_NAME}")
        print(f"   Last updated: {existing_profile.last_updated}")
        print(f"   Room types: {len(existing_profile.room_types)}")
        print(f"\n   Rooms: {', '.join(existing_profile.room_types)}")
        
        # Ask if user wants to update
        update = input("\n🔄 Do you want to update this profile? (y/n): ").lower().strip() == 'y'
        
        if not update:
            print("✅ Using existing profile")
            return existing_profile
    
    # Run discovery
    profile = await discover_hotel_rooms(
        hotel_name=HOTEL_NAME,
        base_url=BASE_URL,
        start_date=START_DATE,
        num_days_to_check=5,  # Sample 5 different dates
        sample_interval=7,     # Weekly intervals
        save_profile=True
    )
    
    return profile

if __name__ == "__main__":
    # Run the discovery
    asyncio.run(main())