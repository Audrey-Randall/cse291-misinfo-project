import csv
import os
import requests
import json
import time
from datetime import datetime
import argparse

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

def make_request(url, all_params):
    # Make request
    response = requests.request("GET", url, auth=bearer_oauth, params=all_params)

    # Handle "too many requests" error
    if response.status_code == 429:
        print("{}: Request returned an error (too many requests?) {}".format(datetime.now(), response.text))
        return None

    # Handle all other errors
    if response.status_code != 200:
        print("Request returned an error: {} {}".format(response.status_code, response.text))
        return None
    return response

def connect_to_endpoint(url, params):
    responses = []
    next_token = 'init'
    while next_token:
        # Handle pagination
        if next_token != 'init':
            all_params = '&'.join(params) + '&pagination_token=' + next_token
        else:
            all_params = '&'.join(params)

        
        resp = make_request(url, all_params)
        if resp is None:
            print("Sleep 10 and retry request once...")
            time.sleep(10)
            resp = make_request(url, all_params)
            if resp is None:
                print("Request failed twice, moving on.")
                break
            
        resp_json = resp.json()
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

def get_conversation(conversation_id):
    url = 'https://api.twitter.com/2/tweets/search/recent?query=conversation_id:1279940000004973111'

def get_tweets(input_file, output_file):
    user_fields = "user.fields=created_at,description,entities,id,location,name,pinned_tweet_id,protected,public_metrics,url,username,verified,withheld"
    tweet_fields = "tweet.fields=attachments,author_id,context_annotations,conversation_id,created_at,edit_controls,entities,geo,id,in_reply_to_user_id,lang,public_metrics,possibly_sensitive,referenced_tweets,reply_settings,source,text,withheld"
    outfile = open(output_file, 'w')
    with open(input_file) as f:
        reader = csv.DictReader(f, delimiter='\t')
        for i, row in enumerate(reader):
            if i < 17800:
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

def get_retweets(input_file, output_file):
    tweet_fields = "tweet.fields=attachments,author_id,context_annotations,conversation_id,created_at,edit_controls,entities,geo,id,in_reply_to_user_id,lang,public_metrics,possibly_sensitive,referenced_tweets,reply_settings,source,text,withheld"
    outfile = open(output_file, 'w')
    with open(input_file) as f:
        reader = csv.DictReader(f, delimiter='\t')
        for i, row in enumerate(reader):
            # if i < 17127:
            #     continue

            # Get retweets.
            # Only 75 requests allowed in 15 minutes.
            # time.sleep(12)
            retweet_url = "https://api.twitter.com/2/tweets/{}/retweeted_by".format(row['tweetId'])
            retweet_resp = connect_to_endpoint(retweet_url, [tweet_fields])

            # Get replies (the conversation).
            converation_url = 'https://api.twitter.com/2/tweets/search/recent?query=conversation_id:{}'.format(row['tweetId'])
            conversation_resp = connect_to_endpoint(retweet_url, [tweet_fields])

            for t in retweet_resp:
                # for key in row:
                #     t['cn_'+key] = row[key]
                outfile.write(str(t)+'\n')
            break
    outfile.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('function')
    args = parser.parse_args()

    if args.function == 'tweets':
        get_tweets('notes-00000.tsv', 'test.json')
    elif args.function == 'retweets':
        get_retweets('notes-00000.tsv', 'retweet_test.json')
    else:
        print('Usage: specify either "tweets" or "retweets"')