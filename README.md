# Download LingQs from LingQ.com
This is a simple python script to download all LingQs (saved vocabulary) from LingQ.com as CSV and JSON files.

# Limitations
The LingQ API has built in rate limitation, so the download can take some time (minutes to hours depending on how many you have saved).

# Requirements
You’ll need an API key, which you can find [here](https://www.lingq.com/en/accounts/apikey/). 

# Instructions
Download the script [here](https://github.com/tomtom800/lingq_downloader/archive/refs/heads/main.zip). Extract the zip. 

Find lingq_downloader.py and move it to the folder you want to use. Open Terminal. Point Terminal to this folder, e.g. `cd ~/Downloads`.
Make the script executable: `chmod +x lingq_downloader.py`

The next Terminal command depends on your intended outputs:

Download all LingQs from all languages: `python3 lingq_downloader.py --api-key YOUR_API_KEY_HERE`

Download specific languages only: `python3 lingq_downloader.py --api-key YOUR_API_KEY_HERE --languages en es fr`

Only download a CSV file: `python3 lingq_downloader.py --api-key YOUR_API_KEY_HERE --format csv`

Only download a JSON file: `python3 lingq_downloader.py --api-key YOUR_API_KEY_HERE --format json`