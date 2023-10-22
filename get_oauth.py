import json, time
from pytube import request, YouTube
import os
import sys
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
def cache_tokens(access_token,refresh_token,expires):
    data = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires': expires
    }
    os.mkdir(resource_path('pytube'))
    os.mkdir(resource_path('pytube\\__cache__\\'))
    file = resource_path('pytube\\__cache__\\tokens.json')
    with open(file, 'w') as f:
        json.dump(data, f)


def fetch_token():
    """Fetch an OAuth token."""
    # Subtracting 30 seconds is arbitrary to avoid potential time discrepencies
    start_time = int(time.time() - 30)
    data = {
        'client_id': "861556708454-d6dlm3lh05idd8npek18k6be8ba3oc68.apps.googleusercontent.com",
        'scope': 'https://www.googleapis.com/auth/youtube'
    }
    response = request._execute_request(
        'https://oauth2.googleapis.com/device/code',
        'POST',
        headers={
            'Content-Type': 'application/json'
        },
        data=data
    )
    response_data = json.loads(response.read())
    verification_url = response_data['verification_url']
    user_code = response_data['user_code']
    print(f'Please open {verification_url} and input code {user_code}')
    input('Press enter when you have completed this step.')

    data = {
        'client_id': "861556708454-d6dlm3lh05idd8npek18k6be8ba3oc68.apps.googleusercontent.com",
        'client_secret': "SboVhoG9s0rNafixCSGGKXAT",
        'device_code': response_data['device_code'],
        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'
    }
    response = request._execute_request(
        'https://oauth2.googleapis.com/token',
        'POST',
        headers={
            'Content-Type': 'application/json'
        },
        data=data
    )
    response_data = json.loads(response.read())

    access_token = response_data['access_token']
    refresh_token = response_data['refresh_token']
    expires = start_time + response_data['expires_in']
    cache_tokens(access_token,refresh_token,expires)

fetch_token()
# yt = YouTube("https://www.youtube.com/watch?v=Kt-tLuszKBA", use_oauth=True)
# print(yt.title)
# input('Enter to exit:')