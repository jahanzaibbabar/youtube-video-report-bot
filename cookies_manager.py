from selenium import webdriver
from selenium.webdriver.common.by import By
from time import sleep
import json
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc


url = 'https://www.youtube.com/'

# save cookies
def save_cookies(website_url):
    driver = webdriver.Chrome()
    driver.get(website_url)

    # manually login the website 
    # when done press enter

    input("press enter!")

    cookies = driver.get_cookies()
    with open('cookies.json', 'w') as cookies_file:
        json.dump(cookies, cookies_file)

    print(cookies)
    driver.close()


# save_cookies(url)


#############################################################
# loading cookies
def load_cookies():
    def domain_to_url(domain: str) -> str:
        if domain.startswith(".") and "www" not in domain:
            domain = "www" + domain
            return "https://" + domain
        elif "www" in domain and domain.startswith("."):
            domain = domain[1:]
            return "https://" + domain
        else:
            return "https://" + domain

    def login_using_cookie_file(driver, cookie_file):
        """Restore auth cookies from a file. Does not guarantee that the user is logged in afterwards.
        Visits the domains specified in the cookies to set them, the previous page is not restored."""
        domain_cookies = {}
        with open(cookie_file) as file:
            cookies = json.load(file)

            # Sort cookies by domain, because we need to visit to domain to add cookies
            for cookie in cookies:
                try:
                    domain_cookies[cookie["domain"]].append(cookie)
                except KeyError:
                    domain_cookies[cookie["domain"]] = [cookie]

        for domain, cookies in domain_cookies.items():
            driver.get(domain_to_url(domain + "/robots.txt"))
            for cookie in cookies:
                try:
                    driver.add_cookie(cookie)
                except:
                    print(f"Couldn't set cookie {cookie['name']} for {domain}")
        return True



    chrome_options = Options()

    # Add options for running in headless mode
    chrome_options.add_argument('--headless')  # Run Chrome in headless mode
    chrome_options.add_argument('--disable-gpu')  # Disable GPU acceleration (necessary in headless mode sometimes)
    chrome_options.add_argument('--no-sandbox')  # Run without sandboxing (useful for running in certain server environments)
    chrome_options.add_argument('--disable-dev-shm-usage')  # Overcome limited resource problems
    chrome_options.add_argument('--window-size=1920x1080')  # Set window size for headless mode
    chrome_options.add_argument('--disable-extensions')  # Disable extensions
    chrome_options.add_argument('--disable-infobars')  # Disable infobars
    chrome_options.add_argument('--start-maximized')  # Start maximized
    chrome_options.add_argument('--disable-popup-blocking')  # Disable popup blocking
    chrome_options.add_argument('--disable-notifications')  # Disable notifications
    
    
    # Set up the WebDriver with the specified options
    # driver = webdriver.Chrome(options=chrome_options)
    driver = uc.Chrome(options=chrome_options, version_main=131)
    login_using_cookie_file(driver, "cookies.json")

    return driver


