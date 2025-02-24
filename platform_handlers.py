from abc import ABC, abstractmethod
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
import keyring
import time
import os
import sys
from pathlib import Path
import subprocess
import psutil
from enum import Enum

class PlatformType(Enum):
    """Enum for supported meeting platforms."""
    ZOOM = "zoom"
    GOOGLE_MEET = "google_meet"
    TEAMS = "teams"

class BrowserType:
    CHROME = "chrome"
    FIREFOX = "firefox"

class PlatformManager:
    def __init__(self):
        self.zoom_app_paths = {
            'windows': r'C:\Users\%USERNAME%\AppData\Roaming\Zoom\bin\Zoom.exe',
            'mac': '/Applications/zoom.us.app',
            'linux': '/usr/bin/zoom'
        }
        self.teams_app_paths = {
            'windows': r'C:\Users\%USERNAME%\AppData\Local\Microsoft\Teams\current\Teams.exe',
            'mac': '/Applications/Microsoft Teams.app',
            'linux': '/usr/bin/teams'
        }
        # Define browser detection paths
        self.browser_paths = {
            BrowserType.CHROME: {
                'windows': [
                    r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                    r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                    r'C:\Users\%USERNAME%\AppData\Local\Google\Chrome\Application\chrome.exe'
                ],
                'mac': [
                    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
                ],
                'linux': [
                    '/usr/bin/google-chrome',
                    '/usr/bin/chromium-browser',
                    '/usr/bin/chromium'
                ]
            },
            BrowserType.FIREFOX: {
                'windows': [
                    r'C:\Program Files\Mozilla Firefox\firefox.exe',
                    r'C:\Program Files (x86)\Mozilla Firefox\firefox.exe'
                ],
                'mac': [
                    '/Applications/Firefox.app/Contents/MacOS/firefox'
                ],
                'linux': [
                    '/usr/bin/firefox'
                ]
            }
        }

    def detect_installed_apps(self):
        """Detect which platform apps are installed."""
        installed_apps = {}
        
        for platform, paths in {
            'zoom': self.zoom_app_paths,
            'teams': self.teams_app_paths
        }.items():
            if sys.platform.startswith('win'):
                path = os.path.expandvars(paths['windows'])
            elif sys.platform.startswith('darwin'):
                path = paths['mac']
            else:
                path = paths['linux']
            
            installed_apps[platform] = os.path.exists(path)
        
        return installed_apps

    def get_app_path(self, platform):
        """Get the path for a specific platform's app."""
        paths = getattr(self, f"{platform}_app_paths")
        if sys.platform.startswith('win'):
            return os.path.expandvars(paths['windows'])
        elif sys.platform.startswith('darwin'):
            return paths['mac']
        return paths['linux']
    
    def detect_browser(self):
        """Detect which browsers are installed."""
        installed_browsers = {}
        
        for browser_type, browser_paths in self.browser_paths.items():
            if sys.platform.startswith('win'):
                paths = browser_paths['windows']
                # Expand environment variables in Windows paths
                paths = [os.path.expandvars(path) for path in paths]
            elif sys.platform.startswith('darwin'):
                paths = browser_paths['mac']
            else:
                paths = browser_paths['linux']
            
            # Check if any of the paths exist
            installed_browsers[browser_type] = any(os.path.exists(path) for path in paths)
        
        return installed_browsers

