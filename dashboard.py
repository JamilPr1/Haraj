"""
Flask Dashboard for viewing scraped Haraj listings
"""

from flask import Flask, render_template, jsonify, send_file, request
import json
import os
from pathlib import Path
import csv
import io
import threading
import subprocess
import sys

# Get the directory where this script is located
_script_dir = Path(__file__).parent.absolute()
BASE_DIR = _script_dir

# Initialize Flask app with explicit template folder
_template_dir = BASE_DIR / "templates"
app = Flask(__name__, template_folder=str(_template_dir))

# Default data directory (relative to script location)
DATA_DIR = BASE_DIR / "scraped_data"
CONFIG_FILE = BASE_DIR / "scraper_config.json"

# Create data directory if it doesn't exist
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except:
    pass  # Continue even if directory creation fails

# Scraping status
scraping_status = {
    'is_running': False,
    'progress': 0,
    'total': 0,
    'current_listing': '',
    'error': None
}

def load_config():
    """Load scraper configuration (credentials) - Production ready"""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Validate config structure
                if isinstance(config, dict):
                    return {
                        'username': config.get('username', ''),
                        'password': config.get('password', '')
                    }
    except json.JSONDecodeError:
        # If file is corrupted, return empty config
        pass
    except PermissionError:
        print(f"Warning: Permission denied reading config file: {CONFIG_FILE}")
    except Exception as e:
        print(f"Warning: Error loading config: {e}")
    
    return {'username': '', 'password': ''}

def save_config(config):
    """Save scraper configuration (credentials) - Production ready"""
    try:
        # Ensure directory exists
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Validate config
        if not isinstance(config, dict):
            return False
        
        # Save config with proper error handling
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'username': config.get('username', ''),
                'password': config.get('password', '')
            }, f, indent=2)
        
        # Set restrictive permissions (Unix-like systems)
        try:
            import stat
            os.chmod(CONFIG_FILE, stat.S_IRUSR | stat.S_IWUSR)  # 600 - read/write for owner only
        except (AttributeError, OSError):
            # Windows doesn't support chmod the same way, that's okay
            pass
        
        return True
    except PermissionError:
        print(f"Error: Permission denied writing config file: {CONFIG_FILE}")
        return False
    except Exception as e:
        print(f"Error saving config: {e}")
        import traceback
        traceback.print_exc()
        return False

def load_listings():
    """Load listings from JSON file"""
    json_file = DATA_DIR / "listings.json"
    if json_file.exists():
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def get_listings_stats(listings):
    """Calculate statistics about listings"""
    if not listings:
        return {
            'total': 0,
            'with_contact': 0,
            'with_images': 0,
            'with_prices': 0,
            'cities': {},
            'categories': {}
        }
    
    stats = {
        'total': len(listings),
        'with_contact': 0,
        'with_images': 0,
        'with_prices': 0,
        'cities': {},
        'categories': {}
    }
    
    for listing in listings:
        # Contact info
        if listing.get('contact_info', {}).get('phone_numbers'):
            stats['with_contact'] += 1
        
        # Images
        if listing.get('images'):
            stats['with_images'] += len(listing.get('images', []))
        
        # Prices
        if listing.get('price'):
            stats['with_prices'] += 1
        
        # Cities
        city = listing.get('city', 'Unknown')
        stats['cities'][city] = stats['cities'].get(city, 0) + 1
        
        # Categories
        category = listing.get('category', 'Unknown')
        stats['categories'][category] = stats['categories'].get(category, 0) + 1
    
    return stats

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'base_dir': str(BASE_DIR),
        'data_dir': str(DATA_DIR),
        'template_dir': str(_template_dir)
    }), 200

@app.route('/api/chromedriver-check')
def chromedriver_check():
    """Check ChromeDriver availability for debugging"""
    import shutil
    import glob
    import os
    
    results = {
        'system_chromedriver': None,
        'nix_store_chromedrivers': [],
        'standard_locations': {},
        'chromium_found': False,
        'chromium_path': None
    }
    
    # Check PATH
    system_chromedriver = shutil.which('chromedriver')
    if system_chromedriver:
        results['system_chromedriver'] = system_chromedriver
        results['system_chromedriver_exists'] = os.path.exists(system_chromedriver)
        results['system_chromedriver_executable'] = os.access(system_chromedriver, os.X_OK) if system_chromedriver else False
    
    # Check nix store
    nix_matches = glob.glob('/nix/store/*/bin/chromedriver')
    results['nix_store_chromedrivers'] = nix_matches[:5]  # Limit to first 5
    
    # Check standard locations
    standard_paths = ['/usr/bin/chromedriver', '/usr/local/bin/chromedriver', '/opt/chromedriver/chromedriver']
    for path in standard_paths:
        results['standard_locations'][path] = {
            'exists': os.path.exists(path),
            'executable': os.access(path, os.X_OK) if os.path.exists(path) else False
        }
    
    # Check for Chromium
    chromium_paths = [
        shutil.which('chromium'),
        shutil.which('chromium-browser'),
        '/usr/bin/chromium',
        '/usr/bin/chromium-browser',
    ]
    for path in chromium_paths:
        if path and os.path.exists(path):
            results['chromium_found'] = True
            results['chromium_path'] = path
            break
    
    return jsonify(results), 200

