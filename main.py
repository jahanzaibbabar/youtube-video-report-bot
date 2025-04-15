#!/usr/bin/env python3
"""
YouTube Video Reporting Tool

This script automates reporting YouTube videos for various violations using undetected-chromedriver.
It provides a command-line interface for users to specify the video URL and report type.
The tool is designed to work with the latest YouTube UI and reporting process while mimicking human behavior.
"""

import argparse
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime
from urllib.parse import urlparse, parse_qs

import requests
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementClickInterceptedException,
    WebDriverException,
    StaleElementReferenceException,
    SessionNotCreatedException,
    InvalidArgumentException
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('youtube_reporter.log')
    ]
)
logger = logging.getLogger('youtube_reporter')

# Create directory for screenshots if it doesn't exist
SCREENSHOTS_DIR = 'screenshots'
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# Report type mapping - Updated for latest YouTube reporting options
REPORT_TYPES = {
    "sexual": "Sexual content",
    "violent": "Violent or repulsive content",
    "hateful": "Hateful or abusive content",
    "harmful": "Harmful or dangerous acts",
    "harassment": "Harassment or bullying",
    "spam": "Spam or misleading",
    "legal": "Legal issues", 
    "child": "Child abuse",
    "terrorism": "Promotes terrorism",
    "misinformation": "Misinformation",
    "copyright": "Infringes my rights"
}

