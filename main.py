from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from twocaptcha import TwoCaptcha
import sys
import os
import time
import requests
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()
GECKO_DRIVER_PATH = os.getenv('GECKO_DRIVER_PATH')
API_KEY_2CAPTCHA = os.getenv('API_KEY_2CAPTCHA')
BASE_URL_IPINDIA = os.getenv('BASE_URL_IPINDIA')

def solve_captcha():
    solver = TwoCaptcha(API_KEY_2CAPTCHA)
    try:
        result = solver.normal('captcha_image.png')
    except Exception as e:
        print("Failed to solve CAPTCHA.")
        sys.exit(e)
    else:
        print("CAPTCHA Solved: ", result['code'])
        return result['code']

def scrape_application_data(app_number):
    options = Options()
    options.add_argument('--headless') # comment out to view the GUI
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Firefox(service=Service(GECKO_DRIVER_PATH), options=options)
    driver.get(BASE_URL_IPINDIA)

    try:
        select_national_appNum = driver.find_element(By.ID, "rdb_0")
        select_national_appNum.click()

        # getting a race condition here - captcha.ashx is getting dynamically updated while being fetched
        # CaptchaURL : https://tmrsearch.ipindia.gov.in/eregister/captcha.ashx
        captcha_image_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ImageCaptcha"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", captcha_image_element)
        location = captcha_image_element.location
        size = captcha_image_element.size
        driver.save_screenshot("screenshot.png")

        x = location['x']
        y = location['y']
        w = size['width']
        h = size['height']

        width = x + w
        height = y + h
        image_path = 'captcha_image.png'
        image = Image.open('screenshot.png')

        # uncomment next line & comment next-2-next line if you want to run GUI !!!
        # image = image.crop((int(x) + 650, int(y) + 100, int(width)+800, int(height) + 130))
        image = image.crop((int(x), int(y), int(width), int(height)))
        image.save(image_path)

        # captcha_image_url = captcha_image_element.get_attribute('src')
        captcha_solution = solve_captcha()

        if not captcha_solution:
            return None

        app_number_field = driver.find_element(By.NAME, "applNumber")
        captcha_field = driver.find_element(By.NAME, "captcha1")

        app_number_field.send_keys(str(app_number))
        captcha_field.send_keys(captcha_solution)

        submit_button = driver.find_element(By.ID, "btnView")
        submit_button.click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "SearchWMDatagrid_ctl03_lnkbtnappNumber1"))
        )

        found_application = driver.find_element(By.ID, "SearchWMDatagrid_ctl03_lnkbtnappNumber1")
        found_application.click()

        raw_application_data = driver.find_element(By.XPATH, "/html/body").text
        print(raw_application_data)
        # Next Steps:
            # 1. Structure this data into tabular / JSON format
            # 2. feed into DB

        driver.close()
        return

    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        driver.quit()


#### Future Plan
    # 1. make the ranges dynamic 
    # 2. Add error Handling & re-try mechanism / keep log
    # 3. to be fetched as per last run from DB

if __name__ == "__main__":
    for app_number in range(1111000, 1111003): # running only one application number now
        print(f"Scraping application number: {app_number}")
        data = scrape_application_data(app_number)
        if data:
            print(f"Data for application number {app_number}: {data}")
        
        time.sleep(1)
