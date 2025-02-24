from abc import ABC, abstractmethod
from typing import Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import keyring
import time
import os
import sys
from pathlib import Path
import subprocess
import psutil

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
    
    def _setup_driver(self):
        """Set up the Chrome WebDriver with appropriate options."""
        if not self.driver:
            options = Options()
            options.add_argument("--start-maximized")
            options.add_argument("--disable-notifications")
            options.add_argument("--use-fake-ui-for-media-stream")
            
            self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            self.wait = WebDriverWait(self.driver, 20)
    
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
        except Exception:
            return False

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
        """Handle the login process for the required account."""
        pass

    @abstractmethod
    def _get_logged_in_email(self):
        """Get the email of the currently logged-in account."""
        pass

    def join_meeting(self, url=None, meeting_id=None, password=None, required_email=None):
        """Join a meeting using either app or browser."""
        self.app_installed = self.platform_manager.detect_installed_apps().get(self.platform_name, False)
        
        if required_email and self.app_installed:
            account_matches = self.verify_account_match(required_email)
            if not account_matches:
                self.use_browser = True
        
        if self.use_browser or not self.app_installed:
            self._join_via_browser(url, meeting_id, password)
        else:
            self._join_via_app(url, meeting_id, password)

class ZoomHandler(MeetingHandler):
    def __init__(self):
        super().__init__()
        self.service_name = "meeting_automator_zoom"
        self.platform_name = "zoom"
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
        """Handle Zoom login process."""
        try:
            # Get stored credentials
            password = keyring.get_password(self.service_name, email)
            
            if not password:
                # Show error dialog
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    None,
                    "Login Error",
                    f"No stored credentials found for {email}.\n"
                    "Please add credentials in the Settings tab first."
                )
                return False
            
            if not self.driver:
                self._setup_driver()
            
            # Go to login page
            self.driver.get("https://zoom.us/signin")
            
            # Try email/password login
            try:
                # Enter email
                email_input = self.wait.until(
                    EC.presence_of_element_located((By.ID, "email"))
                )
                email_input.send_keys(email)
                
                # Enter password
                pwd_input = self.wait.until(
                    EC.presence_of_element_located((By.ID, "password"))
                )
                pwd_input.send_keys(password)
                
                # Click sign in
                sign_in_btn = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[type='submit']"))
                )
                sign_in_btn.click()
                
                # Wait for login to complete
                time.sleep(2)
                
                # Verify login success
                return self._verify_session()
                
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

    def _join_via_browser(self, url=None, meeting_id=None, password=None):
        """Join a Zoom meeting via browser."""
        try:
            self._setup_driver()
            
            if url:
                self.driver.get(url)
            else:
                self.driver.get(f"https://zoom.us/j/{meeting_id}")
            
            # Try to join from browser
            try:
                join_browser_btn = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test-id='joinButtonDesktop']"))
                )
                join_browser_btn.click()
            except:
                pass
            
            # Handle name input
            try:
                name_input = self.wait.until(
                    EC.presence_of_element_located((By.ID, "inputname"))
                )
                name_input.clear()
                name_input.send_keys("Meeting Automator")
            except:
                pass
            
            # Handle password if required
            if password:
                try:
                    pwd_input = self.wait.until(
                        EC.presence_of_element_located((By.ID, "inputpasscode"))
                    )
                    pwd_input.send_keys(password)
                except:
                    pass
            
            # Join meeting
            join_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
            )
            join_btn.click()
            
        except Exception as e:
            print(f"Error joining Zoom meeting: {str(e)}")
            self._cleanup()
            raise

class TeamsHandler(MeetingHandler):
    def __init__(self):
        super().__init__()
        self.service_name = "meeting_automator_teams"
        self.platform_name = "teams"
        self.platform_url = "https://teams.microsoft.com"
        self.verify_url = "https://teams.microsoft.com/_#/profile"
        self.logged_in_indicator = (By.CSS_SELECTOR, ".profile-card")
        self.session_cookie_names = ["MSTS", "TSAUTH"]
        self.logout_url = "https://teams.microsoft.com/_#/profile"
        self.logout_button = (By.CSS_SELECTOR, "[data-tid='logout-button']")
    
    def set_credentials(self, email: str, password: str):
        """Store Microsoft credentials securely."""
        keyring.set_password(self.service_name, email, password)
    
    def _handle_login(self, email):
        """Handle Teams login process."""
        try:
            # Get stored credentials
            password = keyring.get_password(self.service_name, email)
            
            if not password:
                # Show error dialog
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    None,
                    "Login Error",
                    f"No stored credentials found for {email}.\n"
                    "Please add credentials in the Settings tab first."
                )
                return False
            
            if not self.driver:
                self._setup_driver()
            
            # Go to login page
            self.driver.get("https://teams.microsoft.com/signin")
            
            # Enter email
            email_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[type='email']"))
            )
            email_input.send_keys(email)
            
            # Click next
            next_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[type='submit']"))
            )
            next_btn.click()
            
            # Wait for password field
            time.sleep(2)
            
            # Enter password
            pwd_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[type='password']"))
            )
            pwd_input.send_keys(password)
            
            # Click sign in
            sign_in_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "[type='submit']"))
            )
            sign_in_btn.click()
            
            # Handle "Stay signed in?" prompt if it appears
            try:
                stay_signed_in_btn = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "[value='Yes']"))
                )
                stay_signed_in_btn.click()
            except:
                pass
            
            # Wait for login to complete
            time.sleep(5)
            
            # Verify login success
            return self._verify_session()
            
        except Exception as e:
            print(f"Login failed: {str(e)}")
            return False

    def _get_logged_in_email(self):
        """Get the email of the logged-in Teams account."""
        try:
            self.driver.get(self.verify_url)
            email_element = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".profile-email"))
            )
            return email_element.text
        except Exception:
            return None

    def _join_via_app(self, url=None, meeting_id=None, password=None):
        """Join a Teams meeting using the desktop app."""
        if url:
            app_path = self.platform_manager.get_app_path("teams")
            subprocess.Popen([app_path, "--url", url])

    def _join_via_browser(self, url=None, meeting_id=None, password=None):
        """Join a Teams meeting via browser."""
        try:
            self._setup_driver()
            
            if not url:
                raise ValueError("Teams meetings require a URL")
            
            self.driver.get(url)
            
            # Wait for and click "Join now" button
            join_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-tid='join-btn']"))
            )
            join_btn.click()
            
        except Exception as e:
            print(f"Error joining Teams meeting: {str(e)}")
            self._cleanup()
            raise

def get_handler(platform: str) -> MeetingHandler:
    """Factory function to get the appropriate meeting handler."""
    handlers = {
        "zoom": ZoomHandler,
        "teams": TeamsHandler
    }
    
    handler_class = handlers.get(platform.lower())
    if not handler_class:
        raise ValueError(f"Unsupported platform: {platform}")
    
    return handler_class() 