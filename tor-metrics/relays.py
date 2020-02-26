'''
File: relays.py

Relays class object consisting of relays (list of dict) and onionoo fetch
timestamp
'''

import os
import json
import time
import urllib.request
from urllib.error import URLError, HTTPError
import config

ABS_PATH = os.path.dirname(os.path.abspath(__file__))

class Relays:
    '''
    Relay class consisting of relays (list of dict) and onionoo fetch timestamp

    :ts_file: absolute path to timestamp file used in setting If-Modified_since
    :json: relay listings stored as a list of dict, derived from onionoo JSON
    :timestamp: timestamp of onionoo fetch
    '''
    def __init__(self):
        self.url = config.CONFIG['onionoo_url']
        self.ts_file = os.path.join(ABS_PATH, "timestamp")
        self.json = self.fetch_onionoo_details()
        self.timestamp = self.write_timestamp()

    def fetch_onionoo_details(self):
        '''
        Make request to onionoo to retrieve details document, return prepared
        JSON response (trimmed platform and sorted by highest observed
        bandwidth)
        '''
        if os.path.isfile(self.ts_file):
            with open(self.ts_file, 'r') as ts_file:
                prev_timestamp = ts_file.read()
            headers = {"If-Modified-Since": prev_timestamp}
            conn = urllib.request.Request(self.url, headers=headers)
        else:
            conn = urllib.request.Request(self.url)

        api_response = urllib.request.urlopen(conn).read()

        json_data = json.loads(api_response.decode('utf-8'))
        fixed_bw = self.fix_missing_observed_bandwidth(json_data)
        sorted_json = self.sort_by_bandwidth(fixed_bw)
        trimmed_json = self.trim_platform(sorted_json)
        return trimmed_json

    def trim_platform(self, json_data):
        '''
        Trim platform to retain base operating system without version number or
        unnecessary classification which could affect sorting

        e.g. "Tor 0.3.4.9 on Linux" -> "Linux"
        '''
        for relay in json_data['relays']:
            relay['platform'] = relay['platform'].split(' on ', 1)[1].split(' ')[0]
            relay['platform'] = relay['platform'].split('/')[-1] # GNU/*
        return json_data

    def fix_missing_observed_bandwidth(self, json_data):
        '''
        Set the observed_bandwidth parameter value for any relay missing the
        parameter to 0; the observed_bandwidth parameter is (apparently)
        optional, I hadn't run into an instance of it missing until 2019-10-03

        "[...] Missing if router descriptor containing this information cannot be
        found."
        --https://metrics.torproject.org/onionoo.html#details_relay_observed_bandwidth

        '''
        for idx, relay in enumerate(json_data['relays']):
            if not relay.get('observed_bandwidth'):
                json_data['relays'][idx]['observed_bandwidth'] = 0
        return json_data

    def sort_by_bandwidth(self, json_data):
        '''
        Sort full JSON list by highest observed_bandwidth, retain this order
        during subsequent sorting (country, AS, etc)
        '''
        json_data['relays'].sort(key=lambda x: x['observed_bandwidth'],
                                 reverse=True)
        return json_data

    def write_timestamp(self):
        '''
        Store encoded timestamp in a file to retain time of last request, passed
        to onionoo via If-Modified-Since header during fetch() if exists
        '''
        timestamp = time.time()
        f_timestamp = time.strftime('%a, %d %b %Y %H:%M:%S GMT',
                                    time.gmtime(timestamp))
        if self.json is not None:
            with open(self.ts_file, 'w', encoding='utf8') as ts_file:
                ts_file.write(f_timestamp)
        return f_timestamp