class YouTubeReporter:
    """Class to handle YouTube video reporting automation using undetected-chromedriver."""
    
    def __init__(self, headless=True, cookies_path=None, additional_details=None):
        """
        Initialize the YouTube reporter.
        
        Args:
            headless (bool): Whether to run the browser in headless mode
            cookies_path (str): Path to a file containing cookies for authentication
            additional_details (str): Additional details to provide in the report
        """
        self.driver = None
        self.headless = headless
        self.cookies_path = cookies_path
        self.additional_details = additional_details
        self.wait_time = 10  # Default wait time in seconds
        self.screenshots_taken = 0

    def setup_driver(self):
        """Set up and configure the undetected ChromeDriver."""
        try:
            # Take a timestamp for the screenshot filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Configure undetected-chromedriver options
            options = uc.ChromeOptions()
            if self.headless:
                options.add_argument("--headless=new")  # Updated headless mode syntax
            
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--window-size=1920,1080")
            
            current_dir = os.getcwd()
            # Join the current directory path with the desired folder name for user data
            user_data_dir = os.path.join(current_dir, "chrome_profile")

            # Ensure the user data directory exists; if not, create it.
            if not os.path.exists(user_data_dir):
                os.makedirs(user_data_dir)
                print(f"Created user data directory at: {user_data_dir}")

            # Set up Chrome options with the persistent user data directory.
            options.add_argument(f"--user-data-dir={user_data_dir}")
            
            # Create the undetected ChromeDriver
            try:
                self.driver = uc.Chrome(options=options)
                self.driver.implicitly_wait(self.wait_time)
                logger.info("Undetected ChromeDriver initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize undetected ChromeDriver: {str(e)}")
                # Try to save a screenshot if an error occurs during initialization
                try:
                    error_screenshot_path = os.path.join(SCREENSHOTS_DIR, f"driver_init_error_{timestamp}.png")
                    self.driver.save_screenshot(error_screenshot_path)
                    logger.info(f"Saved error screenshot to {error_screenshot_path}")
                except:
                    logger.error("Could not save error screenshot during driver initialization")
                return False
            
            # Load cookies if provided
            if self.cookies_path and os.path.exists(self.cookies_path):
                try:
                    with open(self.cookies_path, 'r') as f:
                        cookies = json.load(f)
                    
                    # First navigate to YouTube domain to set cookies
                    self.driver.get("https://www.youtube.com")
                    self.human_like_delay()
                    
                    # Add the cookies to the driver
                    for cookie in cookies:
                        try:
                            self.driver.add_cookie(cookie)
                        except Exception as e:
                            logger.debug(f"Error adding cookie: {str(e)}")
                    
                    logger.info("Cookies loaded successfully")
                except Exception as e:
                    logger.error(f"Error loading cookies: {str(e)}")
            
            return True
            
        except SessionNotCreatedException as e:
            logger.error(f"Failed to create a new ChromeDriver session: {str(e)}")
            logger.info("This may be due to a Chrome version mismatch. Try updating your Chrome browser.")
            return False
            
        except WebDriverException as e:
            logger.error(f"Failed to initialize ChromeDriver: {str(e)}")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error during driver setup: {str(e)}")
            return False

    def human_like_delay(self, min_seconds=0.5, max_seconds=2.5):
        """Add a random delay to mimic human behavior."""
        delay = random.uniform(min_seconds, max_seconds)
        time.sleep(delay)

    def take_screenshot(self, name_suffix=""):
        """Take a screenshot and save it with a timestamp."""
        if not self.driver:
            return
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.screenshots_taken += 1
            filename = f"{timestamp}_{self.screenshots_taken:03d}_{name_suffix}.png"
            screenshot_path = os.path.join(SCREENSHOTS_DIR, filename)
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"Screenshot saved to {screenshot_path}")
        except Exception as e:
            logger.error(f"Failed to take screenshot: {str(e)}")

    def validate_youtube_url(self, url):
        """
        Validate if the provided URL is a valid YouTube video URL.
        
        Args:
            url (str): The URL to validate
            
        Returns:
            str: The video ID if valid, None otherwise
        """
        try:
            # Check if URL is reachable
            response = requests.head(url, timeout=5)
            response.raise_for_status()
            
            # Parse the URL
            parsed_url = urlparse(url)
            
            # Check if it's a YouTube domain
            if 'youtube.com' in parsed_url.netloc:
                # For standard YouTube URLs (youtube.com/watch?v=...)
                if parsed_url.path == '/watch':
                    query = parse_qs(parsed_url.query)
                    if 'v' in query:
                        return query['v'][0]
            
            # For youtu.be URLs
            elif 'youtu.be' in parsed_url.netloc:
                # Extract video ID from path
                video_id = parsed_url.path.strip('/')
                if video_id:
                    return video_id
            
            logger.error(f"Invalid YouTube URL format: {url}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error validating URL: {str(e)}")
            return None

    def human_like_scroll(self, direction='down', distance=None):
        """Scroll the page in a human-like manner."""
        if not self.driver:
            return
            
        try:
            if direction == 'down':
                # If no specific distance, use a random scroll distance
                if not distance:
                    distance = random.randint(200, 500)
                self.driver.execute_script(f"window.scrollBy(0, {distance});")
            elif direction == 'up':
                if not distance:
                    distance = random.randint(100, 300)
                self.driver.execute_script(f"window.scrollBy(0, -{distance});")
            self.human_like_delay(0.1, 0.5)
        except Exception as e:
            logger.debug(f"Error during scrolling: {str(e)}")

    def navigate_to_video(self, video_url):
        """
        Navigate to the YouTube video page.
        
        Args:
            video_url (str): The URL of the YouTube video
            
        Returns:
            bool: True if navigation was successful, False otherwise
        """
        try:
            self.driver.get(video_url)
            logger.info(f"Navigated to: {video_url}")
            
            # Take a screenshot after navigation
            # self.take_screenshot("video_page")
            
            # Wait for the video page to load with human-like behavior
            self.human_like_delay(1.0, 3.0)
            
            # Scroll down slightly like a human would
            self.human_like_scroll()
            
            # Wait for the video element to be present
            WebDriverWait(self.driver, self.wait_time).until(
                EC.presence_of_element_located((By.TAG_NAME, "video"))
            )
            
            return True
            
        except TimeoutException:
            logger.error("Timeout while waiting for video page to load")
            self.take_screenshot("video_load_timeout")
            return False
            
        except WebDriverException as e:
            logger.error(f"Error navigating to video: {str(e)}")
            self.take_screenshot("navigation_error")
            return False

    def open_report_dialog(self):
        """
        Open the report dialog by clicking the appropriate buttons.
        Updated for the latest YouTube UI layout with human-like behavior.
        
        Returns:
            bool: True if the dialog was opened successfully, False otherwise
        """
        try:
            # Wait for the page to fully load with human-like delay
            # self.human_like_delay(2.0, 4.0)
            
            # # Take screenshot before attempting to open dialog
            # self.take_screenshot("before_report_dialog")
            
            # First attempt to dismiss any popups that might interfere
            try:
                dismiss_buttons = self.driver.find_elements(By.XPATH, "//button[contains(text(), 'Dismiss') or contains(text(), 'No thanks')]")
                for button in dismiss_buttons:
                    try:
                        if button.is_displayed():
                            button.click()
                            logger.info("Dismissed a popup")
                            self.human_like_delay()
                    except:
                        pass
            except:
                pass
            
            wait = WebDriverWait(self.driver, self.wait_time)
            
            # # First try to find 'More actions' in the player controls area
            # # Updated selectors for different UI versions
            # player_selectors = [
            #     "button[aria-label='More actions']",
            #     "button.ytp-button[aria-label='More actions']",
            #     "button.ytp-menubutton[aria-label='More actions']",
            #     "//button[contains(@aria-label, 'More actions')]",
            #     "//button[contains(@aria-label, 'more options')]",
            #     "//button[contains(@aria-label, 'menu')]",
            #     "//button[contains(@title, 'More actions')]",
            #     "//div[contains(@class, 'dropdown-trigger')]//button",
            #     "//div[contains(@id, 'menu')]//button"
            # ]
            
            # more_actions_button = None
            # for selector in player_selectors:
            #     try:
            #         if '/' in selector:  # XPath
            #             elements = self.driver.find_elements(By.XPATH, selector)
            #             for element in elements:
            #                 try:
            #                     # Try to make element visible and clickable
            #                     self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            #                     self.human_like_delay(0.2, 0.6)
            #                     if element.is_displayed() and element.is_enabled():
            #                         more_actions_button = element
            #                         break
            #                 except:
            #                     continue
            #         else:  # CSS selector
            #             elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            #             for element in elements:
            #                 try:
            #                     # Try to make element visible and clickable
            #                     self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            #                     self.human_like_delay(0.2, 0.6)
            #                     if element.is_displayed() and element.is_enabled():
            #                         more_actions_button = element
            #                         break
            #                 except:
            #                     continue
                    
            #         if more_actions_button:
            #             break
            #     except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
            #         continue
            
            # If we couldn't find the more actions button in the player, try the "..." button near the title
            # if not more_actions_button:
            # Scroll to the video info/title area
            self.human_like_scroll('down', 200)
            
            # title_menu_selectors = [
            #     "//div[contains(@id, 'menu')]//button",
            #     "//div[contains(@id, 'top-level-buttons')]//button",
            #     "//div[contains(@class, 'metadata')]//button",
            #     "//div[contains(@id, 'menu-container')]//button",
            #     "//yt-icon-button[contains(@class, 'dropdown-trigger')]",
            #     "//ytd-menu-renderer//button",
            #     "//div[contains(@class, 'actions')]//button",
            #     "//ytd-menu-renderer//yt-button-shape//button"
            # ]
            
            
            more_action_xpath = '//yt-button-shape/button[@aria-label="More actions"]'
            element = wait.until(EC.visibility_of_element_located((By.XPATH, more_action_xpath)))
            # for selector in title_menu_selectors:
            
            more_actions_button = self.driver.find_element(By.XPATH, more_action_xpath)
                # try:
                #     elements = self.driver.find_elements(By.XPATH, more_action_xpath)
                #     for element in elements:
                #         try:
                #             # Try to make element visible and clickable
                #             self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                #             self.human_like_delay(0.2, 0.6)
                #             if element.is_displayed() and element.is_enabled():
                #                 more_actions_button = element
                #                 break
                #         except:
                #             continue
                    
                #     if more_actions_button:
                #         break
                # except:
                #     continue
            
            if not more_actions_button:
                # Take a screenshot to help with debugging
                self.take_screenshot("more_actions_not_found")
                logger.error("Could not find any 'More actions' button")
                return False
            
            # Try to click with human-like behavior
            try:
                # Hover over the button first like a human would
                ActionChains(self.driver).move_to_element(more_actions_button).perform()
                self.human_like_delay(0.3, 0.7)
                more_actions_button.click()
            except Exception as e:
                logger.warning(f"Standard click failed: {e}. Trying JavaScript click.")
                self.driver.execute_script("arguments[0].click();", more_actions_button)
            
            logger.info("Clicked 'More actions' button")
            self.human_like_delay(1.0, 2.0)  # Wait for menu to appear
            
            # Take screenshot after clicking more actions
            # self.take_screenshot("after_more_actions")
            
            # Now find and click the 'Report' option
            # report_selectors = [
            #     "//span[contains(text(), 'Report')]/..",
            #     "//yt-formatted-string[contains(text(), 'Report')]/..",
            #     "//div[contains(text(), 'Report')]/..",
            #     "//paper-item[contains(., 'Report')]",
            #     "//tp-yt-paper-item[contains(., 'Report')]",
            #     "//ytd-menu-service-item-renderer[contains(., 'Report')]",
            #     "//ytd-menu-navigation-item-renderer[contains(., 'Report')]",
            #     "//div[@role='menuitem'][contains(., 'Report')]",
            #     "//li[@role='menuitem'][contains(., 'Report')]",
            #     "//a[contains(@href, 'report')]",
            #     "//span[text()='Report']/ancestor::ytd-menu-service-item-renderer"
            # ]
            report_selectors = "//ytd-menu-service-item-renderer//yt-formatted-string[contains(text(), 'Report')]/.."
            
            report_button = self.driver.find_element(By.XPATH, report_selectors)
            
            # report_button = None
            # for selector in report_selectors:
            #     try:
            #         elements = self.driver.find_elements(By.XPATH, selector)
            #         for element in elements:
            #             try:
            #                 if element.is_displayed() and element.is_enabled():
            #                     report_button = element
            #                     break
            #             except:
            #                 continue
                    
            #         if report_button:
            #             break
            #     except:
            #         continue
            
            if not report_button:
                self.take_screenshot("report_option_not_found")
                logger.error("Could not find the 'Report' option in the menu")
                return False
            
            # Try to click with human-like behavior
            try:
                # Hover over the button first like a human would
                ActionChains(self.driver).move_to_element(report_button).perform()
                self.human_like_delay(0.3, 0.7)
                report_button.click()
            except Exception as e:
                logger.warning(f"Standard click failed: {e}. Trying JavaScript click.")
                self.driver.execute_script("arguments[0].click();", report_button)
                
            logger.info("Clicked 'Report' option")
            self.human_like_delay(1.0, 2.0)  # Wait for report dialog to appear
            
            # Take screenshot after clicking report option
            # self.take_screenshot("after_report_click")
            
            # Make sure the report dialog is visible
            report_dialog_selectors = [
                "//yt-formatted-string[contains(text(), 'Report video')]",
            ]
            
            dialog_visible = False
            for selector in report_dialog_selectors:
                try:
                    element = wait.until(EC.visibility_of_element_located((By.XPATH, selector)))
                    if element.is_displayed():
                        dialog_visible = True
                        break
                except:
                    continue
            
            if not dialog_visible:
                self.take_screenshot("report_dialog_not_visible")
                logger.error("Report dialog did not appear")
                return False
            
            logger.info("Report dialog opened successfully")
            return True
            
        except ElementClickInterceptedException as e:
            logger.error(f"Element click was intercepted, possibly by a popup or overlay: {str(e)}")
            self.take_screenshot("click_intercepted")
            try:
                # Try to dismiss any interceptions
                self.driver.execute_script("""
                    var elements = document.querySelectorAll('button, .ytp-ad-skip-button, .ytp-ad-overlay-close-button');
                    for (var i = 0; i < elements.length; i++) {
                        if (elements[i].innerText.includes('Close') || 
                            elements[i].innerText.includes('Dismiss') || 
                            elements[i].innerText.includes('Skip')) {
                            elements[i].click();
                        }
                    }
                """)
            except:
                pass
            return False
            
        except StaleElementReferenceException:
            logger.error("Element reference is stale, the page may have been updated")
            self.take_screenshot("stale_element")
            return False
            
        except (NoSuchElementException, TimeoutException) as e:
            logger.error(f"Could not find report elements: {str(e)}")
            self.take_screenshot("element_not_found")
            return False
            
        except WebDriverException as e:
            logger.error(f"Error opening report dialog: {str(e)}")
            self.take_screenshot("webdriver_error")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error during report dialog opening: {str(e)}")
            self.take_screenshot("unexpected_error")
            return False

    def select_report_reason(self, report_type):
        """
        Select the appropriate report reason based on the user's input.
        Updated for the latest YouTube reporting interface.
        
        Args:
            report_type (str): The type of report to submit
            
        Returns:
            bool: True if the reason was selected successfully, False otherwise
        """
        if report_type not in REPORT_TYPES:
            logger.error(f"Invalid report type: {report_type}")
            logger.info(f"Available report types: {', '.join(REPORT_TYPES.keys())}")
            return False
        
        reason_text = REPORT_TYPES[report_type]
        
        try:
            wait = WebDriverWait(self.driver, self.wait_time)
            
            # Take screenshot before selecting reason
            # self.take_screenshot("before_reason_selection")
            
            # Find and select the appropriate report reason
            # Enhanced patterns to match a wider variety of YouTube UIs
            # reason_patterns = [
            #     f"//span[contains(text(), '{reason_text}')]/..",
            #     f"//yt-formatted-string[contains(text(), '{reason_text}')]/..",
            #     f"//div[contains(text(), '{reason_text}')]/..",
            #     f"//paper-radio-button[contains(., '{reason_text}')]",
            #     f"//tp-yt-paper-radio-button[contains(., '{reason_text}')]",
            #     f"//input[@type='radio']/following::span[contains(text(), '{reason_text}')]/..",
            #     f"//label[contains(., '{reason_text}')]",
            #     f"//div[@role='radio'][contains(., '{reason_text}')]",
            #     f"//div[@role='option'][contains(., '{reason_text}')]"
            # ]
            
            reason_xpath = f'//div[@id="options-select"]//yt-formatted-string[contains(text(), "{reason_text}")]/..'
            
            # If we can't find the exact reason, try finding a close match
            # if report_type == "legal":
            #     reason_patterns.extend([
            #         "//span[contains(text(), 'rights')]/..",
            #         "//div[contains(text(), 'rights')]/..",
            #         "//yt-formatted-string[contains(text(), 'rights')]/.."])
            # elif report_type == "spam":
            #     reason_patterns.extend([
            #         "//span[contains(text(), 'spam')]/..",
            #         "//div[contains(text(), 'spam')]/..",
            #         "//div[contains(text(), 'misleading')]/..",
            #         "//yt-formatted-string[contains(text(), 'spam')]/.."])
            
            # Try to get all possible options for debugging
            try:
                all_options = self.driver.find_elements(By.XPATH, "//paper-radio-button | //tp-yt-paper-radio-button | //input[@type='radio']/.. | //label | //div[@role='radio'] | //div[@role='option']")
                options_text = [opt.text for opt in all_options if opt.is_displayed()]
                logger.debug(f"Available options: {options_text}")
            except:
                pass
            
            reason_element = self.driver.find_element(By.XPATH, reason_xpath)
            
            # reason_element = None
            # for pattern in reason_patterns:
            #     try:
            #         # First try to find all matching elements
            #         elements = self.driver.find_elements(By.XPATH, pattern)
            #         for element in elements:
            #             try:
            #                 # Ensure element is visible and interactable
            #                 self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            #                 self.human_like_delay(0.3, 0.7)
            #                 if element.is_displayed() and element.is_enabled():
            #                     reason_element = element
            #                     break
            #             except:
            #                 continue
                    
            #         if reason_element:
            #             break
                        
            #     except (TimeoutException, NoSuchElementException, StaleElementReferenceException):
            #         continue
            
            if not reason_element:
                self.take_screenshot("reason_option_not_found")
                logger.error(f"Could not find the reason option: {reason_text}")
                return False
            
            # Try to click with human-like behavior
            try:
                # Hover over the element first like a human would
                ActionChains(self.driver).move_to_element(reason_element).perform()
                self.human_like_delay(0.3, 0.7)
                reason_element.click()
            except Exception as e:
                logger.warning(f"Standard click failed: {e}. Trying JavaScript click.")
                self.driver.execute_script("arguments[0].click();", reason_element)
                
            logger.info(f"Selected report reason: {reason_text}")
            self.human_like_delay(1.0, 1.5)  # Wait for UI to update
            
            # sub_option_dropdown_selectors = '//div[@id="options-select"]//yt-formatted-string[contains(text(), "Harmful")]/..//tp-yt-paper-item:nth-child(2)'
            
            # try:
            #     # click on drop down button
            #     self.driver.find_element(By.XPATH, '//*[@id="input-6"]/input').click()
            #     self.human_like_delay(1.0, 1.5)
                
            #     sub_option_dropdown_selectors = '//tp-yt-paper-item[2]'
            #     sub_option = reason_element.find_element(By.XPATH, sub_option_dropdown_selectors)
                
            #     try:
            #         # Hover over the element first like a human would
            #         ActionChains(self.driver).move_to_element(sub_option).perform()
            #         self.human_like_delay(0.3, 0.7)
            #         sub_option.click()
            #     except Exception as e:
            #         logger.warning(f"Standard click failed:. Trying JavaScript click.")
            #         self.driver.execute_script("arguments[0].click();", sub_option)
                    
            #     self.human_like_delay(1.0, 1.5)
            
            # except Exception as e:
            #     logger.warning(f"Standard click failed: {e}. Trying JavaScript click.")
            #     print("No sub option found")
                
            self.driver.find_element(By.XPATH, '//*[@id="submit-button"]/yt-button-shape/button').click()

            
            
            
            # Take screenshot after selecting main reason
            # self.take_screenshot("after_reason_selection")
            
            # Handle additional options or sub-categories if they appear
            # Try to find and select the SECOND sub-option if present (per user's requirement)
            # sub_option_selectors = [
            #     "//paper-radio-button[2]",
            #     "//tp-yt-paper-radio-button[2]",
            #     "//input[@type='radio'][2]/..",
            #     "//div[@role='radio'][2]",
            #     "//ytd-report-reason-content-renderer//paper-radio-button[2]",
            #     "//ytd-report-reason-content-renderer//tp-yt-paper-radio-button[2]"
            # ]
            
            
            
            # # Try to select the second sub-option
            # second_sub_option_found = False
            # for selector in sub_option_selectors:
            #     try:
            #         elements = self.driver.find_elements(By.XPATH, selector)
            #         for element in elements:
            #             try:
            #                 if element.is_displayed() and element.is_enabled():
            #                     # Hover and click like a human
            #                     ActionChains(self.driver).move_to_element(element).perform()
            #                     self.human_like_delay(0.3, 0.7)
            #                     element.click()
            #                     logger.info("Selected second sub-option for the report reason")
            #                     self.human_like_delay(0.8, 1.2)  # Wait for UI to update
            #                     second_sub_option_found = True
            #                     break
            #             except:
            #                 continue
            #     except:
            #         continue
                
                # if second_sub_option_found:
                #     break
            
            # If no second option was found, try the first one as a fallback
            # if not second_sub_option_found:
            #     first_sub_option_selectors = [
            #         "//paper-radio-button[1]",
            #         "//tp-yt-paper-radio-button[1]",
            #         "//input[@type='radio'][1]/..",
            #         "//div[@role='radio'][1]",
            #         "//ytd-report-reason-content-renderer//paper-radio-button[1]",
            #         "//ytd-report-reason-content-renderer//tp-yt-paper-radio-button[1]"
            #     ]
                
            #     for selector in first_sub_option_selectors:
            #         try:
            #             elements = self.driver.find_elements(By.XPATH, selector)
            #             for element in elements:
            #                 try:
            #                     if element.is_displayed() and element.is_enabled():
            #                         # Hover and click like a human
            #                         ActionChains(self.driver).move_to_element(element).perform()
            #                         self.human_like_delay(0.3, 0.7)
            #                         element.click()
            #                         logger.info("Selected first sub-option as fallback")
            #                         self.human_like_delay(0.8, 1.2)  # Wait for UI to update
            #                         break
            #                 except:
            #                     continue
            #         except:
            #             continue
            
            # Take screenshot after selecting sub-option (if any)
            # self.take_screenshot("after_sub_option_selection")
            
            return True
            
        except ElementClickInterceptedException as e:
            logger.error(f"Element click was intercepted: {e}")
            self.take_screenshot("reason_click_intercepted")
            try:
                # Try to dismiss any interceptions
                self.driver.execute_script("""
                    var elements = document.querySelectorAll('button, .ytp-ad-skip-button');
                    for (var i = 0; i < elements.length; i++) {
                        if (elements[i].innerText.includes('Close') || 
                            elements[i].innerText.includes('Dismiss') || 
                            elements[i].innerText.includes('Skip')) {
                            elements[i].click();
                        }
                    }
                """)
            except:
                pass
            return False
            
        except StaleElementReferenceException as e:
            logger.error(f"Element reference is stale: {e}")
            self.take_screenshot("reason_stale_element")
            return False
            
        except (NoSuchElementException, TimeoutException) as e:
            logger.error(f"Could not select report reason: {e}")
            self.take_screenshot("reason_element_not_found")
            return False
            
        except WebDriverException as e:
            logger.error(f"WebDriver error selecting reason: {e}")
            self.take_screenshot("reason_webdriver_error")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error selecting report reason: {e}")
            self.take_screenshot("reason_unexpected_error")
            return False

    def submit_report(self):
        """
        Submit the report by clicking the submit button and providing additional details if needed.
        Updated for the latest YouTube reporting flow with additional details text area.
        
        Returns:
            bool: True if the report was submitted successfully, False otherwise
        """
        try:
            wait = WebDriverWait(self.driver, self.wait_time)
            max_attempts = 10  # Maximum number of button clicks to prevent infinite loops
            attempts = 0
            
            
            # wait human
            self.human_like_delay(1.0, 2.0)
            
            # enter text in textarea //*[@id="textarea"]
            self.driver.find_element(By.XPATH, '//*[@id="textarea"]').send_keys(self.additional_details)
            self.human_like_delay(1.0, 2.0)
            
            # report //*[@id="submit-button"]/yt-button-renderer/yt-button-shape/button
            self.driver.find_element(By.XPATH, '//*[@id="submit-button"]/yt-button-renderer/yt-button-shape/button').click()
            
            self.human_like_delay(1.0, 2.0)
            
            # Take screenshot after clicking submit
            self.take_screenshot("final_after_submit_click")
            return True
            
            # # Find and click the Next/Submit buttons until the report is completed
            # while attempts < max_attempts:
            #     attempts += 1
                
            #     # Take a screenshot for debugging before looking for buttons
            #     self.take_screenshot(f"submit_attempt_{attempts}")
                
            #     # Check for text area to enter additional details (per user's requirement)
            #     text_area_found = False
            #     text_area_selectors = [
            #         "//textarea",
            #         "//textarea[@placeholder]",
            #         "//textarea[contains(@aria-label, 'details')]",
            #         "//input[@type='text' and contains(@placeholder, 'details')]",
            #         "//div[@role='textbox']"
            #     ]
                
            #     for selector in text_area_selectors:
            #         try:
            #             elements = self.driver.find_elements(By.XPATH, selector)
            #             for element in elements:
            #                 try:
            #                     if element.is_displayed():
            #                         # Scroll to the text area
            #                         self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            #                         self.human_like_delay(0.5, 1.0)
                                    
            #                         # Clear any existing text and focus the field
            #                         element.clear()
            #                         element.click()
            #                         self.human_like_delay(0.3, 0.7)
                                    
            #                         # Determine what text to enter
            #                         text_to_enter = self.additional_details if self.additional_details else "This content violates community guidelines and is inappropriate."
                                    
            #                         # Type the text like a human would - character by character with slight delays
            #                         for char in text_to_enter:
            #                             element.send_keys(char)
            #                             self.human_like_delay(0.03, 0.15)  # Very short delays between keystrokes
                                    
            #                         logger.info("Entered additional details in text area")
            #                         self.human_like_delay(0.8, 1.2)
            #                         text_area_found = True
                                    
            #                         # Take screenshot after entering details
            #                         self.take_screenshot("after_entering_details")
            #                         break
            #                 except:
            #                     continue
            #         except:
            #             continue
                    
            #         if text_area_found:
            #             break
                
            #     # Enhanced button patterns for the latest YouTube UI
            #     button_patterns = [
            #         # Submit buttons
            #         "//button[contains(@aria-label, 'Submit')]",
            #         "//button[contains(text(), 'Submit')]",
            #         "//button[contains(., 'Submit')]",
            #         "//paper-button[contains(text(), 'Submit')]",
            #         "//tp-yt-paper-button[contains(text(), 'Submit')]",
            #         "//yt-button-renderer[contains(., 'Submit')]",
            #         "//div[@role='button'][contains(., 'Submit')]",
                    
            #         # Next buttons
            #         "//button[contains(@aria-label, 'Next')]",
            #         "//button[contains(text(), 'Next')]",
            #         "//button[contains(., 'Next')]",
            #         "//paper-button[contains(text(), 'Next')]",
            #         "//tp-yt-paper-button[contains(text(), 'Next')]",
            #         "//yt-button-renderer[contains(., 'Next')]",
            #         "//div[@role='button'][contains(., 'Next')]",
                    
            #         # Report buttons (sometimes used as final action)
            #         "//button[contains(text(), 'Report')]",
            #         "//button[contains(., 'Report')]",
            #         "//paper-button[contains(text(), 'Report')]",
            #         "//tp-yt-paper-button[contains(text(), 'Report')]",
                    
            #         # Send buttons (sometimes used instead of Submit)
            #         "//button[contains(text(), 'Send')]",
            #         "//button[contains(., 'Send')]",
            #         "//paper-button[contains(text(), 'Send')]",
            #         "//tp-yt-paper-button[contains(text(), 'Send')]",
                    
            #         # Generic buttons that might be used for submission
            #         "//yt-formatted-string[contains(@id, 'submit')]/ancestor::button",
            #         "//yt-formatted-string[contains(@id, 'next')]/ancestor::button",
            #         "//yt-formatted-string[contains(@id, 'report')]/ancestor::button"
            #     ]
                
            #     # Try to find any button in the dialog that might be next/submit/report
            #     found_button = False
            #     for pattern in button_patterns:
            #         try:
            #             elements = self.driver.find_elements(By.XPATH, pattern)
            #             for button in elements:
            #                 try:
            #                     if button.is_displayed() and button.is_enabled():
            #                         # Try to make button visible and interactable
            #                         self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
            #                         self.human_like_delay(0.5, 1.0)
                                    
            #                         try:
            #                             # Hover over the button first like a human would
            #                             ActionChains(self.driver).move_to_element(button).perform()
            #                             self.human_like_delay(0.3, 0.7)
            #                             button.click()
            #                         except Exception as e:
            #                             logger.warning(f"Standard click failed: {e}. Trying JavaScript click.")
            #                             self.driver.execute_script("arguments[0].click();", button)
                                    
            #                         logger.info(f"Clicked button matching pattern: {pattern}")
            #                         found_button = True
            #                         self.human_like_delay(1.5, 2.5)  # Let the UI update
            #                         break
            #                 except:
            #                     continue
                        
            #             if found_button:
            #                 break
            #         except:
            #             continue
                
            #     if not found_button:
            #         # Check if a success message is visible (various formats)
            #         success_patterns = [
            #             "//yt-formatted-string[contains(text(), 'Thanks for reporting')]",
            #             "//div[contains(text(), 'Thanks for reporting')]",
            #             "//span[contains(text(), 'Thanks for reporting')]",
            #             "//div[contains(text(), 'Thank you for reporting')]",
            #             "//yt-formatted-string[contains(text(), 'Thank you for reporting')]",
            #             "//div[contains(text(), 'has been reported')]",
            #             "//yt-formatted-string[contains(text(), 'has been reported')]",
            #             "//div[contains(@class, 'success-message')]",
            #             "//div[contains(@id, 'success')]",
            #             "//p[contains(text(), 'report') and contains(text(), 'received')]"
            #         ]
                    
            #         success_found = False
            #         for pattern in success_patterns:
            #             try:
            #                 elements = self.driver.find_elements(By.XPATH, pattern)
            #                 for element in elements:
            #                     if element.is_displayed():
            #                         logger.info(f"Success message found: {element.text}")
            #                         success_found = True
            #                         break
            #                 if success_found:
            #                     break
            #             except:
            #                 continue
                    
            #         if success_found:
            #             # Take a final success screenshot
            #             self.take_screenshot("report_success")
            #             logger.info("Report submitted successfully")
            #             return True
                    
            #         # If we got here, we couldn't find any more buttons to click
            #         # Check if the report dialog is still visible
            #         try:
            #             dialog_visible = False
            #             dialog_elements = self.driver.find_elements(
            #                 By.XPATH, 
            #                 "//ytd-report-form-modal-renderer | //tp-yt-paper-dialog[contains(., 'Report')]"
            #             )
            #             for element in dialog_elements:
            #                 if element.is_displayed():
            #                     dialog_visible = True
            #                     break
                        
            #             if not dialog_visible:
            #                 # If the dialog is gone without explicit success message, 
            #                 # assume the report was submitted
            #                 self.take_screenshot("dialog_closed")
            #                 logger.info("Report dialog no longer visible, assuming successful submission")
            #                 return True
            #             else:
            #                 # Dialog still visible but no buttons to click
            #                 self.take_screenshot("dialog_stuck")
            #                 logger.error("Report dialog still visible but no buttons found to proceed")
            #                 return False
            #         except:
            #             # If we can't determine dialog state, be optimistic
            #             self.take_screenshot("final_state_unknown")
            #             logger.info("Unable to determine dialog state, assuming successful submission")
            #             return True
                
            #     # If we've made the maximum number of attempts
            #     if attempts >= max_attempts:
            #         self.take_screenshot("max_attempts_reached")
            #         logger.warning(f"Made {max_attempts} button clicks without resolution, stopping")
            #         return False
            
            # return True
            
        except ElementClickInterceptedException as e:
            logger.error(f"Element click was intercepted: {e}")
            self.take_screenshot("submit_click_intercepted")
            try:
                # Try to dismiss any interceptions
                self.driver.execute_script("""
                    var elements = document.querySelectorAll('button, .ytp-ad-skip-button');
                    for (var i = 0; i < elements.length; i++) {
                        if (elements[i].innerText.includes('Close') || 
                            elements[i].innerText.includes('Dismiss') || 
                            elements[i].innerText.includes('Skip')) {
                            elements[i].click();
                        }
                    }
                """)
                # One more attempt after trying to clear obstructions
                button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Submit')]")
                if button and button.is_displayed():
                    button.click()
                    return True
            except:
                pass
            return False
            
        except WebDriverException as e:
            logger.error(f"WebDriver error during report submission: {e}")
            self.take_screenshot("submit_webdriver_error")
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error during report submission: {e}")
            self.take_screenshot("submit_unexpected_error")
            return False

    def report_video(self, video_url, report_type):
        """
        Main method to report a YouTube video.
        
        Args:
            video_url (str): The URL of the YouTube video to report
            report_type (str): The type of report to submit
            
        Returns:
            bool: True if the report was submitted successfully, False otherwise
        """
        success = False
        
        # Validate the YouTube URL
        video_id = self.validate_youtube_url(video_url)
        if not video_id:
            logger.error(f"Invalid YouTube URL: {video_url}")
            return False
        
        # Setup the WebDriver
        if not self.setup_driver():
            return False
        
        try:
            # Navigate to the video
            if not self.navigate_to_video(video_url):
                return False
            
            # Open the report dialog
            if not self.open_report_dialog():
                return False
            
            # Select the report reason
            if not self.select_report_reason(report_type):
                return False
            
            # input ("done?????")
            
            # Submit the report
            success = self.submit_report()
            
            if success:
                logger.info(f"Successfully reported video {video_id} for {report_type}")
                # Take a final screenshot showing the final state
                self.take_screenshot("final_state_success")
            else:
                logger.error(f"Failed to report video {video_id}")
                # Take a screenshot of the failed state
                self.take_screenshot("final_state_failure")
            
        except Exception as e:
            logger.error(f"Unexpected error during reporting: {str(e)}")
            # Take a screenshot of the error state
            self.take_screenshot("unexpected_error")
            success = False
        
        finally:
            # Clean up the driver
            if self.driver:
                self.driver.quit()
                logger.info("WebDriver closed")
            
            return success

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='YouTube Video Reporting Tool')
    
    parser.add_argument('--url', '-u', type=str, required=True,
                        help='The URL of the YouTube video to report')
    
    parser.add_argument('--type', '-t', type=str, required=True,
                        choices=list(REPORT_TYPES.keys()),
                        help='The type of report to submit')
    
    parser.add_argument('--visible', '-v', action='store_true',
                        help='Run in visible mode (not headless)')
    
    parser.add_argument('--cookies', '-c', type=str,
                        help='Path to cookies file for authentication')
    
    parser.add_argument('--details', '-d', type=str,
                        help='Additional details to provide in the report')
    
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    
    return parser.parse_args()

