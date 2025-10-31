import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

# Base URL
BASE_URL = "https://www.carlogos.org"

# Create output directory
OUTPUT_DIR = "./logos/brands"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def scrape_page(url):
    """Scrape a single page and return list of logo data"""
    print(f"Scraping {url}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    logo_list = soup.find('ul', class_='logo-list')
    
    if not logo_list:
        print(f"No logo list found on {url}")
        return []
    
    logos = []
    for li in logo_list.find_all('li'):
        a_tag = li.find('a')
        img_tag = li.find('img')
        
        if a_tag and img_tag:
            # Get the brand name (text directly in the <a> tag, excluding labels)
            brand_name = a_tag.find(text=True, recursive=False).strip()
            img_url = urljoin(BASE_URL, img_tag['src'])
            
            logos.append({
                'brand': brand_name,
                'img_url': img_url
            })
    
    print(f"Found {len(logos)} logos on this page")
    return logos

def download_image(img_url, brand_name):
    """Download an image and save it with the brand name"""
    # Clean the brand name for use as filename
    filename = f"{brand_name.lower().replace(' ', '_')}.png"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    # Skip if already downloaded
    if os.path.exists(filepath):
        print(f"  {filename} already exists, skipping...")
        return True
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(img_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        print(f"  Downloaded: {filename}")
        return True
    except requests.RequestException as e:
        print(f"  Error downloading {img_url}: {e}")
        return False

def main():
    # URLs to scrape
    urls = ["https://www.carlogos.org/car-brands/"]
    urls.extend([f"https://www.carlogos.org/car-brands/page-{i}.html" for i in range(2, 9)])
    
    all_logos = []
    
    # Scrape all pages
    for url in urls:
        logos = scrape_page(url)
        all_logos.extend(logos)
        time.sleep(1)  # Be polite, wait between requests
    
    print(f"\n{'='*60}")
    print(f"Total logos found: {len(all_logos)}")
    print(f"{'='*60}\n")
    
    # Download all images
    print("Downloading images...\n")
    success_count = 0
    for i, logo in enumerate(all_logos, 1):
        print(f"[{i}/{len(all_logos)}] {logo['brand']}")
        if download_image(logo['img_url'], logo['brand']):
            success_count += 1
        time.sleep(0.5)  # Be polite between downloads
    
    print(f"\n{'='*60}")
    print(f"Download complete!")
    print(f"Successfully downloaded: {success_count}/{len(all_logos)} logos")
    print(f"Saved to: {OUTPUT_DIR}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()