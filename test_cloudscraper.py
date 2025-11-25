import cloudscraper
import time

def test_scrape():
    print("Testing cloudscraper on minecraft-server-list.com...")
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )
    
    try:
        url = "https://minecraft-server-list.com/"
        print(f"Fetching {url}...")
        resp = scraper.get(url)
        
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            print("✓ Success! Page fetched.")
            print(f"Title in content: {'<title>' in resp.text}")
            if "Just a moment" in resp.text or "Un momento" in resp.text:
                print("❌ Still got Cloudflare challenge page.")
            else:
                print("✓ Bypassed Cloudflare!")
                print(f"Content length: {len(resp.text)}")
                with open('debug_valid_content.html', 'w', encoding='utf-8') as f:
                    f.write(resp.text)
                print("✓ Saved content to debug_valid_content.html")
        else:
            print(f"❌ Failed with status {resp.status_code}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_scrape()
