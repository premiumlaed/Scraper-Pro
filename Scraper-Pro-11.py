import customtkinter as ctk
from tkinter import messagebox, filedialog
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from urllib.parse import quote_plus
import pandas as pd
import time
import json
import re
import threading
from datetime import datetime
import random
import os
import logging
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Application Constants
APP_VERSION = "2.0"
SUPPORT_CONTACTS = {
    "email": "support@example.com",
    "discord": "https://discord.gg/yoursupport",
    "telegram": "@yoursupport",
    "github": "https://github.com/yourusername/google-scraper-pro/issues"
}

# UI Constants
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
PADDING = 10
BUTTON_WIDTH = 120
BUTTON_HEIGHT = 32

# Platform Settings
PLATFORMS = {
    "linkedin": {
        "base_url": "https://www.linkedin.com",
        "search_url": "https://www.linkedin.com/search/results/all/?keywords=",
        "rate_limit": 2.5  # seconds between requests
    },
    "facebook": {
        "base_url": "https://www.facebook.com",
        "search_url": "https://www.facebook.com/search/top/?q=",
        "rate_limit": 2.0
    },
    "instagram": {
        "base_url": "https://www.instagram.com",
        "search_url": "https://www.instagram.com/explore/tags/",
        "rate_limit": 3.0
    },
    "twitter": {
        "base_url": "https://twitter.com",
        "search_url": "https://twitter.com/search?q=",
        "rate_limit": 2.0
    },
    "google_maps": {
        "base_url": "https://www.google.com/maps",
        "search_url": "https://www.google.com/maps/search/",
        "rate_limit": 2.0
    }
}

