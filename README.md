# Web Crawler POC - Hotel Price Scraper

A sophisticated web scraping tool designed to extract hotel room prices from Online Travel Agency (OTA) websites, specifically targeting Expedia. This proof-of-concept demonstrates advanced anti-bot detection evasion techniques while maintaining ethical scraping practices.

## 🚀 Features

- **Two-Phase Scraping**: Room discovery followed by price extraction
- **Advanced Anti-Bot Detection**: Comprehensive stealth measures to avoid CAPTCHA and blocks
- **Intelligent Session Management**: Automatic rotation and cleanup
- **Human-Like Behavior**: Realistic mouse movements, scrolling, and timing patterns
- **LLM-Powered Extraction**: Uses Google Gemini for intelligent data parsing
- **Configurable Parameters**: Easy customization for different hotels and date ranges

## 📋 Prerequisites

- Python 3.8 or higher
- Google Gemini API key
- Chrome browser (automatically managed by crawl4ai)

## 🛠️ Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Rana-SQA/Web-Crawler-POC.git
cd Web-Crawler-POC
```

### 2. Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Environment Setup

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit the `.env` file and add your Google Gemini API key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

**To get a Gemini API key:**

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key to your `.env` file

## 🏃‍♂️ How to Run

The application consists of two main phases that should be run sequentially:

### Phase 1: Room Discovery

Discovers all available room types for a hotel by sampling multiple dates.

```bash
python discovery_room.py
```

**What it does:**

- Visits the hotel page on multiple random dates
- Extracts all unique room types
- Saves the room profile to `hotel_profiles/`
- Creates a comprehensive hotel profile for Phase 2

### Phase 2: Price Scraping

Extracts actual room prices using the discovered room profile.

```bash
python scraper.py
```

**What it does:**

- Loads the hotel profile from Phase 1
- Scrapes prices for specified date ranges
- Implements advanced anti-bot measures
- Saves results to `scraped_data/`

## ⚙️ Configuration

### Hotel Configuration

Edit the target hotel in both scripts:

**In `discovery_room.py`:**

```python
# Configuration
HOTEL_NAME = "Your Hotel Name"
HOTEL_URL = "https://www.expedia.co.jp/h123456.Hotel-Name"
```

**In `scraper.py`:**

```python
# Configuration
HOTEL_NAME = "Your Hotel Name"
START_DATE = date(2025, 8, 26)
NUM_DAYS = 2
```

### Anti-Bot Settings

The scraper includes comprehensive anti-bot measures:

- **Browser Stealth**: 40+ Chrome flags to avoid detection
- **JavaScript Injection**: Removes automation indicators
- **Human Simulation**: Realistic mouse, keyboard, and scroll patterns
- **Session Management**: Automatic rotation after limits
- **CAPTCHA Detection**: Automatic detection and handling

See `ANTI_BOT_MEASURES.md` for detailed documentation.

## 📁 Project Structure

```
Web-Crawler-POC/
├── README.md                 # This file
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
├── .env                     # Your API keys (create this)
├── discovery_room.py        # Phase 1: Room discovery
├── scraper.py              # Phase 2: Price scraping
├── ANTI_BOT_MEASURES.md    # Anti-bot documentation
├── hotel_profiles/         # Discovered hotel profiles
│   └── minn_juso_profile.json
├── scraped_data/          # Extracted price data
│   └── minn_juso_prices_20250822.json
└── .gitignore            # Git ignore rules
```

## 📊 Output Data

### Hotel Profile (Phase 1)

```json
{
  "hotel_name": "Minn Juso",
  "hotel_url": "https://www.expedia.co.jp/...",
  "room_types": ["Standard Double Room", "Twin Room", "Superior Twin Room"],
  "last_updated": "2025-08-22T10:30:00",
  "metadata": {
    "total_dates_sampled": 5,
    "discovery_success_rate": 100.0
  }
}
```

### Price Data (Phase 2)

```json
{
  "hotel_name": "Minn Juso",
  "daily_rates": [
    {
      "date": "2025-08-26",
      "listings": [
        {
          "name": "Standard Double Room",
          "price": "¥12,500"
        },
        {
          "name": "Twin Room",
          "price": "¥14,800"
        }
      ]
    }
  ]
}
```

## 🛡️ Anti-Bot Features

This scraper implements state-of-the-art anti-detection measures:

### Browser Stealth

- Removes webdriver properties
- Spoofs browser fingerprints
- Disables automation indicators
- Uses realistic browser arguments

### Behavioral Simulation

- Human-like mouse movements
- Natural scrolling patterns
- Realistic timing delays
- Random keyboard events

### Session Management

- Automatic user agent rotation
- Session limits and rotation
- Browser data cleanup
- CAPTCHA detection and handling

### Network Patterns

- Realistic HTTP headers
- Proper cache control
- Natural request timing
- Session warm-up strategies

## 🔧 Troubleshooting

### Common Issues

1. **CAPTCHA Detection**

   ```
   🚫 CAPTCHA detected! Need to implement CAPTCHA solving or wait longer
   ```

   - The script automatically handles this by rotating sessions and waiting
   - Increase delay times in `human_like_delay()` if this persists

2. **Missing Gemini API Key**

   ```
   Error: GEMINI_API_KEY not found in environment
   ```

   - Ensure your `.env` file contains the API key
   - Check that the file is in the project root

3. **No Hotel Profile Found**

   ```
   ❌ Profile not found: hotel_profiles/hotel_name_profile.json
   ```

   - Run Phase 1 (`discovery_room.py`) first
   - Check that the hotel name matches in both scripts

4. **Browser Launch Issues**
   ```
   BrowserType.launch: Failed to launch browser
   ```
   - Ensure Chrome is installed
   - Try running with `headless=True` in browser config

### Debug Mode

Enable debug output by modifying the scripts:

```python
# In scraper.py, increase logging
print(f"Debug: {result.extracted_content[:500]}...")
```

## 📝 Usage Examples

### Basic Hotel Scraping

1. **Discover Rooms:**

   ```bash
   python discovery_room.py
   ```

2. **Scrape Prices:**
   ```bash
   python scraper.py
   ```

### Custom Date Range

Edit `scraper.py`:

```python
START_DATE = date(2025, 9, 1)
NUM_DAYS = 7  # Scrape one week
```

### Different Hotel

Edit both scripts with new hotel details:

```python
HOTEL_NAME = "New Hotel"
HOTEL_URL = "https://www.expedia.co.jp/h789.New-Hotel"
```

## ⚠️ Legal and Ethical Considerations

- **Respect robots.txt** when possible
- **Rate limiting** - Don't overwhelm servers
- **Terms of Service** - Ensure compliance with website ToS
- **Data Usage** - Use scraped data responsibly
- **Local Laws** - Comply with applicable regulations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/improvement`)
3. Commit changes (`git commit -am 'Add new feature'`)
4. Push to branch (`git push origin feature/improvement`)
5. Create a Pull Request

## 📄 License

This project is for educational and research purposes. Please ensure compliance with applicable laws and website terms of service when using this tool.

## 🔗 Dependencies

- **crawl4ai**: Advanced web crawling framework
- **pydantic**: Data validation and parsing
- **python-dotenv**: Environment variable management
- **google-generativeai**: LLM integration for data extraction

## 📞 Support

For issues, questions, or contributions:

- Create an issue on GitHub
- Check existing documentation in `ANTI_BOT_MEASURES.md`
- Review the troubleshooting section above

---

**Happy Scraping!** 🕷️🤖