@app.route('/')
def index():
    """Main dashboard page"""
    try:
        listings = load_listings()
        stats = get_listings_stats(listings)
        config = load_config()
        return render_template('dashboard.html', listings=listings, stats=stats, config=config)
    except Exception as e:
        import traceback
        error_msg = f"Error loading dashboard: {str(e)}\n\n{traceback.format_exc()}"
        return error_msg, 500

@app.route('/api/listings')
def api_listings():
    """API endpoint to get listings"""
    listings = load_listings()
    return jsonify(listings)

@app.route('/api/stats')
def api_stats():
    """API endpoint to get statistics"""
    listings = load_listings()
    stats = get_listings_stats(listings)
    return jsonify(stats)

@app.route('/listing/<listing_id>')
def view_listing(listing_id):
    """View individual listing details"""
    listings = load_listings()
    listing = next((l for l in listings if l.get('listing_id') == listing_id), None)
    
    if not listing:
        return "Listing not found", 404
    
    return render_template('listing_detail.html', listing=listing)

@app.route('/download/json')
def download_json():
    """Download listings as JSON"""
    json_file = DATA_DIR / "listings.json"
    if json_file.exists():
        return send_file(str(json_file), as_attachment=True, download_name='haraj_listings.json')
    return "No data file found", 404

@app.route('/download/csv')
def download_csv():
    """Download listings as CSV with contact information"""
    import re
    listings = load_listings()
    if not listings:
        return "No listings found", 404
    
    # Create CSV in memory
    output = io.StringIO()
    fieldnames = [
        'listing_id', 'title', 'description', 'price', 'city', 'location',
        'posted_time', 'seller_name', 'seller_url', 'category',
        'url', 'image_count', 'tags', 'phone_number', 'whatsapp_number', 'email'
    ]
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for listing in listings:
        contact_info = listing.get('contact_info', {})
        phone_numbers = contact_info.get('phone_numbers', [])
        phone_number = ', '.join(phone_numbers) if phone_numbers else ''
        
        # Extract WhatsApp number from link
        whatsapp_number = ''
        whatsapp_link = contact_info.get('whatsapp_link', '')
        if whatsapp_link:
            # Extract phone from WhatsApp link
            whatsapp_match = re.search(r'(?:wa\.me/|whatsapp.*phone=)(\d+)', whatsapp_link)
            if whatsapp_match:
                whatsapp_number = whatsapp_match.group(1)
                # Remove country code if present
                if whatsapp_number.startswith('966') and len(whatsapp_number) > 9:
                    whatsapp_number = whatsapp_number[3:]
        
        # Extract email
        emails = contact_info.get('emails', [])
        email = ', '.join(emails) if emails else ''
        
        row = {
            'listing_id': listing.get('listing_id', ''),
            'title': listing.get('title', ''),
            'description': listing.get('description', ''),
            'price': listing.get('price', ''),
            'city': listing.get('city', ''),
            'location': listing.get('location', ''),
            'posted_time': listing.get('posted_time', ''),
            'seller_name': listing.get('seller_name', ''),
            'seller_url': listing.get('seller_url', ''),
            'category': listing.get('category', ''),
            'url': listing.get('url', ''),
            'image_count': len(listing.get('images', [])),
            'tags': ', '.join(listing.get('tags', [])),
            'phone_number': phone_number,
            'whatsapp_number': whatsapp_number,
            'email': email
        }
        writer.writerow(row)
    
    # Create response
    output.seek(0)
    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8-sig'))
    mem.seek(0)
    
    return send_file(
        mem,
        mimetype='text/csv',
        as_attachment=True,
        download_name='haraj_listings.csv'
    )

