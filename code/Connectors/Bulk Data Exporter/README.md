# Bulk Custom Task Data Export Connector

This project is a Flask-based application that exports custom task data in various formats (CSV, Parquet, JSON) from a given URL. The application supports proxy configurations and generates files based on a specified pattern.

## Prerequisites

- Python 3.6 or higher
- pip (Python package installer)

## Installation

1. Download the package.
2. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

## Configuration

The application uses environment variables for configuration. You can set these variables in your environment or create a `.env` file in the project root.

Example `.env` file:
```
DEBUG=True
FLASK_RUN_HOST=0.0.0.0
FLASK_RUN_PORT=5000
PROXY_URL=http://proxy.example.com:8080
PROXY_USERNAME=proxyuser
PROXY_PASSWORD=proxypassword
FILE_NAME_PATTERN={outboundEventName}-{occurrenceId}
EXPORT_DATA_FOLDER=/path/to/export_data
```

### FILE_NAME_PATTERN

The `FILE_NAME_PATTERN` environment variable is used to generate file names based on the data in the JSON payload. You can use placeholders in the pattern that correspond to keys in the payload.

Example JSON payload (`sample.json`):
```json
{
  "task": {
    "occurrenceId": "ad03be35-aedd-4cfe-9398-4fac0d113ef9",
    "taskId": "a0ae0669-6c39-45af-9af7-b8451b800282",
    "taskName": "Seminar Attendance List",
    "taskVersionId": "y_pa336pmrnmirKSDvZR3E0orjwLmc.Q",
    "outboundEventName": "ctt_export_user_details"
  },
  "tenant": {
    "externalTenantId": "3e751191f100013b67637678",
    "tenantMoniker": "bct01b"
  },
  "contactResponse": {
    "responseTrackingCode": "bb969091-8f6a-4193-a6d5-424387e8eae0"
  },
  "presignedUrls": {
    "metadataFile": "url.....",
    "dataFile": "url..."
  },
  "sendParameters": {
    "seminar": "Learn Personal Finance",
    "seminar_type": "In-Person"
  }
}
```

With the above payload, you can use the following placeholders in the `FILE_NAME_PATTERN`:

- `{occurrenceId}`: Corresponds to `task.occurrenceId`
- `{taskId}`: Corresponds to `task.taskId`
- `{taskName}`: Corresponds to `task.taskName`
- `{taskVersionId}`: Corresponds to `task.taskVersionId`
- `{outboundEventName}`: Corresponds to `task.outboundEventName`
- `{externalTenantId}`: Corresponds to `tenant.externalTenantId`
- `{tenantMoniker}`: Corresponds to `tenant.tenantMoniker`
- `{responseTrackingCode}`: Corresponds to `contactResponse.responseTrackingCode`
- `{seminar}`: Corresponds to `sendParameters.seminar`
- `{seminar_type}`: Corresponds to `sendParameters.seminar_type`

Example patterns and resulting file names:

- Pattern: `{outboundEventName}-{occurrenceId}`
  - Result: `ctt_export_user_details-ad03be35-aedd-4cfe-9398-4fac0d113ef9`
- Pattern: `{taskName}-{responseTrackingCode}`
  - Result: `Seminar Attendance List-bb969091-8f6a-4193-a6d5-424387e8eae0`
- Pattern: `{tenantMoniker}-{seminar}`
  - Result: `bct01b-Learn Personal Finance`

## Running the Application

### On Windows

1. Run the application using the provided batch script:
    ```sh
    run_app.bat
    ```

### On Linux
1. The application is not tested on Linux yet.
2. You could run the application using a shell script like this:
    ```sh
    ./run_linux.sh
    ```

## Usage

The API can export the data in one of the three formats: CSV, Parquet or JSON. It is mentioned through a URL parameter named `format`.
For example: http://127.0.0.1:5000/export?format=parquet

The HTTP method has to be `POST`.

This API can be configured as a Bulk Custom Connector Endpoint in SAS CI360 to be used in a Bulk Custom Task Type. If you are deploying this on a server that is not accessible from internet (which is the case most of the time), then you need to have a SAS CI360 General Agent assigned to the Connector and you need to run the General Agent on your local environment. 

Learn more about Custom Connectors in SAS CI360 in our online [documentation](https://go.documentation.sas.com/doc/en/cintcdc/production.a/cintag/ch-connectors-custom-setup.htm). 

Learn more about Custom Tasks in SAS CI360 in our online [documentation](https://go.documentation.sas.com/doc/en/cintcdc/production.a/cintag/custom-task-create.htm)

Learn more about General Agents in SAS CI360 in our online [documentation](https://go.documentation.sas.com/doc/en/cintcdc/production.a/cintag/integrating-agents-general.htm)

## Samples

1. Connector configuration 

You can create a Connector on your tenant by exporting `/sample/conn_def_bct05_ecotraining.json` on your tenant. Remember to update the Email Address, IP address, Port number etc. to match your environment. 
This configuration has a variable for `Format` which it expects from the Custom Task's `Send Parameters`. You can change that if you like or keep it so that you can make the `Format` selectable option from each Task. In your task type, you can have a Send Parameter named `export_format` of type Dropdown, with value CSV, Parquet and JSON. This then becomes available for Task designers to select.
