''' List all output parameters as comma-separated values in the "Output:" docString. Do not specify "None" if there is no output parameter.'''
''' List all Python packages that are not built-in packages in the "DependentPackages:" docString. Separate the package names with commas on a single line. '''
''' Attributes of type date/datetime will have decimal values. '''

''' Input Attributes:
  - customer_id (string)
  - nbalistinputjson (dataGrid)
  - customer_firstname (string)
  - customer_email (string)
  - YOUR_ACCESS_TOKEN (string)
'''

''' DependentPackages: '''

import http.client
import json


def execute(
        customer_id,
        nbalistinputjson,
        customer_firstname,
        customer_email,
        mobile_number,
        YOUR_ACCESS_TOKEN):

    'Output:nbalistoutputjson,description,msg_status'

    description = ""
    status = "FAILED"
    print(nbalistinputjson)

    try:

        #
        # Parse incoming JSON if required
        #
        if isinstance(nbalistinputjson, str):
            nbalistinputjson = json.loads(nbalistinputjson)

        metadata = None
        data_rows = None

        #
        # Find metadata and data sections
        #
        for item in nbalistinputjson:

            if "metadata" in item:
                metadata = item["metadata"]

            if "data" in item:
                data_rows = item["data"]

        if not metadata:
            raise Exception("Metadata section not found")

        if not data_rows or len(data_rows) == 0:
            raise Exception("No recommendations found")

        #
        # Build ordered field list
        #
        field_names = []

        for attribute in metadata:
            field_names.extend(attribute.keys())

        #
        # TOP 1 recommendation only
        #
        first_row = data_rows[0]

        #
        # Build attributes dynamically
        #
        attributes = {}

        for index, field_name in enumerate(field_names):

            value = ""

            if index < len(first_row):
                value = first_row[index]

            attributes["md_" + field_name] = str(value)

        #
        # Add customer attributes
        #
        attributes["md_customer_firstname"] = str(customer_firstname)
        attributes["md_customer_email"] = str(customer_email)
        attributes["md_mobile_number"] = str(mobile_number)

        conn = http.client.HTTPSConnection(
            "extapigwservice-demo.cidemo.sas.com",
            timeout=10
        )

        payload = {
            "eventName": "Send Message",
            "customer_id": str(customer_id),
            "applicationId": "SwApp",
            "attributes": attributes
        }

        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + YOUR_ACCESS_TOKEN
        }

        conn.request(
            "POST",
            "/marketingGateway/events",
            json.dumps(payload),
            headers
        )

        response = conn.getresponse()

        description = response.read().decode("utf-8")

        if 200 <= response.status < 300:
            status = "SUCCESS"
        else:
            status = "FAILED"

        conn.close()

    except Exception as ex:
        description = str(ex)
        status = "FAILED"
    msg_status = status

    nbalistoutputjson= nbalistinputjson

    return nbalistoutputjson,description, msg_status