# Set appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
class DataExtractor:
    """Data extraction and cleaning functionality"""

    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """Extract email addresses from text"""
        if not text:
            return []
            
        email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
        emails = re.findall(email_pattern, text)
        cleaned_emails = [
            email.lower() for email in emails 
            if len(email) > 5 and '.' in email.split('@')[1]
        ]
        return list(set(cleaned_emails))

    @staticmethod
    def extract_phones(text: str) -> List[str]:
        """Extract phone numbers from text"""
        if not text:
            return []

        phone_patterns = [
            r'\+\d{1,4}[-\s]?\d{1,3}[-\s]?\d{3,4}[-\s]?\d{3,4}',
            r'\d{3}[-\s]?\d{3}[-\s]?\d{4}',
            r'00\d{1,3}[-\s]?\d{1,3}[-\s]?\d{3,4}[-\s]?\d{3,4}',
            # Middle East Patterns
            r'(?:971|0)?(?:2|3|4|6|7|9|50|51|52|55|56|58)\d{7}',  # UAE
            r'(?:966|0)?(?:5|8|9)\d{8}',  # KSA
            # Add more regional patterns as needed
        ]

        phones = []
        for pattern in phone_patterns:
            found = re.findall(pattern, text)
            phones.extend(found)

        cleaned_phones = []
        for phone in phones:
            cleaned = re.sub(r'[\s\(\)-]', '', phone)
            if len(cleaned) >= 8:
                cleaned_phones.append(cleaned)

        return list(set(cleaned_phones))

    @staticmethod
    def clean_text(text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        # Remove unwanted characters but keep essential ones
        cleaned = re.sub(r'[^\w\s@+\(\)\-\.,]', '', text)
        # Normalize whitespace
        cleaned = ' '.join(cleaned.split())
        return cleaned

    @staticmethod
    def extract_contact_info(text: str) -> Tuple[List[str], List[str]]:
        """Extract both emails and phone numbers from text"""
        cleaned_text = DataExtractor.clean_text(text)
        emails = DataExtractor.extract_emails(cleaned_text)
        phones = DataExtractor.extract_phones(cleaned_text)
        return emails, phones

class PlatformScraper:
    """Base class for platform-specific scrapers"""
    
    def __init__(self, driver: webdriver.Chrome):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
        self.data_extractor = DataExtractor()

    def _wait_and_get_element(self, by, value, timeout=10):
        """Safely wait for and return an element"""
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            logger.warning(f"Timeout waiting for element: {value}")
            return None

    def _safe_click(self, element):
        """Safely click an element with multiple attempts"""
        try:
            # Try regular click
            element.click()
        except:
            try:
                # Try JavaScript click
                self.driver.execute_script("arguments[0].click();", element)
            except Exception as e:
                logger.error(f"Failed to click element: {str(e)}")
                return False
        return True

    def _scroll_page(self, scroll_pause=1.0):
        """Scroll page to load dynamic content"""
        try:
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            while True:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(scroll_pause)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break
                last_height = new_height
        except Exception as e:
            logger.error(f"Error scrolling page: {str(e)}")

class InstagramScraper(PlatformScraper):
    """Instagram-specific scraping functionality"""

    def login(self, username: str, password: str) -> bool:
        """Login to Instagram"""
        try:
            self.driver.get("https://www.instagram.com/login")
            time.sleep(random.uniform(2, 4))

            # Enter username
            username_input = self._wait_and_get_element(By.NAME, "username")
            if username_input:
                username_input.send_keys(username)

            # Enter password
            password_input = self._wait_and_get_element(By.NAME, "password")
            if password_input:
                password_input.send_keys(password)

            # Click login button
            login_button = self._wait_and_get_element(
                By.CSS_SELECTOR, 
                "button[type='submit']"
            )
            if login_button:
                self._safe_click(login_button)

            time.sleep(5)  # Wait for login to complete
            
            # Verify login success
            try:
                self._wait_and_get_element(By.CSS_SELECTOR, "nav[role='navigation']")
                logger.info("Successfully logged into Instagram")
                return True
            except:
                logger.error("Failed to verify Instagram login")
                return False

        except Exception as e:
            logger.error(f"Instagram login failed: {str(e)}")
            return False

    def search_business(self, query: str) -> List[dict]:
        """Search Instagram for business information"""
        results = []
        try:
            encoded_query = quote_plus(query)
            self.driver.get(f"https://www.instagram.com/explore/tags/{encoded_query}/")
            time.sleep(random.uniform(2, 4))

            # Scroll to load more content
            self._scroll_page()

            # Get post links
            posts = self.driver.find_elements(By.CSS_SELECTOR, "article a")
            
            for post in posts[:10]:  # Limit to first 10 posts
                try:
                    # Click post to open
                    self._safe_click(post)
                    time.sleep(random.uniform(1, 2))

                    # Extract user information
                    username = self._wait_and_get_element(
                        By.CSS_SELECTOR, 
                        "header a"
                    )
                    if username:
                        profile_url = username.get_attribute("href")
                        
                        # Visit profile
                        self.driver.get(profile_url)
                        time.sleep(random.uniform(1, 2))

                        # Extract bio
                        bio = self._wait_and_get_element(
                            By.CSS_SELECTOR, 
                            ".-vDIg span"
                        )
                        bio_text = bio.text if bio else ""

                        # Extract contact information
                        emails, phones = self.data_extractor.extract_contact_info(bio_text)

                        results.append({
                            'platform': 'Instagram',
                            'username': username.text,
                            'profile_url': profile_url,
                            'bio': bio_text,
                            'emails': emails,
                            'phones': phones
                        })

                except Exception as e:
                    logger.error(f"Error processing Instagram post: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Instagram search failed: {str(e)}")

        return results

class TwitterScraper(PlatformScraper):
    """Twitter-specific scraping functionality"""

    def search_business(self, query: str) -> List[dict]:
        """Search Twitter for business information"""
        results = []
        try:
            encoded_query = quote_plus(query)
            self.driver.get(f"https://twitter.com/search?q={encoded_query}&f=user")
            time.sleep(random.uniform(2, 4))

            # Scroll to load more results
            for _ in range(3):
                self._scroll_page(scroll_pause=2.0)

            # Find profile cards
            profiles = self.driver.find_elements(
                By.CSS_SELECTOR, 
                '[data-testid="UserCell"]'
            )

            for profile in profiles[:10]:  # Limit to first 10 profiles
                try:
                    # Extract profile information
                    name = profile.find_element(
                        By.CSS_SELECTOR, 
                        '[data-testid="UserName"]'
                    ).text

                    bio = profile.find_element(
                        By.CSS_SELECTOR, 
                        '[data-testid="UserDescription"]'
                    ).text

                    # Get profile URL
                    profile_link = profile.find_element(
                        By.CSS_SELECTOR, 
                        'a[role="link"]'
                    ).get_attribute('href')

                    # Extract contact information
                    emails, phones = self.data_extractor.extract_contact_info(bio)

                    results.append({
                        'platform': 'Twitter',
                        'name': name,
                        'profile_url': profile_link,
                        'bio': bio,
                        'emails': emails,
                        'phones': phones
                    })

                except Exception as e:
                    logger.error(f"Error processing Twitter profile: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Twitter search failed: {str(e)}")

        return results

class GoogleMapsScraper(PlatformScraper):
    """Google Maps-specific scraping functionality"""

    def search_business(self, query: str, location: str) -> List[dict]:
        """Search Google Maps for business information"""
        results = []
        try:
            search_query = f"{query} {location}".strip()
            encoded_query = quote_plus(search_query)
            self.driver.get(f"https://www.google.com/maps/search/{encoded_query}")
            time.sleep(random.uniform(2, 4))

            # Wait for results to load
            self._wait_and_get_element(By.CLASS_NAME, "section-result")

            # Scroll through results
            for _ in range(3):
                self.driver.execute_script(
                    "document.getElementsByClassName('section-layout-root')[0].scrollTop += 1000"
                )
                time.sleep(2)

            # Get business listings
            businesses = self.driver.find_elements(By.CLASS_NAME, "section-result")

            for business in businesses[:10]:  # Limit to first 10 businesses
                try:
                    # Click to open business details
                    self._safe_click(business)
                    time.sleep(random.uniform(1, 2))

                    # Extract business information
                    name = self._wait_and_get_element(
                        By.CSS_SELECTOR, 
                        ".section-result-title"
                    )
                    name_text = name.text if name else "N/A"

                    # Get phone number
                    phone = self._wait_and_get_element(
                        By.CSS_SELECTOR, 
                        "[data-item-id*='phone']"
                    )
                    phone_text = phone.text if phone else ""

                    # Get website
                    website = self._wait_and_get_element(
                        By.CSS_SELECTOR, 
                        "[data-item-id*='website']"
                    )
                    website_url = website.get_attribute("href") if website else ""

                    # Get address
                    address = self._wait_and_get_element(
                        By.CSS_SELECTOR, 
                        "[data-item-id*='address']"
                    )
                    address_text = address.text if address else ""

                    # Extract additional contact information from website if available
                    emails = []
                    if website_url:
                        try:
                            response = requests.get(website_url, timeout=10)
                            if response.status_code == 200:
                                emails = self.data_extractor.extract_emails(response.text)
                        except:
                            pass

                    results.append({
                        'platform': 'Google Maps',
                        'name': name_text,
                        'address': address_text,
                        'phone': [phone_text] if phone_text else [],
                        'website': website_url,
                        'emails': emails
                    })

                    # Go back to results
                    self.driver.execute_script("window.history.go(-1)")
                    time.sleep(1)

                except Exception as e:
                    logger.error(f"Error processing Google Maps business: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Google Maps search failed: {str(e)}")

        return results

class ProxyManager:
    """Manage proxy rotation and validation"""
    
    def __init__(self, proxy_list_path: str = None):
        self.proxies = []
        self.current_index = 0
        if proxy_list_path and os.path.exists(proxy_list_path):
            with open(proxy_list_path, 'r') as f:
                self.proxies = [line.strip() for line in f if line.strip()]

    def get_next_proxy(self) -> str:
        """Get next proxy from the list"""
        if not self.proxies:
            return None
        
        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy

    def validate_proxy(self, proxy: str) -> bool:
        """Validate proxy connectivity"""
        try:
            response = requests.get(
                'https://www.google.com',
                proxies={'http': proxy, 'https': proxy},
                timeout=5
            )
            return response.status_code == 200
        except:
            return False

class RateLimiter:
    """Manage request rate limiting"""
    
    def __init__(self, requests_per_minute: int = 30):
        self.delay = 60.0 / requests_per_minute
        self.last_request = 0

    def wait(self):
        """Wait appropriate time before next request"""
        now = time.time()
        time_passed = now - self.last_request
        if time_passed < self.delay:
            time.sleep(self.delay - time_passed)
        self.last_request = time.time()
class ScraperApp(ctk.CTk):
    """Main application class"""

    def __init__(self):
        super().__init__()

        # Initialize application settings
        self.title("Google Scraper Pro v2.0")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Initialize components
        self.scraper = None
        self.proxy_manager = ProxyManager('proxies.txt')
        self.rate_limiter = RateLimiter()
        self.results = []
        self.stop_search_flag = False
        self.current_task = None

        # Setup UI
        self.setup_ui()
        self.load_settings()

        # Configure styling
        self.configure(fg_color=("white", "gray10"))

    def setup_ui(self):
        """Setup main user interface"""
        # Create main container
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Create notebook for tabs
        self.notebook = ctk.CTkTabview(self.main_container)
        self.notebook.pack(fill="both", expand=True)

        # Add tabs
        self.search_tab = self.notebook.add("Search")
        self.results_tab = self.notebook.add("Results")
        self.settings_tab = self.notebook.add("Settings")
        self.about_tab = self.notebook.add("About")

        # Setup each tab
        self.setup_search_tab()
        self.setup_results_tab()
        self.setup_settings_tab()
        self.setup_about_tab()

    def setup_search_tab(self):
        """Setup search interface"""
        # Search criteria frame
        criteria_frame = ctk.CTkFrame(self.search_tab)
        criteria_frame.pack(fill="x", padx=10, pady=5)

        # Job title
        ctk.CTkLabel(criteria_frame, text="Job Title:").grid(row=0, column=0, padx=5, pady=5)
        self.job_title = ctk.CTkEntry(criteria_frame, width=300)
        self.job_title.grid(row=0, column=1, padx=5, pady=5)

        # Company
        ctk.CTkLabel(criteria_frame, text="Company:").grid(row=1, column=0, padx=5, pady=5)
        self.company = ctk.CTkEntry(criteria_frame, width=300)
        self.company.grid(row=1, column=1, padx=5, pady=5)

        # Location
        ctk.CTkLabel(criteria_frame, text="Location:").grid(row=2, column=0, padx=5, pady=5)
        self.location = ctk.CTkEntry(criteria_frame, width=300)
        self.location.grid(row=2, column=1, padx=5, pady=5)

        # Platform selection
        platforms_frame = ctk.CTkFrame(self.search_tab)
        platforms_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(platforms_frame, text="Platforms:").pack(side="left", padx=5)
        
        self.platform_vars = {}
        for platform in ["LinkedIn", "Facebook", "Instagram", "Twitter", "Google Maps"]:
            var = ctk.BooleanVar(value=True)
            self.platform_vars[platform] = var
            ctk.CTkCheckBox(platforms_frame, text=platform, variable=var).pack(side="left", padx=5)

        # Advanced options
        advanced_frame = ctk.CTkFrame(self.search_tab)
        advanced_frame.pack(fill="x", padx=10, pady=5)

        # Max pages
        ctk.CTkLabel(advanced_frame, text="Max Pages:").pack(side="left", padx=5)
        self.max_pages = ctk.CTkEntry(advanced_frame, width=100)
        self.max_pages.pack(side="left", padx=5)
        self.max_pages.insert(0, "10")

        # Use proxy
        self.use_proxy_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(advanced_frame, text="Use Proxy", variable=self.use_proxy_var).pack(side="left", padx=5)

        # Control buttons
        button_frame = ctk.CTkFrame(self.search_tab)
        button_frame.pack(fill="x", padx=10, pady=5)

        self.search_button = ctk.CTkButton(
            button_frame,
            text="Start Search",
            command=self.start_search,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.search_button.pack(side="left", padx=5)

        self.stop_button = ctk.CTkButton(
            button_frame,
            text="Stop",
            command=self.stop_search,
            fg_color="red",
            hover_color="darkred",
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=5)

        # Progress bar
        self.progress = ctk.CTkProgressBar(self.search_tab)
        self.progress.pack(fill="x", padx=10, pady=5)
        self.progress.set(0)

        # Status label
        self.status_label = ctk.CTkLabel(self.search_tab, text="Ready")
        self.status_label.pack(pady=5)

    def setup_results_tab(self):
        """Setup results display"""
        # Results toolbar
        toolbar_frame = ctk.CTkFrame(self.results_tab)
        toolbar_frame.pack(fill="x", padx=10, pady=5)

        # Export buttons
        ctk.CTkButton(
            toolbar_frame,
            text="Export CSV",
            command=self.export_csv
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            toolbar_frame,
            text="Export JSON",
            command=self.export_json
        ).pack(side="left", padx=5)

        # Results display
        self.results_frame = ctk.CTkScrollableFrame(self.results_tab)
        self.results_frame.pack(fill="both", expand=True, padx=10, pady=5)

    def setup_settings_tab(self):
        """Setup settings interface"""
        settings_frame = ctk.CTkFrame(self.settings_tab)
        settings_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Proxy settings
        proxy_frame = ctk.CTkFrame(settings_frame)
        proxy_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(proxy_frame, text="Proxy Settings").pack(anchor="w")
        
        self.proxy_file_var = ctk.StringVar()
        proxy_entry = ctk.CTkEntry(proxy_frame, textvariable=self.proxy_file_var)
        proxy_entry.pack(side="left", fill="x", expand=True, padx=5)

        ctk.CTkButton(
            proxy_frame,
            text="Browse",
            command=self.browse_proxy_file
        ).pack(side="right")

        # Rate limiting
        rate_frame = ctk.CTkFrame(settings_frame)
        rate_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(rate_frame, text="Requests per minute:").pack(side="left")
        
        self.rate_limit_var = ctk.StringVar(value="30")
        rate_entry = ctk.CTkEntry(rate_frame, textvariable=self.rate_limit_var, width=100)
        rate_entry.pack(side="left", padx=5)

    def setup_about_tab(self):
        """Setup about and support information"""
        about_frame = ctk.CTkFrame(self.about_tab)
        about_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # App info
        ctk.CTkLabel(
            about_frame,
            text=f"Google Scraper Pro v{APP_VERSION}",
            font=("Arial", 16, "bold")
        ).pack(pady=10)

        # Support info
        support_text = f"""
        For support and updates:

        Email: {SUPPORT_CONTACTS['email']}
        Discord: {SUPPORT_CONTACTS['discord']}
        Telegram: {SUPPORT_CONTACTS['telegram']}
        GitHub Issues: {SUPPORT_CONTACTS['github']}
        """

        ctk.CTkLabel(
            about_frame,
            text=support_text,
            justify="left"
        ).pack(pady=10)

    def start_search(self):
        """Start search operation"""
        if not self.job_title.get():
            messagebox.showerror("Error", "Please enter a job title")
            return

        self.search_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.results = []
        self.clear_results_display()
        self.stop_search_flag = False

        # Create search thread
        self.current_task = threading.Thread(
            target=self.search_all_platforms,
            daemon=True
        )
        self.current_task.start()

    def search_all_platforms(self):
        """Search across all selected platforms"""
        try:
            # Initialize browser if needed
            if not self.scraper:
                self.update_status("Initializing browser...")
                self.scraper = self.initialize_scraper()

            total_results = 0
            selected_platforms = [
                platform for platform, var in self.platform_vars.items() 
                if var.get()
            ]

            for i, platform in enumerate(selected_platforms):
                if self.stop_search_flag:
                    break

                self.update_status(f"Searching {platform}...")
                self.progress.set((i + 1) / len(selected_platforms))

                try:
                    if platform == "LinkedIn":
                        results = self.search_linkedin()
                    elif platform == "Facebook":
                        results = self.search_facebook()
                    elif platform == "Instagram":
                        results = self.search_instagram()
                    elif platform == "Twitter":
                        results = self.search_twitter()
                    elif platform == "Google Maps":
                        results = self.search_google_maps()

                    self.process_results(results)
                    total_results += len(results)

                except Exception as e:
                    logger.error(f"Error searching {platform}: {str(e)}")
                    continue

            self.update_status(f"Search complete. Found {total_results} results.")

        except Exception as e:
            self.update_status(f"Search failed: {str(e)}")
            logger.error(f"Search error: {str(e)}")

        finally:
            self.search_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.progress.set(0)

    def process_results(self, results: List[dict]):
        """Process and display search results"""
        for result in results:
            if self.stop_search_flag:
                break

            self.results.append(result)
            self.add_result_to_display(result)

    def add_result_to_display(self, result: dict):
        """Add a single result to the display"""
        result_frame = ctk.CTkFrame(self.results_frame)
        result_frame.pack(fill="x", padx=5, pady=2)

        # Title
        ctk.CTkLabel(
            result_frame,
            text=result.get('title', 'N/A'),
            font=("Arial", 12, "bold")
        ).pack(anchor="w")

        # Platform and other details
        details = f"{result.get('platform', 'N/A')} | {result.get('company', 'N/A')}"
        ctk.CTkLabel(
            result_frame,
            text=details
        ).pack(anchor="w")

        # Contact information
        if result.get('emails'):
            ctk.CTkLabel(
                result_frame,
                text=f"📧 {', '.join(result['emails'])}"
            ).pack(anchor="w")

        if result.get('phones'):
            ctk.CTkLabel(
                result_frame,
                text=f"📱 {', '.join(result['phones'])}"
            ).pack(anchor="w")

        # Action buttons
        button_frame = ctk.CTkFrame(result_frame)
        button_frame.pack(fill="x")

        ctk.CTkButton(
            button_frame,
            text="Open URL",
            command=lambda: self.open_url(result.get('url', ''))
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            button_frame,
            text="Copy Info",
            command=lambda: self.copy_info(result)
        ).pack(side="left", padx=5)

    def export_csv(self):
        """Export results to CSV"""
        if not self.results:
            messagebox.showwarning("Warning", "No results to export")
            return

        try:
            filename = f"scraper_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            df = pd.DataFrame(self.results)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            messagebox.showinfo("Success", f"Results exported to {filename}")
            os.startfile(os.path.dirname(os.path.abspath(filename)))

        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {str(e)}")

    def export_json(self):
        """Export results to JSON"""
        if not self.results:
            messagebox.showwarning("Warning", "No results to export")
            return

        try:
            filename = f"scraper_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=4, ensure_ascii=False)
            
            messagebox.showinfo("Success", f"Results exported to {filename}")
            os.startfile(os.path.dirname(os.path.abspath(filename)))

        except Exception as e:
            messagebox.showerror("Error", f"Export failed: {str(e)}")

    def on_closing(self):
        """Handle application closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.stop_search_flag = True
            if self.scraper:
                self.scraper.quit()
            self.quit()

if __name__ == "__main__":
    try:
        app = ScraperApp()
        app.mainloop()
    except Exception as e:
        logger.critical(f"Application failed to start: {str(e)}")
        messagebox.showerror("Error", f"Application failed to start: {str(e)}")
