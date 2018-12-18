from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

import datetime
import os
import json

from typing import List


def save_creds(creds_path: str, creds: Credentials):
    creds_json = creds.__dict__.copy()

    creds_json['expiry'] = creds_json['expiry'].isoformat()
    expiry = creds_json['expiry']
    creds_json['expiry'] = expiry[:expiry.rfind('.')]

    public_attrs = {}
    for key in creds_json:
        if key.startswith('_'):
            public_attrs[key[1::]] = creds_json[key]
        else:
            public_attrs[key] = creds_json[key]

    with open(creds_path, 'w') as file:
        json.dump(public_attrs, file)


def load_creds(creds_path: str) -> Credentials:
    with open(creds_path) as file:
        creds_json = json.load(file)

    # expiry isn't a valid kwarg so save it to set manually
    expiry = creds_json['expiry']
    del(creds_json['expiry'])

    creds = Credentials(**creds_json)

    creds.expiry = datetime.datetime.strptime(expiry, '%Y-%m-%dT%H:%M:%S')
    return creds


# TODO: Instead of creating creds for each service, make one token with all scopes needed when SheetHandlers are made
def get_creds(service: str, scopes: List[str]) -> Credentials:
    creds_path = f'creds/{service}_token.json'
    if not os.path.exists(creds_path):
        flow = InstalledAppFlow.from_client_secrets_file('creds/client_secret.json', scopes)
        creds = flow.run_local_server(port=9999)
        save_creds(creds_path, creds)
    else:
        creds = load_creds(creds_path)

        if creds.expired:
            creds.refresh(Request())
            save_creds(creds_path, creds)

    return creds
