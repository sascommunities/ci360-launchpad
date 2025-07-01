#! python3
'''
Copyright © 2025, SAS Institute Inc., Cary, NC, USA.  All Rights Reserved.
SPDX-License-Identifier: Apache-2.0
Created on August 27, 2018
last update on May0 28, 2025
Version 0.4
@author: Mathias Bouten
'''

import requests, base64, jwt, json, argparse
import os
import configparser
import logging
from argparse import RawTextHelpFormatter 


##### functions #####
def readConfig(configFile):
    keys = {}
    seperator = '='
    with open(configFile) as f:
        for line in f:
            if line.startswith('#') == False and seperator in line: 
                # Find the name and value by splitting the string
                name, value = line.split(seperator, 1)
                # Assign key value pair to dict
                keys[name.strip()] = value.strip()
    return keys

def generateToken(tenantid, secret):
    client_secret_bytes = bytearray(secret, 'ascii')
    token = jwt.encode({'clientID': tenantid}, base64.b64encode(client_secret_bytes),algorithm='HS256')
    return token


def sendSingleEvent(token,url,eventPayload):
    # create headers
    headers = {}
    headers['Authorization'] = 'Bearer '+jwtToken
    headers['Content-Type']  = 'application/json'
    headers['Accept']        = 'application/json'  
    #print('\n Headers: ')
    #print('#################################')
    #print(json.dumps(headers, indent=4, sort_keys=True))
    
    payload = json.dumps(eventPayload)
    print('\n Payload:')
    #print('#################################')
    print(json.dumps(eventPayload, indent=4, sort_keys=True))
    
    # call ci360
    try: 
        response = requests.request("POST", url, headers=headers, data=payload)
    except requests.exceptions.RequestException as e:  
        print(e)    
        sys.exit(1)
    else:
        print('  ...response status code: '+ str(response.status_code))
        #print('#################################')
        if response.status_code != 200:
            json_data = json.loads(response.text)
            print('')
            print(json.dumps(json_data, indent=4, sort_keys=True))


def getFileUploadLocation():
    # Generate the JWT and set headers
    jwtToken = generateToken(config['tenant_id'],config['secret'])
    headers = {}
    headers['Authorization'] = 'Bearer '+jwtToken
    headers['Content-Type']  = 'application/json'
    #print('\n Get Upload Location Headers: ')
    #print('#################################')
    #print(json.dumps(headers, indent=4, sort_keys=True))
    
    # create the request json object to retrieve file upload location
    request_json_object = {}
    request_json_object['applicationId'] = 'eventGenerator'
    request_json_object['version'] = 1
    payload = json.dumps(request_json_object)
    #print('\n Payload:')
    #print('#################################')
    #print(json.dumps(request_json_object, indent=4, sort_keys=True))
    
    # call ci360
    try: 
        response = requests.request("POST", config['bulkEventUrl'], headers=headers, data=payload)
    except requests.exceptions.RequestException as e:  
        print(e)    
        sys.exit(1)
    else:
        print('  ...response status code: '+ str(response.status_code))
        #print('#################################')
        #print(response)
        json_data = json.loads(response.text)
        fileLocation = json_data['links'][0]['href']
        #print(json.dumps(fileLocation, indent=4, sort_keys=True))
        return fileLocation
        #if response.status_code != 200:
            #json_data = json.loads(response.text)
            #print(json_data)
            #print(json.dumps(json_data, indent=4, sort_keys=True))

            
            
            
def uploadBulkEventFile(upload_url, pathname):
    print('  ...uploading file....')
    
    upload_headers = {}
    upload_headers['Content-Type']  = 'application/octet-stream'
    #print('\n Upload Headers: ')
    #print('##############################')
    #print(json.dumps(upload_headers, indent=4, sort_keys=True))
    
    try: 
        with open(pathname, 'rb') as infile:
            response = requests.put(upload_url, headers=upload_headers, data=infile)
    except requests.exceptions.RequestException as e:  
        print(e)    
        sys.exit(1)
    else:
        print('  ...bulk Upload Response: ' + str(response))
        #print('##############################')
        #print(response)
               
#####################


# read config
config = readConfig('config.ini')
singleEventFile = config['singleEventFile']
bulkEventFile = config['bulkEventFile']

# Generate the JWT
jwtToken = generateToken(config['tenant_id'],config['client_secret'])


## START PROGRAM
# check command line arguments
parser = argparse.ArgumentParser(description=
        'Send external events to CI360 \
        \nExamples: py send360event.py  \
        \n          py send360event.py -a single \
        \n          py send360event.py -a single -f my_single_event_file.txt \
        \n          py send360event.py -a bulk \
        \n          py send360event.py -a bulk -f my_bulk_event_file.csv'
        , formatter_class=RawTextHelpFormatter)

parser.add_argument('-a', action='store', dest='action', type=str, 
    help='enter event action type here: bulk or single', required=True)
parser.add_argument('-f', action='store', dest='file', type=str, 
    help='enter event file name: event(s).csv', required=False)
args = parser.parse_args()

print('')

if args.action is not None:
    action = args.action
    if action == 'single':
        file = singleEventFile
        if args.file is not None:
            file = args.file
        print('Send SINGLE event to CI360')
        print('  ...using event config file: ' + file)
        eventPayload = readConfig(file)
        ##### call webservice to send event #####
        sendSingleEvent(jwtToken,config['singleEventUrl'],eventPayload)
    if action == 'bulk':
        file = bulkEventFile
        if args.file is not None:
            file = args.file
        print('Send BULK events to CI360')
        print('  ...using bulk event file: ' + file)
        # Step 1: get file upload location
        fileUploadLocation = getFileUploadLocation()
        # Step 2: upload bulk event file
        uploadBulkEventFile(fileUploadLocation, file)
        
#####################


# End
print('\nDone\n')