def main():
    """Main entry point for the script."""
    # args = parse_arguments()
    
    # # Set debug logging if requested
    # if args.debug:
    #     logger.setLevel(logging.DEBUG)
    #     for handler in logger.handlers:
    #         handler.setLevel(logging.DEBUG)
    
    # # Display startup information
    # logger.info("YouTube Video Reporting Tool")
    # logger.info(f"Target URL: {args.url}")
    # logger.info(f"Report type: {args.type} ({REPORT_TYPES.get(args.type)})")
    # logger.info(f"Headless mode: {not args.visible}")
    # logger.info(f"Using cookies file: {args.cookies if args.cookies else 'None'}")
    
    url = "https://www.youtube.com/watch?v=vzCqJGO80Is"
    type1 = "misinformation"
    
    # Create the YouTube reporter
    reporter = YouTubeReporter(
        headless=False,
        cookies_path=False,
        additional_details='This content violates community guidelines and is inappropriate.',
    )
    
    # Report the video
    success = reporter.report_video(url, type1)
    
    if success:
        print("\n✅ Video reported successfully!")
        print(f"Screenshots saved to {SCREENSHOTS_DIR}/")
        sys.exit(0)
    else:
        print("\n❌ Failed to report the video. Check the logs for details.")
        print(f"Debug screenshots saved to {SCREENSHOTS_DIR}/")
        sys.exit(1)

if __name__ == "__main__":
    main()