from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from twocaptcha import TwoCaptcha
import sys, os, time, uuid, glob, re, pytesseract, easyocr
from PIL import Image,  ImageEnhance, ImageFilter
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

load_dotenv()
GECKO_DRIVER_PATH = os.getenv('GECKO_DRIVER_PATH')
API_KEY_2CAPTCHA = os.getenv('API_KEY_2CAPTCHA')
BASE_URL_IPINDIA = os.getenv('BASE_URL_IPINDIA')

# out of service - not using anymore
def solve_captcha_using_2CAPTCHA(image_path):
    solver = TwoCaptcha(API_KEY_2CAPTCHA)
    try:
        result = solver.normal(image_path)
    except Exception as e:
        print("Failed to solve CAPTCHA:", e)
        sys.exit(e)
    else:
        print("CAPTCHA Solved: ", result['code'])
        return result['code']

def preprocess_image_for_enhancement(image_path): # not much help
    try:
        image = Image.open(image_path)
        gray_image = image.convert('L')
        enhancer = ImageEnhance.Contrast(gray_image)
        contrast_image = enhancer.enhance(2.0)
        sharpened = contrast_image.filter(ImageFilter.EDGE_ENHANCE)
        threshold = 200
        binary_image = sharpened.point(lambda x: 0 if x < threshold else 255, '1')
        binary_image.save(f'binary_image_{image_path}.png')
        return binary_image
    except Exception as e:
        print(f"Preprocessing error: {e}")
        return None

def solve_captcha_using_tesseract(image_path):
    try:
        processed_image = preprocess_image_for_enhancement(image_path)
        print(type(processed_image))
        text = pytesseract.image_to_string(image=processed_image, config='--psm 6', lang='eng')
    except Exception as e:
        print("Failed to solve CAPTCHA:", e)
        sys.exit(e)
    else:
        result = text.strip()
        print("CAPTCHA Solved: ", result)
        return result

def solve_captcha_using_easyocr(image_path):
    try:
        reader = easyocr.Reader(['en'])
        result = reader.readtext(image_path)
    except Exception as e:
        print("Failed to solve CAPTCHA:", e)
        sys.exit(e)
    else:
        print("CAPTCHA Solved: ", result[0][1])
        return result[0][1]


def scrape_application_data(app_number, unique_image_uuid):
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
        # solved using taking screenshot & cropping it
        # CaptchaURL : https://tmrsearch.ipindia.gov.in/eregister/captcha.ashx
        captcha_image_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "ImageCaptcha"))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", captcha_image_element)
        location = captcha_image_element.location
        size = captcha_image_element.size
        driver.save_screenshot(f"screenshot_{unique_image_uuid}.png")

        x = location['x']
        y = location['y']
        w = size['width']
        h = size['height']

        width = x + w
        height = y + h
        image = Image.open(f"screenshot_{unique_image_uuid}.png")

        # uncomment next line & comment next-2-next line if you want to run GUI !!!
        # image = image.crop((int(x) + 650, int(y) + 100, int(width)+800, int(height) + 130))
        image = image.crop((int(x), int(y), int(width), int(height)))
        image.save(f"captcha_{unique_image_uuid}.png")

        captcha_solution = solve_captcha_using_easyocr(f"captcha_{unique_image_uuid}.png")

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
        # print(type(raw_application_data), raw_application_data)

        # Next Steps:
            # 1. Structure this data into tabular / JSON format
            # 2. feed into DB

        driver.close()
        return raw_application_data

    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        driver.quit()


#### Future Plan
    # 1. make the ranges dynamic 
    # 2. Add error Handling & re-try mechanism / keep log
    # 3. to be fetched as per last run from DB

