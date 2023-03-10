import warnings
warnings.filterwarnings("ignore")
import csv
import os
import requests
import json
import time
from datetime import datetime
import argparse
from collections import defaultdict
import numpy as np
from matplotlib import pyplot as plt
import ast

import matplotlib
matplotlib.use('agg')

# To set your enviornment variables in your terminal run the following line:
# export 'TWITTER_BEARER_TOKEN'='<your_bearer_token>'
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
        print("{}: Request returned an error: {} {}".format(datetime.now(), response.status_code, response.text))
        return None
    return response

def connect_to_endpoint(url, params, output_file, tweet_id):
    responses = []
    next_token = 'init'
    f = open(output_file, 'w')
    while next_token:
        # Handle pagination
        if next_token != 'init':
            all_params = '&'.join(params) + '&pagination_token=' + next_token
            print('Handling pagination with token', next_token)
            time.sleep(12)
        else:
            all_params = '&'.join(params)
            print('Handling pagination with token', next_token)

        resp = make_request(url, all_params)
        if resp is None:
            print("Retry request once...")
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
        resp_json['cn_tweetId'] = tweet_id
        f.write(json.dumps(resp_json)+'\n')
        responses.append(resp_json)
    f.close()
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
    seen_ids = set([])
    with open(input_file) as f:
        for line in f:
            row = json.loads(line)
            tweet_id = row['cn_tweetId']
            # Only 75 retweet requests allowed in 15 minutes.
            time.sleep(12)
            # Some tweets have multiple notes, don't request retweets for the same tweet multiple times
            if tweet_id in seen_ids:
                continue
            seen_ids.add(tweet_id)
            retweet_url = "https://api.twitter.com/2/tweets/{}/retweeted_by".format(tweet_id)
            connect_to_endpoint(retweet_url, [tweet_fields], output_file, tweet_id)
            
    outfile.close()

def get_helpfulness_ratings(input_file):
    tweets = defaultdict(lambda: [])
    with open(input_file) as f:
        reader = csv.DictReader(f, delimiter='\t')
        for row in reader:
            tweets[row['noteId']].append(row['helpfulnessLevel'])
    return tweets

# Get some stats and plot the histogram of how many "helpfulness" votes each CN has.
def analyze_helpfulness(input_file):
    tweets = get_helpfulness_ratings(input_file)
    num_ratings = [len(tweets[t]) for t in tweets]
    print('Mean ratings:', np.mean(num_ratings), 'Median ratings', np.median(num_ratings), 'max:', np.max(num_ratings))

    counts, bins = np.histogram(num_ratings, bins=max(num_ratings))
    plt.hist(bins[:-1], bins, weights=counts, histtype='step', cumulative=True, density=True)
    print('Counts:', counts[:10], 'Bins:', bins[:10])
    plt.xlabel('Number of "helpfulness" votes')
    plt.ylabel('Number of Community Notes')
    # plt.yscale('log')
    plt.xlim(0, 100)
    plt.savefig('ratings_histogram.png', dpi=300)
    plt.show()    

def filter_helpful(input_file):
    # Based on the histogram/CDF, 10 seems like a reasonable starting point, 
    # that'll mean we only have to make queries for half our data.
    num_votes_threshold = 10
    tweets = get_helpfulness_ratings(input_file)
    useful_tweets = []

    for t in tweets:
        if len(tweets[t]) < num_votes_threshold:
            continue
        num_votes = defaultdict(lambda: 0)
        for vote in tweets[t]:
            num_votes[vote] += 1
        
        # If a strict majority of the votes are "HELPFUL," consider the Community Note useful.
        if num_votes['HELPFUL'] > 0.5*len(num_votes):
            useful_tweets.append(t)

    print('Number of useful tweets:', len(useful_tweets))
    return useful_tweets

def sort_by_num_retweets(input_file, output_file, useful_note_ids):
    with open(input_file) as f:
        lines = []
        for line in f:
            row = ast.literal_eval(line)
            # Skip unhelpful notes or notes with too few ratings
            if row['cn_noteId'] not in useful_note_ids:
                continue
            lines.append(row)
    # Sort lines (list of dicts) by [data][public_metrics][retweet_count].
    # Retweets are not the same as quote tweets but retweets probably imply
    # agreement because they have no extra context added.
    f = open(output_file, 'w')
    for line in sorted(lines, key=(lambda x: x['data']['public_metrics']['retweet_count'] if 'data' in x else 0), reverse=True):
        f.write(json.dumps(line)+'\n')
    f.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('function')
    args = parser.parse_args()

    if args.function == 'tweets':
        get_tweets('notes-00000.tsv', 'test.json')
    elif args.function == 'retweets':
        get_retweets('all_helpful_data_sorted.json', 'retweet_data.json')
    elif args.function == 'analyze_helpfulness':
        analyze_helpfulness('ratings-00000.tsv')
    elif args.function == 'filter':
        useful_note_ids = filter_helpful('ratings-00000.tsv')
        sort_by_num_retweets('all_tweet_data.json', 'all_helpful_data_sorted.json', useful_note_ids)
    else:
        print('Usage: specify either "tweets" or "retweets"')
