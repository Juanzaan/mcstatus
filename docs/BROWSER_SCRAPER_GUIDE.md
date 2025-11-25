# 🌐 Browser Automation Scraper - Guide

## What It Does

The `browser_scraper.py` uses **Selenium** to scrape minecraft-server-list.com with a **real Chrome browser**, handling JavaScript-rendered content that basic HTTP requests can't access.

## Features

### 🔧 Technical
- **Auto-driver management** - Automatically downloads Chrome WebDriver
- **JavaScript execution** - Runs page scripts to extract dynamic content
- **Multiple extraction strategies**:
  1. BeautifulSoup HTML parsing
  2. Regex pattern matching for IPs/domains
  3. JavaScript DOM querying
- **Lazy-loading** - Scrolls pages to trigger content loading
- **Concurrent verification** - 30 threads for fast server checking

### 🎯 Filtering
- ✅ PREMIUM authentication only
- ✅ 500+ players minimum
- ✅ Active servers (responding to pings)

## Running

```bash
# Headless mode (no visible browser - faster)
echo y | python browser_scraper.py

# Visible browser (watch it work)
echo n | python browser_scraper.py
```

## Output Files

1. **browser_scraped_ips.txt** - All IPs found (Phase 1)
2. **browser_premium_500plus.json** - Verified servers (full details)
3. **browser_premium_ips.txt** - Just the IPs
4. **browser_premium_500plus.csv** - CSV format

## Progress

The script shows:
- **Phase 1:** Progress bar for page scraping
  - Updates every 10 pages with IP count
- **Phase 2:** Progress bar for server verification
  - Shows servers/second verification rate

## Expected Runtime

- **Phase 1:** ~10-20 minutes (500 pages)
  - Depends on internet speed
  - Browser automation is slower than HTTP
- **Phase 2:** Depends on IPs found
  - ~1 minute per 50 servers (with 30 threads)

## Requirements

- ✅ Chrome browser installed
- ✅ selenium package
- ✅ webdriver-manager package
- Good internet connection

## Why Browser Automation?

minecraft-server-list.com likely uses:
- JavaScript to load server data
- Lazy loading (infinite scroll)
- Dynamic content rendering
- Anti-scraping measures

Regular HTTP scrapers can't see this content. Selenium simulates a real browser, so it sees everything a human would see.

## Troubleshooting

### "ChromeDriver executable not found"
- Solution: webdriver-manager will auto-download it
- Manual: Install Chrome browser first

### No IPs found
- Website structure changed
- Try visible mode (echo n) to watch what happens
- Check browser_scraped_ips.txt after Phase 1

### Verification slow
- Normal for large datasets
- Reduce max_workers from 30 to 10 if needed
- Check network speed

## Alternative: Manual Approach

If automation fails:
1. Browse minecraft-server-list.com manually
2. Copy server IPs to `ips.txt`
3. Run: `python escaner_completo.py`

---

**Status:** Running in headless mode...
**Monitor:** Watch console for progress bars
