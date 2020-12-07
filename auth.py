from stravalib.client import Client
from httplib2 import Http
import json
import flask


def strava_auth(data):
    code = data
    print(data)
    client = Client()
    token = client.exchange_code_for_token(
    client_id="54636", client_secret="#########################", code=code,
    )
    return (token)

def strava_refresh_token(data):
    refresh_token = data
    client = Client()
    response = client.refresh_access_token(
    client_id="54636", client_secret="############################", refresh_token=refresh_token,
    )
    return (response['access_token'])



if __name__ == "__main__":
    strava_auth()
