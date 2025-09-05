# DISCLAIMER

This script and guide are intended for training purposes only. Production usage is not recommended and may require further customizations, security reviews, and validation to meet enterprise requirements.

---

# SAS CI360 Customer Table Upload - Training Hands-On Guide

This guide will help you use the `customer-table-upload.py` script to automate uploading customer CSV files to SAS CI360 tables, track import job status, and manage file archiving and error handling.

## Prerequisites
- Python 3.8+
- Required Python packages (see `requirements.txt`)
- Access to SAS CI360 tenant and API credentials
- Properly configured `tenant-config.ini` file
- VeloxPy 
### How to Get VeloxPy

VeloxPy is a field-developed client SDK that provides an easier interface for working with the REST APIs of SAS Customer Intelligence 360. You can download and install it from the [SAS Customer Intelligence 360 - Extensions](https://github.com/sassoftware/ci360-extensions).

If, for any reason, you can’t install it or want more control over its code, you can copy the entire `sas_ci360_veloxpy` folder from the same repository into the `API/Ex1` folder and continue with the exercise.

## Folder Structure
- `source/`   - Place your CSV files to be uploaded here
- `archive/`  - Successfully processed files will be moved here
- `error/`    - Files that fail processing will be moved here

## How to Run
1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
2. Place your CSV files in the `source` folder. Each file should be named as:
   ```
   <ci360_table_name>_<FILE_NAME_SEPARATOR>_<anything>.csv
   ```
   The FILE_NAME_SEPARATOR is defined in the code as `_name_`. 
   For example, if your table in CI 360 is named Customer_Profile
   then the csv file should be:
   1. `Customer_Profile.csv`
   2. or `Customer_Profile_name_01012026.csv`
   The code will automatically split the name with `_name_` and then take the first part, that is `Customer_Profile` and try to get the details of the table from CI 360 tenant.
3. Run the script from the command line:
   ```
   python customer-table-upload.py source=<source_folder> archive=<archive_folder> error=<error_folder>
   ```
   Example:
   ```
   python customer-table-upload.py source=./source archive=./archive error=./error
   ```

## What the Script Does
- Initializes connection to SAS CI360 using your config file
- Scans the source folder for CSV files
- Skips non-CSV and empty files (moves them to error folder)
- For each valid CSV:
  - Extracts the table name from the file name
  - Finds the matching table in CI360
  - Gets a signed URL and uploads the file
  - Creates and runs an import job
  - Moves the file to archive folder if successful, or error folder if not
- Polls the status of all import jobs every 60 seconds until all are complete
- Logs all actions and errors for easy troubleshooting

## Troubleshooting
- Check the log output for details on errors or job status
- Ensure your `tenant-config.ini` and credentials are correct
- Make sure your CSV files match the expected naming convention

---
Happy uploading!
