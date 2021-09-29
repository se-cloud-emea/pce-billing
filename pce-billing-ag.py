# -*- coding: utf-8 -*-

import sys
import json
import getpass
import argparse
import requests
from dotenv import load_dotenv


__author__ = 'Victor Knell'
__copyright__ = 'Copyright 2021, Palo Alto Networks'
__license__ = 'MIT'
__version__ = '0.2.0'
__maintainer__ = 'Victor Knell'
__email__ = 'vknell@paloaltonetworks.com'
__status__ = 'Dev'

# argparse help menu
stack = [
    "app",
    "app2",
    "app3",
    "app4",
    "app.gov",
    "app.cn",
    "app.sg",
    "app.eu",
    "app2.eu",
    "app.ca",
    "app.anz",
    "app.uk",
    "app.cn",
]

parser = argparse.ArgumentParser(prog='pcc-billing-ag',
                                 usage='%(prog)s [-h] [-v,--version] stack',
                                 description='Query the Prisma API to get average billing per Account Group'
                                 )
parser.version = __version__
parser.add_argument('stack',
                    type=str,
                    choices=stack,
                    help='select the Prisma Cloud stack')
parser.add_argument('-p', '--print',
                    metavar='',
                    help='print the available stacks')
# parser.add_argument('-f', '--file',
#                     metavar='',
#                     help='List of Account Groups to use, one AG per line')
# parser.add_argument('-i', '--include',
#                     metavar='',
#                     help='List of Account Groups to use, one AG per line')
# parser.add_argument('-e', '--exclude',
#                     metavar='',
#                     help='List of Account Groups to use, one AG per line')
# parser.add_argument('-t', '--timerange',
#                     help='Specify a time range, default is 3 months')
# parser.add_argument('-c', '--credits',
#                     metavar='',
#                     help='Against total credit paid instead of credits consumed')
parser.add_argument('-v', '--version', action='version')
args = parser.parse_args()


def print_stacks():
    for i in stack:
        print(i)

# get a key securely in the terminal
def get_key(string):
    if sys.stdin.isatty():
        secret = getpass.getpass(str(string))
    else:
        secret = sys.stdin.readline().rstrip()
    return secret


# define the api functions & methods
def auth_get_token(url, user, password):
    """
    Method to get the JWT after login using the Access Key and the Secret Key
    Returns token
    """
    r_url = "https://{}/login".format(url)
    r_headers = {
        'content-Type': 'application/json; charset=UTF-8',
    }
    r_data = {
        'username': '{}'.format(user),
        'password': '{}'.format(password),
    }
    r = requests.post(r_url, headers=r_headers, data=json.dumps(r_data))
    token = r.json().get('token')
    return token


def api_get(url, endpoint, token, data=""):
    """
    Method to query the Prisma Cloud CSPM API using the GET method
    Returns requests object
    """
    r_url = "https://{}{}".format(url, endpoint)
    r_headers = {
        'content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'x-redlock-auth': '{}'.format(token),
    }
    r = requests.get(r_url, headers=r_headers, data=json.dumps(data))
    return r


def api_post(url, endpoint, token, data=""):
    """
    Method to query the Prisma Cloud CSPM API using the POST method
    Returns requests object
    """
    r_url = "https://{}{}".format(url, endpoint)
    r_headers = {
        'content-Type': 'application/json; charset=UTF-8',
        'x-redlock-auth': '{}'.format(token),
    }
    r = requests.post(r_url, headers=r_headers, data=json.dumps(data))
    return r


def api_put(url, endpoint, token, data=""):
    """
    Method to query the Prisma Cloud CSPM API using the PUT method
    Returns requests object
    """
    r_url = "https://{}{}".format(url, endpoint)
    r_headers = {
        'content-Type': 'application/json; charset=UTF-8',
        'x-redlock-auth': '{}'.format(token),
    }
    r = requests.put(r_url, headers=r_headers, data=json.dumps(data))
    return r


