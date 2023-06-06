import logging
import os
import time
from urllib.parse import urlparse

import requests

from zscaler_cc_lambda_service.utils.secret_manager import get_secret_value

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ZscalerApiClient:
    def __init__(self, api_key, username, password, base_url):
        self.api_key = api_key
        self.username = username
        self.password = password
        self.base_url = base_url
        self.jsessionid = None

    def obfuscate_api_key(self, seed):
        now = int(time.time() * 1000)
        n = str(now)[-6:]
        r = str(int(n) >> 1).zfill(6)
        key = ""
        for i in range(0, len(str(n)), 1):
            key += seed[int(str(n)[i])]
        for j in range(0, len(str(r)), 1):
            key += seed[int(str(r)[j]) + 2]

        logger.info(f"Timestamp: {now}\tKey: {key}")
        return now, key

    def authenticate(self):
        auth_url = f"{self.base_url}/api/v1/auth"
        timestamp, new_api_key = self.obfuscate_api_key(self.api_key)
        auth_payload = {
            "apiKey": new_api_key,
            "username": self.username,
            "password": self.password,
            "timestamp": timestamp
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        response = requests.post(auth_url, json=auth_payload, headers=headers)

        if response.status_code == 200:
            self.jsessionid = response.cookies.get('JSESSIONID')
            logger.info("Authentication successful.")
        else:
            logger.error(f"Authentication failed. HTTP status code: {response.status_code}")
            exit()

    def make_api_request(self, url, method='get', payload=None):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Cookie": f"JSESSIONID={self.jsessionid}"
        }

        try:
            if method == 'get':
                response = requests.get(url, headers=headers)
            elif method == 'post':
                response = requests.post(url, json=payload, headers=headers)
            elif method == 'put':
                response = requests.put(url, headers=headers)
            elif method == 'delete':
                response = requests.delete(url, headers=headers)
            else:
                logger.error("Invalid HTTP method.")
                return None

            if response.status_code == 200:
                data = response.json()
                logger.info(f"API request successful. Response: {data}")
                return data
            else:
                logger.error(f"API request failed. url: {url} HTTP status code: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error occurred during API request: {str(e)}")
            return None

    def process_data(self, zSGroupId, zsVmId):
        # Step 1: Authenticate and obtain JSESSIONID
        self.authenticate()

        # # Step 2: Use JSESSIONID for further API calls
        # ecgrouplite_url = f"{self.base_url}/api/v1/ecgroup/lite"
        # self.make_api_request(ecgrouplite_url)
        #
        # # Step 3: Read ecvmid
        ecvm_url = f"{self.base_url}/api/v1/ecgroup/{zSGroupId}/vm/{zsVmId}"
        # self.make_api_request(ecvm_url)

        # Step 4: Delete the ecvmid
        self.make_api_request(ecvm_url, method='delete')

        # Step 5: Get ecAdminActivateStatus
        ecAdminActivateStatus_url = f"{self.base_url}/api/v1/ecAdminActivateStatus"
        self.make_api_request(ecAdminActivateStatus_url)

        # Step 6: Activate using Put
        ecAdminActivate_url = f"{self.base_url}/api/v1/ecAdminActivateStatus/activate"
        self.make_api_request(ecAdminActivate_url, method='put')

        # Step 7: Logout using delete
        logout_url = f"{self.base_url}/api/v1/auth"
        self.make_api_request(logout_url, method='delete')


def main():
    test_zscaler_resouce_deletion()


def test_zscaler_resouce_deletion():
    cc_url = os.environ['CC_URL']

    secret_name = os.environ['SECRET_NAME']

    # Call the method to retrieve the secret value
    api_key, username, password = get_secret_value(secret_name)

    prov_url = "https://" + cc_url
    parsed_url = urlparse(prov_url)
    base_url = "https://" + parsed_url.netloc
    logger.info(f"Zscaler Cloud url: {base_url}")
    start_time = time.time()
    zscaler_api = ZscalerApiClient(api_key, username, password, base_url)
    # Test data
    zSGroupId = 1234
    zsVmId = 4567
    zscaler_api.process_data(zSGroupId, zsVmId)
    end_time = time.time()
    execution_time = end_time - start_time
    logger.info(f"Time taken: {execution_time} seconds")


if __name__ == "__main__":
    main()