from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport import Request
import os
import json
from typing import List


# TODO: serialize datetime in Credentials object
def save_creds(creds_path: str, creds: Credentials):
    with open(creds_path, 'w') as file:
        json.dump(creds.__dict__, file)


def get_creds(service: str, scopes: List[str]) -> Credentials:
    creds_path = f'creds/{service}_token.json'
    if not os.path.exists(creds_path):
        flow = InstalledAppFlow.from_client_secrets_file('creds/client_secret.json', scopes)
        creds = flow.run_local_server(port=9999)
        print(creds.__dict__)
        #save_creds(creds_path, creds)
    else:
        with open(creds_path) as creds_file:
            cred_attrs = json.load(creds_file)
        creds = Credentials(**cred_attrs)

        if creds.expired:
            creds.refresh(Request())
            #save_creds(creds_path, creds)

    return creds
