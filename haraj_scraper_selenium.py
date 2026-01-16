"""
Haraj.com.sa Web Scraper with Selenium Support
For JavaScript-heavy pages that require browser rendering
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import json
import os
import re
from urllib.parse import urljoin, urlparse
import time
from typing import Dict, List, Optional
import csv
from pathlib import Path
import requests
import random
import shutil
import glob


class HarajScraperSelenium:
    def __init__(self, output_dir: str = "scraped_data", download_images: bool = True, headless: bool = True, 
                 username: str = None, password: str = None):
        """
        Initialize the Haraj scraper with Selenium
        
        Args:
            output_dir: Directory to save scraped data and images
            download_images: Whether to download images
            headless: Run browser in headless mode
        """
        self.base_url = "https://haraj.com.sa"
        self.output_dir = Path(output_dir)
        self.images_dir = self.output_dir / "images"
        self.download_images = download_images
        
        # Create output directories
        self.output_dir.mkdir(exist_ok=True)
        if self.download_images:
            self.images_dir.mkdir(exist_ok=True)
        
        # Setup Chrome options
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-setuid-sandbox')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument('--lang=ar,en')
        
        # For Railway/Linux environments, try to use system Chrome if available
        # Nixpacks installs Chromium, so check for it first
        if os.path.exists('/nix/store'):
            # Nix environment - try to find chromium in nix store
            import subprocess
            try:
                chromium_path = subprocess.check_output(['which', 'chromium'], stderr=subprocess.DEVNULL).decode().strip()
                if chromium_path:
                    chrome_options.binary_location = chromium_path
            except:
                pass
        
        # Fallback to standard locations
        if not chrome_options.binary_location:
            if os.path.exists('/usr/bin/google-chrome'):
                chrome_options.binary_location = '/usr/bin/google-chrome'
            elif os.path.exists('/usr/bin/google-chrome-stable'):
                chrome_options.binary_location = '/usr/bin/google-chrome-stable'
            elif os.path.exists('/usr/bin/chromium'):
                chrome_options.binary_location = '/usr/bin/chromium'
            elif os.path.exists('/usr/bin/chromium-browser'):
                chrome_options.binary_location = '/usr/bin/chromium-browser'
        
        # User agents for rotation (ToS compliance)
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        ]
        
        # Set random user agent
        user_agent = random.choice(self.user_agents)
        chrome_options.add_argument(f'user-agent={user_agent}')
        
        # Initialize driver with better error handling for Railway
        # Try system chromedriver first (from nixpacks), then fallback to webdriver-manager
        chromedriver_paths = [
            '/usr/bin/chromedriver',
            '/usr/local/bin/chromedriver',
            '/nix/store/*/bin/chromedriver',  # Nix store location
        ]
        
        # Check for chromedriver in PATH
        import shutil
        system_chromedriver = shutil.which('chromedriver')
        if system_chromedriver:
            chromedriver_paths.append(system_chromedriver)
        
        # Add standard locations
        chromedriver_paths.extend([
            '/usr/bin/chromedriver',
            '/usr/local/bin/chromedriver',
            '/opt/chromedriver/chromedriver',
        ])
        
        # Check nix store for chromedriver
        nix_chromedriver_glob = '/nix/store/*/bin/chromedriver'
        nix_matches = glob.glob(nix_chromedriver_glob)
        if nix_matches:
            chromedriver_paths.extend(nix_matches)
        
        driver_found = False
        driver_path = None
        
        # Try system chromedriver first
        for path in chromedriver_paths:
            if os.path.exists(path):
                try:
                    # Make executable
                    os.chmod(path, 0o755)
                    # Test if it works (quick test) - but don't fail if test fails, just try to use it
                    try:
                        service = Service(path)
                        test_driver = webdriver.Chrome(service=service, options=chrome_options)
                        test_driver.quit()
                        print(f"ChromeDriver at {path} passed test")
                    except Exception as test_error:
                        print(f"ChromeDriver at {path} test failed, but will try to use it anyway: {test_error}")
                    
                    # Use this driver (even if test failed, it might work in actual use)
                    driver_path = path
                    driver_found = True
                    print(f"Using system ChromeDriver at: {path}")
                    break
                except Exception as path_error:
                    print(f"Error with ChromeDriver at {path}: {path_error}")
                    continue
        
        # If system chromedriver not found, use webdriver-manager
        if not driver_found:
            try:
                print("System ChromeDriver not found, using webdriver-manager...")
                print("WARNING: webdriver-manager ChromeDriver may have dependency issues on Railway.")
                print("Make sure chromedriver is in nixpacks.toml nixPkgs list.")
                
                driver_path = ChromeDriverManager().install()
                # Make sure driver is executable (important for Linux)
                if os.path.exists(driver_path):
                    # Set executable permissions
                    os.chmod(driver_path, 0o755)
                    # Also make sure parent directories are accessible
                    driver_dir = os.path.dirname(driver_path)
                    depth = 0
                    while driver_dir and driver_dir != '/' and depth < 5:
                        if os.path.exists(driver_dir):
                            try:
                                os.chmod(driver_dir, 0o755)
                            except:
                                pass
                        driver_dir = os.path.dirname(driver_dir)
                        depth += 1
                    
                    # Verify the file is actually executable
                    if not os.access(driver_path, os.X_OK):
                        raise Exception(f"ChromeDriver at {driver_path} is not executable even after chmod")
                    
                    # Try to verify it can run (check if it's a valid binary)
                    try:
                        import subprocess
                        result = subprocess.run([driver_path, '--version'], 
                                              capture_output=True, 
                                              timeout=5,
                                              stderr=subprocess.DEVNULL)
                        if result.returncode != 0:
                            print(f"Warning: ChromeDriver version check failed, but continuing...")
                    except Exception as version_check_error:
                        print(f"Warning: Could not verify ChromeDriver version: {version_check_error}")
                    
                    driver_found = True
                    print(f"Using webdriver-manager ChromeDriver at: {driver_path}")
                else:
                    raise Exception(f"ChromeDriver path from webdriver-manager does not exist: {driver_path}")
            except Exception as wdm_error:
                error_msg = f"Failed to initialize ChromeDriver.\n"
                error_msg += f"System driver not found, and webdriver-manager failed: {str(wdm_error)}\n"
                error_msg += f"\nTroubleshooting:\n"
                error_msg += f"1. Make sure 'chromedriver' is in nixpacks.toml nixPkgs list\n"
                error_msg += f"2. Make sure 'chromium' is in nixpacks.toml nixPkgs list\n"
                error_msg += f"3. Check Railway logs for chromedriver installation\n"
                error_msg += f"4. Status code 127 usually means missing shared libraries (libnss3, etc.)"
                raise Exception(error_msg)
        
        # Initialize the actual driver
        if driver_path and driver_found:
            try:
                service = Service(driver_path)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                print(f"ChromeDriver initialized successfully at: {driver_path}")
            except Exception as init_error:
                error_msg = f"Failed to start ChromeDriver at {driver_path}: {str(init_error)}"
                error_msg += "\nMake sure:"
                error_msg += "\n1. Chrome/Chromium is installed (check nixpacks.toml)"
                error_msg += "\n2. ChromeDriver is installed (check nixpacks.toml)"
                error_msg += "\n3. All required libraries are installed (libnss3, libatk-bridge2.0-0, etc.)"
                raise Exception(error_msg)
        else:
            raise Exception("ChromeDriver path not found or not initialized")
        self.driver.implicitly_wait(3)  # Reduced for speed
        
        # Session for downloading images
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': user_agent,
        })
        
        # Counter for ToS compliance (change behavior every 10 listings)
        self.listing_count = 0
        
        # Login credentials (optional)
        self.username = username
        self.password = password
        self.is_logged_in = False
        
        # Login if credentials provided
        if self.username and self.password:
            self.login()
    
    def _apply_tos_compliance_measures(self):
        """
        Apply ToS-compliant measures after every 10 listings - ULTRA OPTIMIZED
        """
        if self.listing_count > 0 and self.listing_count % 10 == 0:
            print(f"\n[ToS Compliance] Applied measures after {self.listing_count} listings...")
            
            # Minimal delay (5-10 seconds) for maximum speed while still being respectful
            delay = random.randint(5, 10)
            print(f"  - Extended delay: {delay} seconds")
            time.sleep(delay)
            
            # Clear cookies every 20 listings
            if self.listing_count % 20 == 0:
                self.driver.delete_all_cookies()
                print("  - Cookies cleared")
            
            # Rotate user agent by updating driver options
            if self.listing_count % 30 == 0:
                user_agent = random.choice(self.user_agents)
                self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": user_agent})
                print("  - User-Agent rotated")
            
            print("  - Continuing scraping...\n")
    
    def login(self):
        """Login to Haraj.com.sa if credentials are provided"""
        if not self.username or not self.password:
            return False
        
        try:
            print("Attempting to login to Haraj.com.sa...")
            self.driver.get("https://haraj.com.sa")
            time.sleep(2)
            
            # Look for login button/link
            login_selectors = [
                "//a[contains(text(), 'تسجيل الدخول') or contains(text(), 'دخول')]",
                "//button[contains(text(), 'تسجيل الدخول') or contains(text(), 'دخول')]",
                "//a[contains(@href, 'login') or contains(@href, 'signin')]",
            ]
            
            login_button = None
            for selector in login_selectors:
                try:
                    buttons = self.driver.find_elements(By.XPATH, selector)
                    if buttons:
                        login_button = buttons[0]
                        break
                except:
                    continue
            
            if not login_button:
                print("  Warning: Could not find login button. Proceeding without login.")
                return False
            
            # Click login button
            login_button.click()
            time.sleep(2)
            
            # Find username/email field
            username_fields = self.driver.find_elements(By.XPATH, 
                "//input[@type='text' or @type='email' or @name='username' or @name='email' or @id='username' or @id='email']")
            if not username_fields:
                username_fields = self.driver.find_elements(By.XPATH, "//input[contains(@placeholder, 'البريد') or contains(@placeholder, 'اسم')]")
            
            # Find password field
            password_fields = self.driver.find_elements(By.XPATH, 
                "//input[@type='password']")
            
            if username_fields and password_fields:
                username_fields[0].send_keys(self.username)
                time.sleep(0.5)
                password_fields[0].send_keys(self.password)
                time.sleep(0.5)
                
                # Find and click submit button
                submit_buttons = self.driver.find_elements(By.XPATH,
                    "//button[@type='submit'] | //button[contains(text(), 'دخول')] | //input[@type='submit']")
                if submit_buttons:
                    submit_buttons[0].click()
                    time.sleep(3)
                    
                    # Check if login was successful
                    # Look for user profile or logout button
                    profile_indicators = self.driver.find_elements(By.XPATH,
                        "//*[contains(text(), 'حسابي') or contains(text(), 'تسجيل الخروج') or contains(@class, 'user')]")
                    
                    if profile_indicators or 'haraj.com.sa' in self.driver.current_url:
                        self.is_logged_in = True
                        print("  ✓ Login successful!")
                        return True
                    else:
                        print("  ✗ Login may have failed. Check credentials.")
                        return False
                else:
                    print("  ✗ Could not find submit button")
                    return False
            else:
                print("  ✗ Could not find login form fields")
                return False
                
        except Exception as e:
            print(f"  ✗ Login error: {e}")
            return False
    
    def get_page(self, url: str) -> Optional[BeautifulSoup]:
        """Load page with Selenium and return BeautifulSoup - ULTRA OPTIMIZED"""
        try:
            self.driver.get(url)
            time.sleep(0.5)  # Minimal wait - just enough for initial load
            
            # Quick check for body (no long wait)
            try:
                WebDriverWait(self.driver, 1).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except:
                pass
            
            # Get page source immediately - no scrolling needed for basic extraction
            page_source = self.driver.page_source
            return BeautifulSoup(page_source, 'html.parser')
        except Exception as e:
            print(f"Error loading {url}: {e}")
            return None
    
    def extract_listing_id(self, url: str) -> Optional[str]:
        """Extract listing ID from URL"""
        match = re.search(r'/(\d+)/', url)
        return match.group(1) if match else None
    
    def extract_listing_details(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract all details from a listing page"""
        listing_data = {
            'url': url,
            'listing_id': self.extract_listing_id(url),
            'title': '',
            'description': '',
            'price': '',
            'location': '',
            'city': '',
            'posted_time': '',
            'seller_name': '',
            'seller_url': '',
            'category': '',
            'tags': [],
            'images': [],
            'contact_info': {},
        }
        
        if not soup:
            return listing_data
        
        # Extract title - try multiple methods
        title_elem = soup.find('h1')
        if title_elem:
            listing_data['title'] = title_elem.get_text(strip=True)
        else:
            # Try using Selenium to find title
            try:
                title_elements = self.driver.find_elements(By.TAG_NAME, "h1")
                if title_elements:
                    listing_data['title'] = title_elements[0].text.strip()
                else:
                    # Try data-testid
                    title_elements = self.driver.find_elements(By.XPATH, "//*[@data-testid='post_title']")
                    if title_elements:
                        listing_data['title'] = title_elements[0].text.strip()
            except:
                pass
        
        # Extract description/article content - try multiple methods
        article = soup.find('article')
        if article:
            listing_data['description'] = article.get_text(strip=True)
        else:
            # Try using Selenium
            try:
                article_elements = self.driver.find_elements(By.XPATH, "//article[@data-testid='post-article']")
                if article_elements:
                    listing_data['description'] = article_elements[0].text.strip()
                else:
                    # Try any article tag
                    article_elements = self.driver.find_elements(By.TAG_NAME, "article")
                    if article_elements:
                        listing_data['description'] = article_elements[0].text.strip()
            except:
                pass
        
        # Try to find price using Selenium (more reliable for dynamic content)
        try:
            price_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'ريال') or contains(text(), 'ر.س')]")
            for elem in price_elements:
                text = elem.text.strip()
                if re.search(r'\d+', text):
                    listing_data['price'] = text
                    break
        except:
            pass
        
        # Extract location/city
        try:
            city_elements = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/city/')]")
            if city_elements:
                listing_data['city'] = city_elements[0].text.strip()
                listing_data['location'] = listing_data['city']
        except:
            pass
        
        # Extract posted time
        try:
            time_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'الآن') or contains(text(), 'منذ')]")
            if time_elements:
                listing_data['posted_time'] = time_elements[0].text.strip()
        except:
            pass
        
        # Extract seller information
        try:
            seller_elements = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/users/')]")
            if seller_elements:
                listing_data['seller_name'] = seller_elements[0].text.strip()
                listing_data['seller_url'] = urljoin(self.base_url, seller_elements[0].get_attribute('href'))
        except:
            pass
        
        # Extract category and tags
        try:
            tag_elements = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/tags/')]")
            tags = []
            for elem in tag_elements:
                tag_text = elem.text.strip()
                if tag_text:
                    tags.append(tag_text)
            listing_data['tags'] = tags
            if tags:
                listing_data['category'] = tags[0]
        except:
            pass
        
        # Extract images - use Selenium to find all images
        try:
            img_elements = self.driver.find_elements(By.TAG_NAME, "img")
            images = []
            for img in img_elements:
                src = img.get_attribute('src') or img.get_attribute('data-src') or img.get_attribute('data-lazy-src')
                if src:
                    # Filter out icons, logos, and small images
                    if any(exclude in src.lower() for exclude in ['icon', 'logo', 'badge', 'avatar']):
                        continue
                    # Make absolute URL
                    img_url = urljoin(self.base_url, src)
                    if img_url not in images:
                        images.append(img_url)
            listing_data['images'] = images
        except Exception as e:
            print(f"Error extracting images: {e}")
        
        # Extract contact information by clicking contact button - ULTRA OPTIMIZED
        try:
            # Find contact button - try multiple selectors for better detection
            contact_buttons = self.driver.find_elements(By.XPATH, 
                "//button[contains(@data-testid, 'contact') or contains(text(), 'تواصل') or contains(@class, 'contact')] | " +
                "//a[contains(@class, 'contact') or contains(text(), 'تواصل')] | " +
                "//*[@role='button' and (contains(text(), 'تواصل') or contains(@data-testid, 'contact'))]")
            
            if not contact_buttons:
                # Try alternative: look for any clickable element with contact-related text
                contact_buttons = self.driver.find_elements(By.XPATH, 
                    "//*[contains(text(), 'تواصل') and (self::button or self::a or @role='button')]")
            
            if contact_buttons:
                listing_data['contact_info']['has_contact_button'] = True
                
                # Click the contact button to reveal contact info
                try:
                    # Click directly without scrolling (faster)
                    self.driver.execute_script("arguments[0].click();", contact_buttons[0])
                    time.sleep(0.5)  # Minimal wait for modal to appear
                    
                    # Check if login prompt appeared instead of contact info
                    login_prompts = self.driver.find_elements(By.XPATH,
                        "//*[contains(text(), 'تسجيل الدخول') or contains(text(), 'يجب تسجيل الدخول') or contains(text(), 'login')]")
                    if login_prompts and not self.is_logged_in:
                        print("  ⚠️  Login required to view contact information")
                        listing_data['contact_info']['login_required'] = True
                        # Try to close the login prompt
                        try:
                            self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                            time.sleep(0.2)
                        except:
                            pass
                        return listing_data
                    
                    # Wait for modal/contact info to appear - faster detection
                    try:
                        WebDriverWait(self.driver, 1.5).until(
                            EC.any_of(
                                EC.presence_of_element_located((By.XPATH, "//*[contains(@class, 'modal') or contains(@class, 'dialog') or contains(@role, 'dialog')]")),
                                EC.presence_of_element_located((By.XPATH, "//a[starts-with(@href, 'tel:')]")),
                                EC.presence_of_element_located((By.XPATH, "//*[contains(@class, 'phone') or contains(@class, 'contact-info')]"))
                            )
                        )
                    except:
                        time.sleep(0.3)  # Brief wait if modal detection fails
                    
                    # Extract seller name and phone from contact modal
                    seller_phone = None
                    seller_name_from_contact = None
                    
                    # Find the contact modal/dialog container
                    modal_container = None
                    try:
                        # Try to find modal by various selectors
                        modal_selectors = [
                            "//div[contains(@class, 'modal') or contains(@class, 'dialog') or contains(@role, 'dialog')]",
                            "//div[contains(@data-testid, 'contact') or contains(@data-testid, 'modal')]",
                            "//*[contains(@class, 'contact-info') or contains(@class, 'contact-details')]",
                        ]
                        for selector in modal_selectors:
                            modals = self.driver.find_elements(By.XPATH, selector)
                            if modals:
                                modal_container = modals[0]
                                break
                    except:
                        pass
                    
                    # Method 1: Extract from tel: links (most reliable for phone)
                    try:
                        phone_links = self.driver.find_elements(By.XPATH, "//a[starts-with(@href, 'tel:')]")
                        if phone_links:
                            href = phone_links[0].get_attribute('href')
                            phone_match = re.search(r'tel:[\+]?(\d+)', href)
                            if phone_match:
                                phone = phone_match.group(1)
                                # Remove country code (966)
                                if phone.startswith('966') and len(phone) > 9:
                                    phone = phone[3:]
                                elif phone.startswith('+966'):
                                    phone = phone[4:]
                                if len(phone) >= 9:
                                    seller_phone = phone
                    except:
                        pass
                    
                    # Method 2: Extract from modal container text (phone and name)
                    if modal_container:
                        try:
                            modal_text = modal_container.text
                            
                            # Extract seller name - look for name patterns in modal
                            # Usually appears before phone number
                            name_patterns = [
                                r'([أ-ي\s]{3,})',  # Arabic name (3+ Arabic chars)
                                r'([A-Za-z\s]{3,})',  # English name
                            ]
                            for pattern in name_patterns:
                                name_matches = re.findall(pattern, modal_text)
                                if name_matches:
                                    # Take first reasonable name (not too long, not phone-like)
                                    for match in name_matches[:3]:
                                        name = match.strip()
                                        if 3 <= len(name) <= 50 and not re.match(r'^\d+$', name):
                                            seller_name_from_contact = name
                                            break
                                if seller_name_from_contact:
                                    break
                            
                            # Extract phone from modal text
                            if not seller_phone:
                                phone_patterns = [
                                    r'(\+966[\d\s-]{9,})',  # +966 format
                                    r'(05[\d\s-]{9,})',     # 05 format (9 digits after 05)
                                    r'(5[\d\s-]{9,})',      # 5 format
                                ]
                                for pattern in phone_patterns:
                                    matches = re.findall(pattern, modal_text)
                                    if matches:
                                        phone = re.sub(r'[\s-]', '', str(matches[0]))
                                        # Remove country code
                                        if phone.startswith('966') and len(phone) > 9:
                                            phone = phone[3:]
                                        elif phone.startswith('+966'):
                                            phone = phone[4:]
                                        if len(phone) >= 9:
                                            seller_phone = phone
                                            break
                        except:
                            pass
                    
                    # Method 3: Look for phone in specific elements within modal
                    if not seller_phone and modal_container:
                        try:
                            phone_elements = modal_container.find_elements(By.XPATH, 
                                ".//*[contains(text(), '05') or contains(text(), '+966') or contains(text(), '5')]")
                            
                            for elem in phone_elements[:3]:
                                text = elem.text.strip()
                                phone_match = re.search(r'(\+?966[\d\s-]{9,}|05[\d\s-]{9,}|5[\d\s-]{9,})', text)
                                if phone_match:
                                    phone = re.sub(r'[\s-]', '', phone_match.group(1))
                                    if phone.startswith('966') and len(phone) > 9:
                                        phone = phone[3:]
                                    elif phone.startswith('+966'):
                                        phone = phone[4:]
                                    if len(phone) >= 9:
                                        seller_phone = phone
                                        break
                        except:
                            pass
                    
                    # Store extracted contact info
                    if seller_phone:
                        listing_data['contact_info']['phone_numbers'] = [seller_phone]
                        listing_data['contact_info']['contact_extracted'] = True
                        listing_data['contact_info']['seller_phone'] = seller_phone
                    
                    # Store seller name from contact if found
                    if seller_name_from_contact:
                        listing_data['contact_info']['seller_name'] = seller_name_from_contact
                        if not listing_data.get('seller_name'):
                            listing_data['seller_name'] = seller_name_from_contact
                    
                    # Try to find WhatsApp link in modal
                    try:
                        whatsapp_links = self.driver.find_elements(By.XPATH, 
                            "//a[contains(@href, 'wa.me') or contains(@href, 'whatsapp')]")
                        if whatsapp_links:
                            listing_data['contact_info']['whatsapp_available'] = True
                            listing_data['contact_info']['whatsapp_link'] = whatsapp_links[0].get_attribute('href')
                    except:
                        pass
                    
                    # Close modal quickly (use ESC key or close button)
                    try:
                        # Try ESC key first (fastest)
                        self.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        time.sleep(0.1)
                    except:
                        # Fallback to close button
                        try:
                            close_buttons = self.driver.find_elements(By.XPATH, 
                                "//button[contains(@class, 'close') or contains(@aria-label, 'close') or contains(text(), '×')]")
                            if close_buttons:
                                close_buttons[0].click()
                                time.sleep(0.1)
                        except:
                            pass
                        
                except Exception as e:
                    print(f"  Warning: Could not extract contact info: {e}")
                    
        except Exception as e:
            print(f"  Warning: Error extracting contact info: {e}")
        
        return listing_data
    
    def download_image(self, img_url: str, listing_id: str, index: int) -> Optional[str]:
        """Download an image and return local path"""
        try:
            response = self.session.get(img_url, timeout=30, stream=True)
            response.raise_for_status()
            
            # Determine file extension
            content_type = response.headers.get('content-type', '')
            ext = 'jpg'
            if 'png' in content_type:
                ext = 'png'
            elif 'webp' in content_type:
                ext = 'webp'
            elif 'gif' in content_type:
                ext = 'gif'
            
            # Generate filename
            filename = f"{listing_id}_{index}.{ext}"
            filepath = self.images_dir / filename
            
            # Save image
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return str(filepath)
        except Exception as e:
            print(f"Error downloading image {img_url}: {e}")
            return None
    
    def scrape_listing(self, listing_url: str) -> Dict:
        """Scrape a single listing"""
        # Apply ToS compliance measures every 10 listings
        self._apply_tos_compliance_measures()
        
        print(f"Scraping: {listing_url}")
        
        # Minimal delay for speed (0.2-0.5 seconds)
        delay = random.uniform(0.2, 0.5)
        time.sleep(delay)
        
        soup = self.get_page(listing_url)
        if not soup:
            self.listing_count += 1
            print(f"  Warning: Failed to load page for {listing_url}")
            return {}
        
        listing_data = self.extract_listing_details(soup, listing_url)
        
        # Validate that we got at least some data
        if not listing_data.get('listing_id') and not listing_data.get('title'):
            print(f"  Warning: No data extracted from {listing_url}")
            # Try to get at least the URL
            listing_data['url'] = listing_url
            listing_data['listing_id'] = self.extract_listing_id(listing_url)
        
        # Download images if enabled
        if self.download_images and listing_data.get('images'):
            downloaded_images = []
            for idx, img_url in enumerate(listing_data['images']):
                local_path = self.download_image(img_url, listing_data.get('listing_id', 'unknown'), idx)
                if local_path:
                    downloaded_images.append({
                        'url': img_url,
                        'local_path': local_path
                    })
                # Minimal delay between image downloads
                time.sleep(random.uniform(0.1, 0.3))
            
            listing_data['downloaded_images'] = downloaded_images
        
        # Increment counter
        self.listing_count += 1
        
        return listing_data
    
    def find_listing_urls(self, category_url: str, max_pages: int = 10) -> List[str]:
        """Find all listing URLs from a category page"""
        listing_urls = []
        
        for page in range(1, max_pages + 1):
            if page == 1:
                url = category_url
            else:
                if '?' in category_url:
                    url = f"{category_url}&page={page}"
                else:
                    url = f"{category_url}?page={page}"
            
            print(f"Fetching listings from page {page}...")
            try:
                self.driver.get(url)
                time.sleep(0.8)  # Minimal wait
            except Exception as e:
                print(f"Error loading page {page}: {e}")
                break
            
            # Quick check for body
            try:
                WebDriverWait(self.driver, 2).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except:
                pass
            
            # Quick scroll to load content (minimal wait)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(0.4)  # Minimal wait
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(0.2)  # Minimal wait
            
            # Find all listing links - improved selector
            try:
                # Try multiple selectors to find listing links
                page_urls = []
                
                # Method 1: Find all links and filter by pattern
                all_links = self.driver.find_elements(By.TAG_NAME, "a")
                for link in all_links:
                    try:
                        href = link.get_attribute('href')
                        if href:
                            # Pattern: /11173528712/title/ or /11173528712/encoded-title/
                            if re.search(r'/\d{10,}/[^/]+/?$', href) and 'haraj.com.sa' in href:
                                # Clean and normalize URL
                                if href.endswith('/'):
                                    clean_url = href
                                else:
                                    clean_url = href + '/'
                                
                                if clean_url not in listing_urls and clean_url not in page_urls:
                                    page_urls.append(clean_url)
                    except:
                        continue
                
                # Method 2: Try finding links with data-testid or specific classes
                if not page_urls:
                    try:
                        # Look for post cards or listing containers
                        post_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/') and string-length(@href) > 20]")
                        for link in post_links:
                            href = link.get_attribute('href')
                            if href and re.search(r'/\d{10,}/', href) and 'haraj.com.sa' in href:
                                if href.endswith('/'):
                                    clean_url = href
                                else:
                                    clean_url = href + '/'
                                if clean_url not in listing_urls and clean_url not in page_urls:
                                    page_urls.append(clean_url)
                    except:
                        pass
                
                # Remove duplicates
                page_urls = list(dict.fromkeys(page_urls))
                
                if not page_urls:
                    print(f"No more listings found on page {page}")
                    # Try one more scroll and wait
                    if page == 1:
                        time.sleep(3)
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(2)
                        # Retry once
                        all_links = self.driver.find_elements(By.TAG_NAME, "a")
                        for link in all_links:
                            try:
                                href = link.get_attribute('href')
                                if href and re.search(r'/\d{10,}/[^/]+/?$', href) and 'haraj.com.sa' in href:
                                    if href.endswith('/'):
                                        clean_url = href
                                    else:
                                        clean_url = href + '/'
                                    if clean_url not in listing_urls and clean_url not in page_urls:
                                        page_urls.append(clean_url)
                            except:
                                continue
                        page_urls = list(dict.fromkeys(page_urls))
                    
                    if not page_urls:
                        break
                
                listing_urls.extend(page_urls)
                print(f"Found {len(page_urls)} listings on page {page}")
            except Exception as e:
                print(f"Error finding listings on page {page}: {e}")
                import traceback
                traceback.print_exc()
                break
            
            time.sleep(0.5)  # Reduced delay between pages
        
        return listing_urls
    
    def scrape_category(self, category_url: str, max_listings: int = 50, max_pages: int = 10) -> List[Dict]:
        """Scrape all listings from a category"""
        print(f"Scraping category: {category_url}")
        
        listing_urls = self.find_listing_urls(category_url, max_pages)
        listing_urls = listing_urls[:max_listings]
        
        print(f"Found {len(listing_urls)} listings to scrape")
        
        all_listings = []
        for idx, url in enumerate(listing_urls, 1):
            print(f"\n[{idx}/{len(listing_urls)}]")
            listing_data = self.scrape_listing(url)
            if listing_data:
                all_listings.append(listing_data)
            
            # Minimal delay between listings for maximum speed
            if idx < len(listing_urls):
                time.sleep(random.uniform(0.1, 0.3))  # Ultra fast
        
        return all_listings
    
    def save_to_json(self, data: List[Dict], filename: str = "listings.json"):
        """Save scraped data to JSON file"""
        filepath = self.output_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\nData saved to {filepath}")
    
    def save_to_csv(self, data: List[Dict], filename: str = "listings.csv"):
        """Save scraped data to CSV file with contact information"""
        if not data:
            return
        
        filepath = self.output_dir / filename
        fieldnames = [
            'listing_id', 'title', 'description', 'price', 'city', 'location',
            'posted_time', 'seller_name', 'seller_url', 'category',
            'url', 'image_count', 'tags',
            'phone_number', 'whatsapp_number', 'email'
        ]
        
        with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for listing in data:
                # Extract contact information
                contact_info = listing.get('contact_info', {})
                phone_numbers = contact_info.get('phone_numbers', [])
                phone_number = ', '.join(phone_numbers) if phone_numbers else ''
                
                # Extract WhatsApp number from link
                whatsapp_number = ''
                whatsapp_link = contact_info.get('whatsapp_link', '')
                if whatsapp_link:
                    # Extract phone from WhatsApp link (e.g., wa.me/966501234567 or whatsapp://send?phone=966501234567)
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
        
        print(f"CSV saved to {filepath}")
    
    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()


