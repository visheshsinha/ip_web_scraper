### Web Scraping India IP Applications

Pre-requisite: Firefox Browser installed

Preferrably use Python 3.9, since it's tested on it, python3.13 (Latest) doesn't have support for pytorch (dep. for easyocr) yet
```
python / python3.9 -m venv venv
source venv/bin/activate
pip / pip3 install -r requirements.txt
mkdir driver
vim .env
```

For tesseract (PS: the one in requirement.txt is just the python wrapper for this OCR)
```
brew install tesseract
```

In `.env`, enter your API key from 2Captcha:
```
API_KEY_2CAPTCHA='your_API_KEY' 
GECKO_DRIVER_PATH='firefox_browser_driver_path'
BASE_URL_IPINDIA='base_URL'
```

In `driver` folder - place your geckodriver executable file
Download from : https://github.com/mozilla/geckodriver/releases
Unpack : 
```
tar -xzvf geckodriver-filename.tar.gz 
```



```
python / python3 main.py
```