class MeetingHandler(ABC):
    def __init__(self):
        self.driver = None
        self.wait = None
        self.platform_manager = PlatformManager()
        self.use_browser = False
        self.app_installed = False
        self.session_cookie_names = []
        self.verify_url = None
        self.logged_in_indicator = None
        self.logout_url = None
        self.logout_button = None
        self.browser_type = None
        self.permissions_granted = False
    
    def _detect_preferred_browser(self):
        """Detect the preferred browser to use."""
        installed_browsers = self.platform_manager.detect_browser()
        
        # Prefer Chrome over Firefox if both are installed
        if installed_browsers.get(BrowserType.CHROME, False):
            return BrowserType.CHROME
        elif installed_browsers.get(BrowserType.FIREFOX, False):
            return BrowserType.FIREFOX
        else:
            # Default to Chrome if no browser is detected
            return BrowserType.CHROME
    
    def _setup_driver(self):
        """Set up the WebDriver with appropriate options."""
        if not self.driver:
            # Determine which browser to use
            if not self.browser_type:
                self.browser_type = self._detect_preferred_browser()
            
            if self.browser_type == BrowserType.CHROME:
                options = ChromeOptions()
                options.add_argument("--start-maximized")
                options.add_argument("--disable-notifications")
                
                # Enable automatic media stream permissions
                options.add_argument("--use-fake-ui-for-media-stream")
                
                # Add Chrome-specific preferences for permissions
                options.add_experimental_option("prefs", {
                    "profile.default_content_setting_values.media_stream_mic": 1,  # 1 = allow, 2 = block
                    "profile.default_content_setting_values.media_stream_camera": 1,
                    "profile.default_content_setting_values.notifications": 1,
                    "profile.default_content_setting_values.geolocation": 1
                })
                
                self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
            
            elif self.browser_type == BrowserType.FIREFOX:
                options = FirefoxOptions()
                options.set_preference("media.navigator.permission.disabled", True)  # Auto-allow camera/mic
                options.set_preference("permissions.default.microphone", 1)  # 1 = allow
                options.set_preference("permissions.default.camera", 1)  # 1 = allow
                options.set_preference("dom.webnotifications.enabled", False)  # Disable notifications
                
                self.driver = webdriver.Firefox(service=FirefoxService(GeckoDriverManager().install()), options=options)
            
            # Set a longer wait time for both browsers
            self.wait = WebDriverWait(self.driver, 30)
    
    def _cleanup(self):
        """Clean up the WebDriver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.wait = None
    
    def check_existing_session(self):
        """Check if there's an existing session in the browser."""
        try:
            self._setup_driver()
            self.driver.get(self.platform_url)
            
            # Check for session cookies
            cookies = self.driver.get_cookies()
            session_cookie = next(
                (c for c in cookies if c['name'] in self.session_cookie_names),
                None
            )
            
            if session_cookie:
                return self._verify_session()
            return False
        except Exception as e:
            print(f"Session check error: {str(e)}")
            return False

    def _pre_grant_permissions(self, url):
        """Visit site once to pre-grant camera/mic permissions if needed."""
        if not self.permissions_granted:
            try:
                # Visit the permission test URL
                self.driver.get(url)
                
                # Wait a moment to ensure permissions are processed
                time.sleep(3)
                
                # Check for permission prompts
                self._handle_permission_prompts()
                
                self.permissions_granted = True
                
                # Return to original URL
                self.driver.get(self.platform_url)
                
                return True
            except Exception as e:
                print(f"Error pre-granting permissions: {str(e)}")
                return False
        return True
    
    def _handle_permission_prompts(self):
        """Handle permission prompts that may appear."""
        try:
            # Different approaches for different browsers
            if self.browser_type == BrowserType.CHROME:
                # For Chrome, look for the "Allow" button in permission dialogs
                try:
                    # Common selectors for Chrome permission dialogs
                    selectors = [
                        "//button[contains(text(), 'Allow')]",
                        "//button[contains(text(), 'Accept')]",
                        "//div[contains(@aria-label, 'Allow')]",
                        "//div[contains(@aria-label, 'Accept')]"
                    ]
                    
                    for selector in selectors:
                        try:
                            allow_buttons = self.driver.find_elements(By.XPATH, selector)
                            for button in allow_buttons:
                                if button.is_displayed():
                                    button.click()
                                    time.sleep(1)  # Wait for dialog to close
                        except Exception:
                            pass
                except Exception:
                    pass
            
            elif self.browser_type == BrowserType.FIREFOX:
                # Firefox has different permission UI
                try:
                    selectors = [
                        "//button[contains(text(), 'Allow')]",
                        "//button[@id='permission-accept']",
                        "//button[contains(@value, 'allow')]"
                    ]
                    
                    for selector in selectors:
                        try:
                            allow_buttons = self.driver.find_elements(By.XPATH, selector)
                            for button in allow_buttons:
                                if button.is_displayed():
                                    button.click()
                                    time.sleep(1)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception as e:
            print(f"Error handling permission prompts: {str(e)}")

    def _verify_session(self):
        """Verify if existing session is valid."""
        try:
            self.driver.get(self.verify_url)
            return bool(self.wait.until(
                EC.presence_of_element_located(self.logged_in_indicator)
            ))
        except Exception:
            return False

    def verify_account_match(self, required_email):
        """Verify if the logged-in account matches the required one."""
        try:
            current_email = self._get_logged_in_email()
            
            if not current_email:
                # No account logged in, proceed with normal login
                return self._handle_login(required_email)
            
            if current_email.lower() != required_email.lower():
                # Different account logged in, handle account switch
                return self._handle_account_switch(current_email, required_email)
            
            return True
        except Exception as e:
            print(f"Error verifying account: {str(e)}")
            self.use_browser = True
            return False

    def _handle_account_switch(self, current_email, required_email):
        """Handle switching between different accounts."""
        try:
            # Show confirmation dialog via PyQt6
            from PyQt6.QtWidgets import QMessageBox
            
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle("Account Mismatch")
            msg.setText(f"Different account detected in browser")
            msg.setInformativeText(
                f"Current: {current_email}\n"
                f"Required: {required_email}\n\n"
                "Would you like to:"
            )
            msg.setStandardButtons(
                QMessageBox.StandardButton.Yes | 
                QMessageBox.StandardButton.No | 
                QMessageBox.StandardButton.Cancel
            )
            msg.button(QMessageBox.StandardButton.Yes).setText("Switch Account")
            msg.button(QMessageBox.StandardButton.No).setText("Use Current Account")
            msg.button(QMessageBox.StandardButton.Cancel).setText("Cancel")
            
            response = msg.exec()
            
            if response == QMessageBox.StandardButton.Yes:
                # User wants to switch accounts
                if self._logout():
                    return self._handle_login(required_email)
                return False
            elif response == QMessageBox.StandardButton.No:
                # User wants to use current account
                return True
            else:
                # User cancelled
                return False
                
        except Exception as e:
            print(f"Error handling account switch: {str(e)}")
            return False

    def _logout(self):
        """Logout from the current session."""
        try:
            if not self.driver:
                self._setup_driver()
            
            self.driver.get(self.logout_url)
            
            # Wait for and click logout button
            logout_btn = self.wait.until(
                EC.element_to_be_clickable(self.logout_button)
            )
            logout_btn.click()
            
            # Wait for logout to complete
            time.sleep(2)
            
            # Clear cookies and cache
            self.driver.delete_all_cookies()
            
            return True
        except Exception as e:
            print(f"Error during logout: {str(e)}")
            return False
    
    @abstractmethod
    def _handle_login(self, email):
        """Handle login process."""
        pass
    
    @abstractmethod
    def _get_logged_in_email(self):
        """Get currently logged in email."""
        pass
    
    def join_meeting(self, url=None, meeting_id=None, password=None, required_email=None):
        """Join a meeting using either URL or ID."""
        try:
            # Setup driver and pre-grant permissions
            self._setup_driver()
            self._pre_grant_permissions(self.platform_url)
            
            # Check if app is preferred and available
            self.app_installed = self.platform_manager.detect_installed_apps().get(self.platform_type, False)
            
            if not self.use_browser and self.app_installed:
                # Join via native app
                return self._join_via_app(url, meeting_id, password)
            else:
                # Join via browser
                # If email authentication is required, verify account
                if required_email:
                    self.verify_account_match(required_email)
                
                # Join the meeting
                return self._join_via_browser(url, meeting_id, password)
                
        except Exception as e:
            print(f"Error joining meeting: {str(e)}")
            return False
        finally:
            # Always ensure driver is cleaned up
            if not self.app_installed:
                self._cleanup()

