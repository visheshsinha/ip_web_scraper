### Web Scraping India IP Applications

Pre-requisite: Firefox Browser installed

```
python / python3 -m venv venv
pip / pip3 install -r requirements.txt
mkdir driver
vim .env
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