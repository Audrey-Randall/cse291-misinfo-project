import csv
import os
import requests
import json

# To set your enviornment variables in your terminal run the following line:
# export 'BEARER_TOKEN'='<your_bearer_token>'
bearer_token = os.environ.get('TWITTER_BEARER_TOKEN')

def create_url(ids):
    # User fields are adjustable, options include:
    # created_at, description, entities, id, location, name,
    # pinned_tweet_id, profile_image_url, protected,
    # public_metrics, url, username, verified, and withheld
    user_fields = "user.fields=created_at,description,entities,id,location,name,pinned_tweet_id,profile_image_url,protected,public_metrics,url,username,verified,withheld"
    # You can adjust ids to include a single Tweets.
    # Or you can add to up to 100 comma-separated IDs
    url = "https://api.twitter.com/2/tweets/retweeted_by/:id?".format(','.join(ids))
    print(url)
    return url, user_fields

def bearer_oauth(r):
    """
    Method required by bearer token authentication.
    """

    r.headers["Authorization"] = 'Bearer '+bearer_token
    r.headers["User-Agent"] = "v2RetweetedByPython"
    print(r.headers)
    return r


def connect_to_endpoint(url, user_fields):
    response = requests.request("GET", url, auth=bearer_oauth, params=user_fields)
    print(response.status_code)
    if response.status_code != 200:
        raise Exception(
            "Request returned an error: {} {}".format(
                response.status_code, response.text
            )
        )
    print(response.json())

def parse(filename):
    with open(filename) as f:
        reader = csv.DictReader(f, delimiter='\t')
        ids = []
        for row in reader:
            if len(ids) >= 2:
                url, user_fields = create_url(ids)
                connect_to_endpoint(url, user_fields)
                ids = []
                break
            ids.append(row['tweetId'])
            


parse('notes-00000.tsv')
# ids = ['1377030478167937024','1536848327979016193']
# print(','.join(ids))