def api_delete(url, endpoint, token, data=""):
    """
    Method to query the Prisma Cloud CSPM API using the DELETE method
    Returns requests object
    """
    r_url = "https://{}{}".format(url, endpoint)
    r_headers = {
        'content-Type': 'application/json; charset=UTF-8',
        'x-redlock-auth': '{}'.format(token),
    }
    r = requests.delete(r_url, headers=r_headers, data=json.dumps(data))
    return r


def get_account_groups(url, token, data=""):
    """
    Get the account_groups list
    Returns requests object
    """
    r_endpoint = "/cloud/group"
    r = api_get(url, r_endpoint, token, data)
    return r


def set_timerange(value="7", format="day"):
    """
    Method to create the JSON timeRange data requested for the licensing endpoint
    Returns JSON object
    """
    timerange = {
        "timeRange": {
            "type": "relative",
            "value": {
                "amount": value,
                "unit": format,
            }
        }
    }
    return timerange


def get_license_usage(url, token, data=""):
    r_endpoint = "/license/api/v1/usage/time_series"
    if data == "":
        data = set_timerange()
        data['accountIds'] = []
    r = api_post(url, r_endpoint, token, data)
    return r


def get_workloadsPurchased(url, token):
    r = get_license_usage(url, token)
    return r.json().get('workloadsPurchased')


def get_license_avg(url, token, data=""):
    """
    Method to get the average credits used for one or more Accounts
    Requires AccountIds as List and timeRange
    Returns int
    """
    # no pcc licence added (others/container)
    r = get_license_usage(url, token, data)
    # reading all items in Datapoints - 1 per timeUnit
    time_unit = 0
    total = 0
    for i in r.json().get('dataPoints'):
        time_unit += 1
        # removing containers credits
        for j in list(i['counts'].keys()):
            if j != "others":
                total += sum(list(i['counts'][j].values()))
    average = int(total/time_unit)
    return average


def credits_per_account(url, token, account_ids, timerange=set_timerange()):
    # formatting timerange to send timerange and the account groups as request body
    r_data = timerange
    r_data['accountIds'] = []
    if type(account_ids) is list:
        r_data['accountIds'] = account_ids
    else:
        r_data['accountIds'].append(account_ids)
    # returns the average 
    return get_license_avg(url, token, r_data)


def credits_per_ag(url, token):
    r = get_account_groups(url, token)
    ledger = {}
    for i in r.json():
        if i['accountIds'] != []:
            credits_avg = credits_per_account(url, token, i['accountIds'])
            ledger[i['name']] = credits_avg
    return ledger
            

def display():
    header = '-' * 50
    name = "NAME"
    avg = "AVG CREDITS"
    prc_c = "USED"
    prc_p = "PURCH"
    print(header)
    print('{:<17s}{:>10s}{:>10s}{:>12s}'.format(name, avg, prc_c, prc_p))
    print(header)


if __name__ == "__main__":
    # set the stack domain
    if args.stack != 'app.cn':
        stack_console = str(args.stack)+'.prismacloud.io'
        stack_api = stack_console.replace('app', 'api', 1)
    else:
        stack_console = 'app.prismacloud.cn'
        stack_api = 'api.prismacloud.cn'
    # prompt for the access & secret keys
    access_key = get_key("Enter your Access Key: ")
    secret_key = get_key("Enter your Secret Key: ")


    # login and get token
    token = auth_get_token(stack_api, access_key, secret_key)
    consumed = get_license_avg(stack_api, token)
    purchased = get_workloadsPurchased(stack_api , token)
    ledger = credits_per_ag(stack_api, token)
    # printing the results
    display()
    for key in ledger:
        print('{:<17s}{:>11d}{:>9d}%{:>11d}%'.format(
            key, ledger[key], int(100*ledger[key]/consumed), int(100*ledger[key]/purchased)))
    print("Total consumed credits on purchased credits: {}/{}".format(consumed, purchased))



