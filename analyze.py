import csv
import os
import requests
import json
import time
from datetime import datetime

# To set your enviornment variables in your terminal run the following line:
# export 'BEARER_TOKEN'='<your_bearer_token>'
bearer_token = os.environ.get('TWITTER_BEARER_TOKEN')

def bearer_oauth(r):
    """
    Method required by bearer token authentication.
    """

    r.headers["Authorization"] = 'Bearer '+bearer_token
    r.headers["User-Agent"] = "v2RetweetedByPython"
    return r


def connect_to_endpoint(url, params):
    responses = []
    next_token = 'init'
    while next_token:
        # Handle pagination
        if next_token != 'init':
            all_params = '&'.join(params) + '&pagination_token=' + next_token
        else:
            all_params = '&'.join(params)

        # Make request
        response = requests.request("GET", url, auth=bearer_oauth, params=all_params)

        # Handle "too many requests" error
        if response.status_code == 429:
            print("{}: Request returned an error (too many requests?) {} Sleeping and continuing.".format(datetime.now(), response.text))
            time.sleep(10)
            continue

        # Handle all other errors
        if response.status_code != 200:
            raise Exception(
                "Request returned an error: {} {}".format(
                    response.status_code, response.text
                )
            )
        resp_json = response.json()
        if 'error' in resp_json:
            raise Exception(
                "Error in response: {}".format(resp_json['error'])
            )

        # Set next pagination token, if necessary. If not, return.
        try:
            next_token = resp_json['meta']['next_token']
        except KeyError:
            responses.append(resp_json)
            break
        responses.append(resp_json)
    return responses

def parse(input_file, output_file):
    user_fields = "user.fields=created_at,description,entities,id,location,name,pinned_tweet_id,protected,public_metrics,url,username,verified,withheld"
    tweet_fields = "tweet.fields=attachments,author_id,context_annotations,conversation_id,created_at,edit_controls,entities,geo,id,in_reply_to_user_id,lang,public_metrics,possibly_sensitive,referenced_tweets,reply_settings,source,text,withheld"
    outfile = open(output_file, 'w')
    with open(input_file) as f:
        reader = csv.DictReader(f, delimiter='\t')
        for i, row in enumerate(reader):
            if i < 14314:
                continue
            time.sleep(3)
            # retweet_url = "https://api.twitter.com/2/tweets/{}/retweeted_by".format(row['tweetId'])
            tweet_url = "https://api.twitter.com/2/tweets/{}".format(row['tweetId'])
            # retweet_resp = connect_to_endpoint(retweet_url, [tweet_fields])
            tweet_resp = connect_to_endpoint(tweet_url, [user_fields, tweet_fields])
            for t in tweet_resp:
                for key in row:
                    t['cn_'+key] = row[key]
                outfile.write(str(t)+'\n')
    outfile.close()

parse('notes-00000.tsv', 'test.json')
# ids = ['1377030478167937024','1536848327979016193']
# print(','.join(ids))