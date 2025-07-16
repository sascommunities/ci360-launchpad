import json
import unicodedata
import requests
from flask import current_app
from logger import get_logger

log = get_logger(__name__)

def get_data_url(payload):
    """Extract data file URL from payload"""
    data = json.loads(payload)
    if 'presignedUrls' in data.keys():
        if 'dataFile' in data['presignedUrls'].keys():
            return unicodedata.normalize("NFKD", data['presignedUrls']['dataFile'])
        else:
            log.warning("No data file in presigned URL...")
    else:
        log.warning("No presigned URL object found...")

def get_meta_url(payload):
    """Extract metadata file URL from payload"""
    data = json.loads(payload)
    if 'presignedUrls' in data.keys():
        if 'metadataFile' in data['presignedUrls'].keys():
            return unicodedata.normalize("NFKD", data['presignedUrls']['metadataFile'])
        else:
            log.warning("No metadata file in presigned URL...")
    else:
        log.warning("No presigned URL object found...")

def download_url_content(url):
    """Download content from the given URL"""
    try:
        proxies = None
        if current_app.config['PROXY_URL']:
            proxy_url = current_app.config['PROXY_URL']
            if current_app.config['PROXY_USERNAME'] and current_app.config['PROXY_PASSWORD']:
                proxy_url = proxy_url.replace("://", f"://{current_app.config['PROXY_USERNAME']}:{current_app.config['PROXY_PASSWORD']}@")
            proxies = {
                "http": proxy_url,
                "https": proxy_url,
            }
            log.info(f"Using proxy: {proxy_url}")

        response = requests.get(url, proxies=proxies)
        if response.status_code == 200:
            return response.content
        else:
            log.error(f"Failed to download content from URL: {url}. Status code: {response.status_code}")
            return None
    except Exception as e:
        log.error(f"Error downloading content from URL: {url}. Error: {e}")
        return None
