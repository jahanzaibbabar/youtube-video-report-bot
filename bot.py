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
SCREENSHOTS_DIR = 'static/screenshots'
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)
latest_screenshot = None

# Report type mapping - Updated for latest YouTube reporting options
REPORT_TYPES = {
    "sexual": "Sexual content",
    "violent": "Violent or repulsive content",
    "hateful": "Hateful or abusive content",
    "harmful": "Harmful or dangerous acts",
    "harassment": "Harassment or bullying",
    "spam": "Spam or misleading",
    "legal": "Legal issue", 
    "child": "Child abuse",
    "terrorism": "Promotes terrorism",
    "misinformation": "Misinformation",
}

not_sub_option = ['child', 'terrorism', 'misinformation']

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
            global latest_screenshot
            latest_screenshot = screenshot_path
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
            
            
            self.human_like_scroll('down', 200)
            
            self.human_like_delay(4.0, 6.0)  # Wait for the page to settle
            
            more_action_xpath = '//yt-button-shape/button[@aria-label="More actions"]'
            element = wait.until(EC.visibility_of_element_located((By.XPATH, more_action_xpath)))
            # for selector in title_menu_selectors:
            
            more_actions_button = self.driver.find_element(By.XPATH, more_action_xpath)
                
            
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
                # self.driver.execute_script("arguments[0].click();", more_actions_button)
                self.take_screenshot("more_actions_click_error")
                return False
            
            logger.info("Clicked 'More actions' button")
            self.human_like_delay(1.0, 2.0)  # Wait for menu to appear
            
           
            report_selectors = "//ytd-menu-service-item-renderer//yt-formatted-string[contains(text(), 'Report')]/.."
            
            report_button = self.driver.find_element(By.XPATH, report_selectors)
            
            
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
                # self.driver.execute_script("arguments[0].click();", report_button)
                self.take_screenshot("report_option_click_error")
                return False
                
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

            
           
            # # Try to get all possible options for debugging
            # try:
            #     all_options = self.driver.find_elements(By.XPATH, "//paper-radio-button | //tp-yt-paper-radio-button | //input[@type='radio']/.. | //label | //div[@role='radio'] | //div[@role='option']")
            #     options_text = [opt.text for opt in all_options if opt.is_displayed()]
            #     logger.debug(f"Available options: {options_text}")
            # except:
            #     pass
            
            reason_xpath = f'//div[@id="options-select"]//yt-formatted-string[contains(text(), "{reason_text}")]/..'
            reason_element = self.driver.find_element(By.XPATH, reason_xpath)
            
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
                logger.warning(f"Standard click failed: {e}. ")
                # self.driver.execute_script("arguments[0].click();", reason_element)
                self.take_screenshot("reason_option_click_error")
                return False
                
            logger.info(f"Selected report reason: {reason_text}")
            self.human_like_delay(1.0, 1.5)  # Wait for UI to update
            
            # sub_option_dropdown_selectors = '//div[@id="options-select"]//yt-formatted-string[contains(text(), "Harmful")]/..//tp-yt-paper-item:nth-child(2)'
            #######################################
            
            if report_type not in not_sub_option:
                # click on drop down button
                try:
                    # drop_down_button_xpath = f'//div[@id="options-select"]//yt-formatted-string[contains(text(), "{reason_text}")]/ancestor::tp-yt-paper-radio-button/following-sibling::tp-yt-paper-dropdown-menu[1]//input'
                    drop_down_button_xpath = f'//div[@id="options-select"]//yt-formatted-string[contains(text(), "{reason_text}")]/following::input'
                    self.driver.find_element(By.XPATH, drop_down_button_xpath).click()
                    self.human_like_delay(1.0, 1.5)
                    
                    sub_option_dropdown_selectors = f'//div[@id="options-select"]//yt-formatted-string[contains(text(), "{reason_text}")]/following::tp-yt-iron-dropdown[1]//tp-yt-paper-item[2]'
                    sub_option = reason_element.find_element(By.XPATH, sub_option_dropdown_selectors)
                    
                    try:
                        # Hover over the element first like a human would
                        ActionChains(self.driver).move_to_element(sub_option).perform()
                        self.human_like_delay(0.3, 0.7)
                        sub_option.click()
                    except Exception as e:
                        logger.warning(f"Standard click failed:. Trying JavaScript click.")
                        # self.driver.execute_script("arguments[0].click();", sub_option)
                        self.take_screenshot("sub_option_click_error")
                        return False
                        
                    self.human_like_delay(1.0, 1.5)
                
                except Exception as e:
                    logger.warning(f"Standard click failed: {e}. Trying JavaScript click.")
                    self.take_screenshot("dropdown_click_error")
                    return False
                
            self.driver.find_element(By.XPATH, '//*[@id="submit-button"]/yt-button-shape/button').click()
            
            return True
            
        
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
        
            # Wait for a human-like delay
            self.human_like_delay(1.0, 2.0)
            
            try:
                # Enter text in the textarea if additional details are provided
                if self.additional_details:
                    textarea = self.driver.find_element(By.XPATH, '//*[@id="textarea"]')
                    textarea.clear()  # Clear any pre-filled text
                    textarea.send_keys(self.additional_details)
                    logger.info("Entered additional details in the textarea")
                    self.human_like_delay(1.0, 2.0)
            except NoSuchElementException:
                logger.warning("Textarea for additional details not found. Skipping this step.")
            
            try:
                # Click the submit button
                submit_button = self.driver.find_element(By.XPATH, '//*[@id="submit-button"]/yt-button-renderer/yt-button-shape/button')
                submit_button.click()
                logger.info("Clicked the submit button")
                self.human_like_delay(1.0, 2.0)
            except NoSuchElementException:
                logger.error("Submit button not found. Unable to submit the report.")
                self.take_screenshot("submit_button_not_found")
                return False
            
            # Take a screenshot after clicking submit
            self.take_screenshot("final_after_submit_click")
            return True
    
            
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
            
            
            # Submit the report
            success = self.submit_report()
            
            if success:
                logger.info(f"Successfully reported video {video_id} for {report_type}")
                # Take a final screenshot showing the final state
                self.take_screenshot("final_state_success")
                return True
            else:
                logger.error(f"Failed to report video {video_id}")
                # Take a screenshot of the failed state
                self.take_screenshot("final_state_failure")
                return False
            
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

def report_video(url, report_type, additional_details=''):
    """Main entry point for the script."""
    global latest_screenshot
    latest_screenshot = None
    
    # url = "https://www.youtube.com/watch?v=vzCqJGO80Is"
    # type1 = "misinformation"
    
    # Create the YouTube reporter
    reporter = YouTubeReporter(
        headless=True,
        cookies_path=False,
        additional_details=additional_details,
    )
    
    # Report the video
    success = reporter.report_video(url, report_type)
    
    if success:
        print("\n✅ Video reported successfully!")
        return True, latest_screenshot
    else:
        print("\n❌ Failed to report the video. Check the logs for details.")
        return False, latest_screenshot

if __name__ == "__main__":
    report_video()