class ZoomHandler(MeetingHandler):
    def __init__(self):
        super().__init__()
        self.service_name = "meeting_automator_zoom"
        self.platform_name = "zoom"
        self.platform_type = "zoom"  # Used by platform_manager
        self.platform_url = "https://zoom.us"
        self.verify_url = "https://zoom.us/profile"
        self.logged_in_indicator = (By.CSS_SELECTOR, ".profile-info")
        self.session_cookie_names = ["_zm_ssid", "_zm_chtaid"]
        self.google_auth_url = "https://zoom.us/google/oauth"
        self.logout_url = "https://zoom.us/profile"
        self.logout_button = (By.CSS_SELECTOR, "[aria-label='Sign Out']")
    
    def set_credentials(self, username: str, password: str):
        """Store Zoom credentials securely."""
        keyring.set_password(self.service_name, username, password)
    
    def sign_in_with_google(self):
        """Sign in to Zoom using Google authentication."""
        try:
            self._setup_driver()
            self.driver.get(self.google_auth_url)
            
            google_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-google-signin]"))
            )
            google_btn.click()
            
            # Handle Google auth flow
            self._handle_google_auth()
            return True
        except Exception as e:
            print(f"Google sign-in failed: {str(e)}")
            return False
    
    def _handle_login(self, email):
        """Handle login to Zoom."""
        try:
            # Try to find credentials for this email
            password = keyring.get_password(self.service_name, email)
            
            if not password:
                print(f"No credentials found for {email}")
                return False
            
            if not self.driver:
                self._setup_driver()
            
            # Navigate to sign-in page
            self.driver.get(self.platform_url + "/signin")
            
            try:
                # Try email/password login first
                email_field = self.wait.until(
                    EC.element_to_be_clickable((By.ID, "email"))
                )
                email_field.send_keys(email)
                
                password_field = self.driver.find_element(By.ID, "password")
                password_field.send_keys(password)
                
                sign_in_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Sign In')]")
                sign_in_btn.click()
                
                # Wait for login to complete
                self.wait.until(
                    EC.presence_of_element_located(self.logged_in_indicator)
                )
                
                return True
                
            except Exception as e:
                print(f"Email/password login failed: {str(e)}")
                # Try Google sign-in as fallback
                return self.sign_in_with_google()
                
        except Exception as e:
            print(f"Login failed: {str(e)}")
            return False

    def _get_logged_in_email(self):
        """Get the email of the logged-in Zoom account."""
        try:
            self.driver.get(self.verify_url)
            email_element = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".profile-email"))
            )
            return email_element.text
        except Exception:
            return None

    def _join_via_app(self, url=None, meeting_id=None, password=None):
        """Join a Zoom meeting using the desktop app."""
        try:
            app_path = self.platform_manager.get_app_path("zoom")
            
            if url:
                subprocess.Popen([app_path, "--url=" + url])
            elif meeting_id:
                cmd = [app_path, "--join"]
                if meeting_id:
                    cmd.extend(["--meetingid", meeting_id])
                if password:
                    cmd.extend(["--password", password])
                
                subprocess.Popen(cmd)
            
            return True
        except Exception as e:
            print(f"Error joining via app: {str(e)}")
            # Fallback to browser if app joining fails
            self.use_browser = True
            return self._join_via_browser(url, meeting_id, password)

    def _join_via_browser(self, url=None, meeting_id=None, password=None):
        """Join a Zoom meeting using the web browser."""
        try:
            if not self.driver:
                self._setup_driver()
            
            # Make sure we've pre-granted permissions
            self._pre_grant_permissions("https://zoom.us/wc/join")
            
            # Direct joining via URL if provided
            if url:
                self.driver.get(url)
            else:
                # Join via meeting ID
                self.driver.get("https://zoom.us/wc/join/" + meeting_id)
                
                # Handle password if needed
                try:
                    pwd_field = self.wait.until(
                        EC.element_to_be_clickable((By.ID, "input-for-pwd"))
                    )
                    pwd_field.send_keys(password)
                    
                    join_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Join')]")
                    join_btn.click()
                except Exception:
                    # Password field might not appear if not needed
                    pass
            
            # Wait for joining page to load
            time.sleep(3)
            
            # Handle browser permission prompts
            self._handle_permission_prompts()
            
            # Click to join audio if prompted
            try:
                # Look for the "Join Audio by Computer" button
                join_audio_btns = self.wait.until(
                    EC.presence_of_all_elements_located((By.XPATH, "//button[contains(text(), 'Join Audio') or contains(text(), 'Computer Audio')]"))
                )
                if join_audio_btns:
                    join_audio_btns[0].click()
            except Exception:
                # This might not appear if auto-join is set
                pass
            
            # Successfully joined
            return True
        except Exception as e:
            print(f"Error joining via browser: {str(e)}")
            return False

