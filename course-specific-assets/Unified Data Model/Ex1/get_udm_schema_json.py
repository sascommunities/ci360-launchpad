import requests
import jwt
import base64

# Adjust the hostname and schema version as needed
external_gateway = "https://extapigwservice-prod.ci360.sas.com"
schema_end_point = "/marketingGateway/discoverService/dataDownload/eventData/detail/partitionedData?category=all&schemaVersion=" 
schema_version = "18"
# adjust the tenant credentials
client_id = "your_client_id"
client_secret = "your_client_secret"

available_data_url = external_gateway + schema_end_point + schema_version
client_secret = bytes(client_secret,encoding='ascii')
encodedSecret = base64.b64encode(client_secret)
token = jwt.encode({'clientID': client_id}, encodedSecret, algorithm='HS256')

headers = {"Authorization": f"Bearer {token}"}
response1 = requests.get(available_data_url, headers=headers)

if response1.status_code == 200:
    data = response1.json()
    schema_url = data['items'][1]['schemaUrl']

    if schema_url:
        response2 = requests.get(schema_url)
        if response2.status_code == 200:
            with open("UDM_schema_v"+schema_version+".json", "w", encoding="utf-8") as file:
                file.write(response2.text)
            print("Second response written to 'UDM_schema_v"+schema_version+".json'")
        else:
            print(f"Second GET failed with status code {response2.status_code}")
    else:
        print(f"schemaURL not found in the first response. Found {schema_url}")
else:
    print(f"First GET failed with status code {response1.status_code}")