def run_scraper(max_listings, category_url):
    """Run the scraper in background"""
    global scraping_status
    scraping_status['is_running'] = True
    scraping_status['progress'] = 0
    scraping_status['total'] = max_listings
    scraping_status['current_listing'] = 'Starting...'
    scraping_status['error'] = None
    
    try:
        # Import scraper (may fail in Vercel due to Selenium)
        try:
            from haraj_scraper_selenium import HarajScraperSelenium
        except ImportError as e:
            scraping_status['error'] = f"Selenium scraper not available in this environment: {str(e)}"
            scraping_status['is_running'] = False
            return
        
        # Load credentials from config
        config = load_config()
        username = config.get('username', '') or None
        password = config.get('password', '') or None
        
        try:
            scraper = HarajScraperSelenium(
                output_dir="scraped_data",
                download_images=False,
                headless=True,
                username=username,
                password=password
            )
        except Exception as e:
            scraping_status['error'] = f"Failed to initialize scraper: {str(e)}"
            scraping_status['is_running'] = False
            return
        
        try:
            # Find listing URLs first
            scraping_status['current_listing'] = 'Finding listings...'
            try:
                listing_urls = scraper.find_listing_urls(category_url, max_pages=10)
                listing_urls = listing_urls[:max_listings]
            except Exception as e:
                scraping_status['error'] = f"Failed to find listings: {str(e)}"
                scraping_status['is_running'] = False
                try:
                    scraper.close()
                except:
                    pass
                return
            
            scraping_status['total'] = len(listing_urls)
            scraping_status['current_listing'] = f'Found {len(listing_urls)} listings. Starting to scrape...'
            
            # Scrape each listing with progress updates
            all_listings = []
            for idx, url in enumerate(listing_urls, 1):
                if not scraping_status['is_running']:
                    break
                    
                scraping_status['progress'] = idx
                scraping_status['current_listing'] = f'Scraping listing {idx}/{len(listing_urls)}...'
                
                listing_data = scraper.scrape_listing(url)
                # Accept listing if it has at least URL or ID (even if other fields are missing)
                if listing_data and (listing_data.get('listing_id') or listing_data.get('url')):
                    all_listings.append(listing_data)
                else:
                    print(f"  Skipping listing - no data extracted: {url}")
            
            if all_listings:
                scraping_status['current_listing'] = 'Saving data...'
                try:
                    scraper.save_to_json(all_listings, "listings.json")
                    scraper.save_to_csv(all_listings, "listings.csv")
                except Exception as e:
                    scraping_status['error'] = f"Failed to save data: {str(e)}"
                scraping_status['progress'] = len(listing_urls)
                scraping_status['current_listing'] = f'Completed! Scraped {len(all_listings)} listings'
            else:
                if listing_urls:
                    scraping_status['error'] = f"Found {len(listing_urls)} listing URLs but failed to extract data. Check browser/network issues."
                else:
                    scraping_status['error'] = f"No listing URLs found. The website structure may have changed or the category URL is invalid: {category_url}"
        finally:
            try:
                scraper.close()
            except:
                pass
            
    except Exception as e:
        scraping_status['error'] = str(e)
        import traceback
        error_trace = traceback.format_exc()
        scraping_status['error'] = error_trace[:1000]  # Limit error length but show more
        print(f"Scraping error: {error_trace}")
    finally:
        scraping_status['is_running'] = False
        scraping_status['current_listing'] = 'Finished'

@app.route('/api/start-scraping', methods=['POST'])
def start_scraping():
    """Start scraping listings"""
    global scraping_status
    
    if scraping_status['is_running']:
        return jsonify({'error': 'Scraping is already running'}), 400
    
    try:
        data = request.get_json() or {}
        max_listings = int(data.get('max_listings', 10))
        category_url = data.get('category_url', 'https://haraj.com.sa/tags/حراج السيارات')
        
        if max_listings < 1 or max_listings > 100:
            return jsonify({'error': 'Number of listings must be between 1 and 100'}), 400
        
        # Start scraping in background thread
        thread = threading.Thread(target=run_scraper, args=(max_listings, category_url))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'status': 'started',
            'message': f'Scraping started for {max_listings} listings'
        })
    except Exception as e:
        return jsonify({'error': f'Failed to start scraping: {str(e)}'}), 500

@app.route('/api/scraping-status')
def scraping_status_api():
    """Get current scraping status"""
    return jsonify(scraping_status)

@app.route('/api/stop-scraping', methods=['POST'])
def stop_scraping():
    """Stop scraping (if possible)"""
    global scraping_status
    # Note: This is a simple implementation. For full control, you'd need process management
    scraping_status['is_running'] = False
    scraping_status['error'] = "Scraping stopped by user (may take a moment to fully halt current task)."
    return jsonify({'message': 'Scraping stop requested', 'status': scraping_status})

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get scraper settings (credentials)"""
    config = load_config()
    # Don't return password for security, only username
    return jsonify({
        'username': config.get('username', ''),
        'has_password': bool(config.get('password', ''))
    })

@app.route('/api/settings', methods=['POST'])
def save_settings():
    """Save scraper settings (credentials) - Production ready"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided', 'success': False}), 400
        
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        # Load existing config to preserve password if not changed
        config = load_config()
        
        # Only update password if provided (not empty)
        if password:
            config['password'] = password
        
        # Always update username
        config['username'] = username
        
        if save_config(config):
            return jsonify({
                'message': 'Settings saved successfully', 
                'success': True,
                'config_path': str(CONFIG_FILE)
            })
        else:
            return jsonify({
                'message': f'Failed to save settings. Check file permissions for: {CONFIG_FILE}', 
                'success': False,
                'error': 'File write error'
            }), 500
    except Exception as e:
        return jsonify({
            'message': f'Error saving settings: {str(e)}', 
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Create data directory if it doesn't exist (production ready)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Ensure config file directory exists
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    print("=" * 70)
    print("Haraj Scraper Dashboard")
    print("=" * 70)
    print(f"\nDashboard running at: http://localhost:5000")
    print(f"Data directory: {DATA_DIR.absolute()}")
    print("\nMake sure you have scraped some listings first!")
    print("Run: python haraj_scraper_selenium.py --category <URL> --max-listings 20")
    print("=" * 70 + "\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