class TeamsHandler(MeetingHandler):
    def __init__(self):
        super().__init__()
        self.service_name = "meeting_automator_teams"
        self.platform_name = "teams"
        self.platform_type = "teams"  # Used by platform_manager
        self.platform_url = "https://teams.microsoft.com"
        self.verify_url = "https://teams.microsoft.com/_#/calendarv2"
        self.logged_in_indicator = (By.CSS_SELECTOR, ".user-picture")
        self.session_cookie_names = ["MSTS", "MSPAuth"]
        self.logout_url = "https://teams.microsoft.com/_#/profilecard"
        self.logout_button = (By.XPATH, "//button[contains(@title, 'Sign out')]")
    
    def set_credentials(self, email: str, password: str):
        """Store Teams credentials securely."""
        keyring.set_password(self.service_name, email, password)
    
    def _handle_login(self, email):
        """Handle login to Microsoft Teams."""
        try:
            # Try to find credentials for this email
            password = keyring.get_password(self.service_name, email)
            
            if not password:
                print(f"No credentials found for {email}")
                return False
            
            if not self.driver:
                self._setup_driver()
            
            # Navigate to Teams
            self.driver.get(self.platform_url)
            
            # Check if we need to sign in
            try:
                # Enter email
                email_field = self.wait.until(
                    EC.element_to_be_clickable((By.NAME, "loginfmt"))
                )
                email_field.send_keys(email)
                
                # Click Next
                next_btn = self.wait.until(
                    EC.element_to_be_clickable((By.ID, "idSIButton9"))
                )
                next_btn.click()
                
                # Wait for password field and enter password
                password_field = self.wait.until(
                    EC.element_to_be_clickable((By.NAME, "passwd"))
                )
                password_field.send_keys(password)
                
                # Click Sign in
                sign_in_btn = self.wait.until(
                    EC.element_to_be_clickable((By.ID, "idSIButton9"))
                )
                sign_in_btn.click()
                
                # Handle "Stay signed in" prompt
                try:
                    stay_signed_in_btn = self.wait.until(
                        EC.element_to_be_clickable((By.ID, "idSIButton9")),
                        timeout=10
                    )
                    stay_signed_in_btn.click()
                except Exception:
                    # This prompt might not appear if "Don't show again" was checked
                    pass
                
                # Handle "Use the web app instead" prompt
                try:
                    web_app_btn = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'web app instead')]")),
                        timeout=10
                    )
                    web_app_btn.click()
                except Exception:
                    # This prompt might not appear
                    pass
                
                # Wait for Teams to load
                self.wait.until(
                    EC.presence_of_element_located(self.logged_in_indicator)
                )
                
                return True
                
            except Exception as e:
                print(f"Microsoft login failed: {str(e)}")
                return False
                
        except Exception as e:
            print(f"Teams login failed: {str(e)}")
            return False

    def _get_logged_in_email(self):
        """Get the email of the logged-in Microsoft account."""
        try:
            # Click on profile picture to open menu
            profile_pic = self.wait.until(
                EC.element_to_be_clickable(self.logged_in_indicator)
            )
            profile_pic.click()
            
            # Get email from profile card
            email_element = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".profile-card-content .user-email"))
            )
            return email_element.text
        except Exception as e:
            print(f"Error getting logged in email: {str(e)}")
            return None

    def _join_via_app(self, url=None, meeting_id=None, password=None):
        """Join a Teams meeting using the desktop app."""
        try:
            app_path = self.platform_manager.get_app_path("teams")
            
            if url:
                subprocess.Popen([app_path, url])
            
            return True
        except Exception as e:
            print(f"Error joining via app: {str(e)}")
            # Fallback to browser if app joining fails
            self.use_browser = True
            return self._join_via_browser(url, meeting_id, password)

    def _join_via_browser(self, url=None, meeting_id=None, password=None):
        """Join a Teams meeting using the web browser."""
        try:
            if not self.driver:
                self._setup_driver()
            
            # Make sure we've pre-granted permissions
            self._pre_grant_permissions("https://teams.microsoft.com")
            
            # Navigate to the meeting URL
            if url:
                self.driver.get(url)
            else:
                # We can't join by meeting ID directly, need to use URL
                print("Teams meetings require a URL to join via browser")
                return False
            
            # Wait for page to load
            time.sleep(5)
            
            # Check for "Continue on this browser" option
            try:
                continue_browser_btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue on this browser')]")),
                    timeout=10
                )
                continue_browser_btn.click()
            except Exception:
                # This might not appear
                pass
            
            # Handle browser permission prompts
            self._handle_permission_prompts()
            
            # Wait for join options to load
            time.sleep(3)
            
            # Toggle camera off (optional)
            try:
                camera_toggle = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Camera')]"))
                )
                # Check if camera is on based on aria-pressed attribute
                if camera_toggle.get_attribute("aria-pressed") == "true":
                    camera_toggle.click()
            except Exception:
                # Camera toggle might not be available
                pass
            
            # Toggle microphone off (optional)
            try:
                mic_toggle = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Microphone')]"))
                )
                # Check if microphone is on based on aria-pressed attribute
                if mic_toggle.get_attribute("aria-pressed") == "true":
                    mic_toggle.click()
            except Exception:
                # Microphone toggle might not be available
                pass
            
            # Enter name if prompted
            try:
                name_field = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder*='Enter name']")),
                    timeout=5
                )
                name_field.clear()
                name_field.send_keys("Meeting Automator")
            except Exception:
                # Name field might not appear if logged in
                pass
            
            # Click Join button
            join_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Join')]"))
            )
            join_btn.click()
            
            # Successfully joined
            return True
        except Exception as e:
            print(f"Error joining Teams meeting: {str(e)}")
            return False

