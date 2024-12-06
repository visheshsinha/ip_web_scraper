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
GECKO_DRIVER_PATH = 'driver/geckodriver'

BASE_URL = 'https://tmrsearch.ipindia.gov.in/eregister/Application_View.aspx'

def solve_captcha(captcha_image_url):
    response = requests.get(captcha_image_url)
    image = Image.open(BytesIO(response.content))
    image_path = 'captcha_image.png'
    image.save(image_path)

    API_KEY = os.getenv('API_KEY_2CAPTCHA')
    solver = TwoCaptcha(API_KEY)

    try:
        result = solver.normal('captcha_image.png')
    except Exception as e:
        print("Failed to solve CAPTCHA.")
        sys.exit(e)
    else:
        sys.exit('solved: ' + str(result))

def scrape_application_data(app_number):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Firefox(service=Service(GECKO_DRIVER_PATH), options=options)
    driver.get(BASE_URL)

    try:
        select_national_appNum = driver.find_element(By.ID, "rdb_0")
        select_national_appNum.click()

        captcha_image_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ImageCaptcha"))
        )

        captcha_image_url = captcha_image_element.get_attribute('src')
        captcha_solution = solve_captcha(captcha_image_url)
        
        print("CAPTCHA::::", captcha_solution)

        if not captcha_solution:
            return None

        app_number_field = driver.find_element(By.NAME, "applNumber")
        captcha_field = driver.find_element(By.NAME, "captcha1")

        app_number_field.send_keys(str(app_number))
        captcha_field.send_keys(captcha_solution)

        submit_button = driver.find_element(By.ID, "btnView")
        submit_button.click()

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "panelgetdetail"))
        )

        result_data = driver.find_element(By.ID, "panelgetdetail").text
        return result_data

    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        driver.quit()


#### Future Plan
    # 1. make the ranges dynamic 
    # 2. to be fetched as per last run from DB

for app_number in range(1111000, 1111001): # running only one application number now
    print(f"Scraping application number: {app_number}")
    data = scrape_application_data(app_number)
    if data:
        print(f"Data for application number {app_number}: {data}")
    
    time.sleep(1)