def main():
    """Main function to run the scraper"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Haraj.com.sa Web Scraper (Selenium)')
    parser.add_argument('--url', type=str, help='Single listing URL to scrape')
    parser.add_argument('--category', type=str, help='Category URL to scrape multiple listings')
    parser.add_argument('--max-listings', type=int, default=50, help='Maximum number of listings to scrape')
    parser.add_argument('--max-pages', type=int, default=10, help='Maximum number of pages to scrape')
    parser.add_argument('--no-images', action='store_true', help='Skip downloading images')
    parser.add_argument('--output-dir', type=str, default='scraped_data', help='Output directory')
    parser.add_argument('--no-headless', action='store_true', help='Run browser in visible mode')
    
    args = parser.parse_args()
    
    # Initialize scraper
    scraper = HarajScraperSelenium(
        output_dir=args.output_dir,
        download_images=not args.no_images,
        headless=not args.no_headless
    )
    
    try:
        if args.url:
            listing_data = scraper.scrape_listing(args.url)
            if listing_data:
                scraper.save_to_json([listing_data], "single_listing.json")
                scraper.save_to_csv([listing_data], "single_listing.csv")
                print("\nScraping completed!")
        
        elif args.category:
            listings = scraper.scrape_category(
                args.category,
                max_listings=args.max_listings,
                max_pages=args.max_pages
            )
            
            if listings:
                scraper.save_to_json(listings, "listings.json")
                scraper.save_to_csv(listings, "listings.csv")
                print(f"\nScraped {len(listings)} listings successfully!")
        
        else:
            print("Please provide either --url or --category argument")
    
    finally:
        scraper.close()


if __name__ == "__main__":
    main()