def parse_raw_data(raw_data):
    data = {}
    data['as_on_date'] = re.search(r'As on Date\s*:\s*(.*)', raw_data).group(1).strip()
    data['status'] = re.search(r'Status\s*:\s*(.*)', raw_data).group(1).strip()
    data['tm_application_no'] = re.search(r'TM Application No\.\s*(\d+)', raw_data).group(1).strip()
    data['class'] = re.search(r'Class\s*(\d+)', raw_data).group(1).strip()
    data['date_of_application'] = re.search(r'Date of Application\s*(.*)', raw_data).group(1).strip()
    data['appropriate_office'] = re.search(r'Appropriate Office\s*(.*)', raw_data).group(1).strip()
    data['state'] = re.search(r'State\s*(.*)', raw_data).group(1).strip()
    data['country'] = re.search(r'Country\s*(.*)', raw_data).group(1).strip()
    data['filing_mode'] = re.search(r'Filing Mode\s*(.*)', raw_data).group(1).strip()
    data['tm_applied_for'] = re.search(r'TM Applied For\s*(.*)', raw_data).group(1).strip()
    data['tm_category'] = re.search(r'TM Category\s*(.*)', raw_data).group(1).strip()
    data['trade_mark_type'] = re.search(r'Trade Mark Type\s*(.*)', raw_data).group(1).strip()
    data['user_detail'] = re.search(r'User Detail\s*(.*)', raw_data).group(1).strip()
    data['certificate_no'] = re.search(r'Certificate No\.\s*(\d+)', raw_data).group(1).strip()
    data['certificate_date'] = re.search(r'Dated\s*:\s*(.*)', raw_data).group(1).strip()
    data['valid_upto'] = re.search(r'Valid upto/ Renewed upto\s*(.*)', raw_data).group(1).strip()
    data['proprietor_name'] = re.search(r'Proprietor name\s*\(1\)\s*(.*)', raw_data).group(1).strip()
    data['body_incorporate'] = re.search(r'Body Incorporate\s*(.*)', raw_data).group(1).strip()
    data['proprietor_address'] = re.search(r'Proprietor Address\s*(.*)', raw_data).group(1).strip()
    data['email_id'] = re.search(r'Email Id\s*(.*)', raw_data).group(1).strip()
    data['agent_name'] = re.search(r'Agent name\s*(.*)', raw_data).group(1).strip()
    data['agent_address'] = re.search(r'Agent Address\s*(.*)', raw_data).group(1).strip()
    data['goods_service_details'] = re.search(r'Goods & Service Details\s*\[CLASS : \d+\]\s*(.*)', raw_data).group(1).strip()
    data['publication_details'] = re.search(r'Publication Details\s*Published in Journal No\.\s*:\s*(.*)', raw_data).group(1).strip()
    data['publication_date'] = re.search(r'Dated\s*:\s*(.*)', raw_data).group(1).strip()

    return data

def scrape_application_data_range(start, end):
    for app_number in range(start, end):
        print(f"Scraping application number: {app_number}")
        unique_image_uuid = uuid.uuid4() # To avoid race cond.n while multithreading

        try:
            raw_data = scrape_application_data(app_number, unique_image_uuid)
            data = parse_raw_data(raw_data)
            if data:
                print(f"Data for application number {app_number}: {data}")
            time.sleep(1)
        except Exception as e:
            print(f"Error in scapping data for application {app_number}, error: {e}")

        

def cleanup_png_files():
    png_files = glob.glob("*.png")
    for file in png_files:
        try:
            os.remove(file)
            print(f"Deleted file: {file}")
        except Exception as e:
            print(f"Error deleting file {file}: {e}")

if __name__ == "__main__":
    # ranges for multithreading
    ranges = [(1111000, 1111011), (1111011, 1111022), (1111022, 1111033)]

    with ThreadPoolExecutor(max_workers=len(ranges)) as executor:
        futures = [executor.submit(scrape_application_data_range, start, end) for start, end in ranges]

    for future in futures:
        try:
            future.result()
        except Exception as e:
            print(f"Error in thread: {e}")

    cleanup_png_files()


    