def get_handler(platform: str) -> MeetingHandler:
    """Factory function to get the appropriate handler for a platform."""
    if isinstance(platform, str):
        platform = platform.lower()
        
        if platform == "zoom" or platform == PlatformType.ZOOM.value:
            return ZoomHandler()
        elif platform == "teams" or platform == PlatformType.TEAMS.value:
            return TeamsHandler()
        elif platform == "google_meet" or platform == PlatformType.GOOGLE_MEET.value:
            return GoogleMeetHandler()
        else:
            raise ValueError(f"Unknown platform: {platform}")
    elif isinstance(platform, PlatformType):
        if platform == PlatformType.ZOOM:
            return ZoomHandler()
        elif platform == PlatformType.TEAMS:
            return TeamsHandler()
        elif platform == PlatformType.GOOGLE_MEET:
            return GoogleMeetHandler()
        else:
            raise ValueError(f"Unknown platform type: {platform}")
    else:
        raise TypeError(f"Platform must be a string or PlatformType, got {type(platform)}")

class GoogleMeetHandler(MeetingHandler):
    def __init__(self):
        super().__init__()
        self.service_name = "meeting_automator_google"
        self.platform_name = "google_meet"
        self.platform_type = "google_meet"
        self.platform_url = "https://meet.google.com"
        self.verify_url = "https://accounts.google.com/ServiceLogin?continue=https://meet.google.com"
        self.logged_in_indicator = (By.XPATH, "//a[contains(@href, 'SignOutOptions')]")
        self.session_cookie_names = ["SID", "HSID", "SSID"]
        self.logout_url = "https://accounts.google.com/Logout"
        self.logout_button = (By.XPATH, "//button[contains(text(), 'Sign out')]")
    
    def set_credentials(self, email: str, password: str):
        """Store Google credentials securely."""
        keyring.set_password(self.service_name, email, password)
    
    def _handle_login(self, email):
        """Handle login to Google Meet."""
        try:
            # Try to find credentials for this email
            password = keyring.get_password(self.service_name, email)
            
            if not password:
                print(f"No credentials found for {email}")
                return False
            
            if not self.driver:
                self._setup_driver()
            
            # Navigate to Google sign-in
            self.driver.get("https://accounts.google.com/signin")
            
            # Enter email
            email_field = self.wait.until(
                EC.element_to_be_clickable((By.ID, "identifierId"))
            )
            email_field.send_keys(email)
            
            # Click Next
            next_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button/span[contains(text(), 'Next')]"))
            )
            next_btn.click()
            
            # Wait for password field and enter password
            password_field = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//input[@type='password']"))
            )
            password_field.send_keys(password)
            
            # Click Next to complete sign-in
            next_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button/span[contains(text(), 'Next')]"))
            )
            next_btn.click()
            
            # Wait for login to complete
            time.sleep(5)
            
            # Verify login success
            self.driver.get(self.verify_url)
            try:
                self.wait.until(
                    EC.presence_of_element_located(self.logged_in_indicator)
                )
                return True
            except Exception:
                return False
                
        except Exception as e:
            print(f"Google login failed: {str(e)}")
            return False

    def _get_logged_in_email(self):
        """Get the email of the logged-in Google account."""
        try:
            # Go to Google account page
            self.driver.get("https://myaccount.google.com/")
            
            # Look for email in account page
            email_element = self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@data-email, '@')]"))
            )
            return email_element.get_attribute("data-email")
        except Exception as e:
            print(f"Error getting logged in email: {str(e)}")
            return None

    def _join_via_app(self, url=None, meeting_id=None, password=None):
        """Google Meet has no desktop app, always use browser."""
        return self._join_via_browser(url, meeting_id, password)

    def _join_via_browser(self, url=None, meeting_id=None, password=None):
        """Join a Google Meet meeting using the web browser."""
        try:
            if not self.driver:
                self._setup_driver()
            
            # Make sure we've pre-granted permissions
            self._pre_grant_permissions("https://meet.google.com")
            
            # Navigate to the meeting
            if url:
                self.driver.get(url)
            elif meeting_id:
                self.driver.get(f"https://meet.google.com/{meeting_id}")
            else:
                print("Google Meet requires either a URL or meeting ID")
                return False
            
            # Handle browser permission prompts
            self._handle_permission_prompts()
            
            # Wait for join options to load
            time.sleep(3)
            
            # Turn off camera and microphone if they're on
            try:
                # Camera toggle button
                camera_toggle = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Turn off camera']"))
                )
                camera_toggle.click()
            except Exception:
                # Camera might already be off
                pass
            
            try:
                # Microphone toggle button
                mic_toggle = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@aria-label='Turn off microphone']"))
                )
                mic_toggle.click()
            except Exception:
                # Microphone might already be off
                pass
            
            # Click Join button - different buttons depending on context
            try:
                # Try "Join now" button first (when you're the first participant)
                join_btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//span[text()='Join now']/ancestor::button")),
                    timeout=5
                )
                join_btn.click()
            except Exception:
                try:
                    # Try "Ask to join" button (when others are already in the meeting)
                    join_btn = self.wait.until(
                        EC.element_to_be_clickable((By.XPATH, "//span[text()='Ask to join']/ancestor::button"))
                    )
                    join_btn.click()
                except Exception as e:
                    print(f"Could not find Join button: {str(e)}")
                    return False
            
            # Successfully joined
            return True
        except Exception as e:
            print(f"Error joining Google Meet: {str(e)}")
            return False 