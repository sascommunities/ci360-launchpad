"""
customer-table-upload.py

Automates uploading customer CSV files to SAS CI360 tables using signed URLs, tracks import job status, and manages file archiving and error handling.

Usage:
    python customer-table-upload.py source=<source_folder> archive=<archive_folder> error=<error_folder>

Arguments:
    source  - Folder containing CSV files to upload
    archive - Folder to move successfully processed files
    error   - Folder to move files that failed processing
"""
import sys
import os
import logging
import time
import asyncio
from sas_ci360_veloxpy import initApp, APIClient, GLOBAL_CONFIG

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# Options: "replace" "upsert"
# The mode in which the imported data is processed. Typically, you should use upsert mode. 
DEFAULT_UPDATE_MODE = "upsert"

# the code will try to split the csv file name with this, and then use the first part as the name of the descriptor.
FILE_NAME_SEPARATOR = "_name_"

# the maximum number of tables to retrieve in a single API call. The code will not check beyond this limit.
LIMIT_TABLE_COUNT=100

# the interval (in seconds) to wait between polling for job status updates.
DEFAULT_POLL_INTERVAL = 60

# The type of file being uploaded.
DEFAULT_FILE_TYPE="CSV"

# Whether the header row is included in the file.
HEADER_ROW_INCLUDED="true"

# The delimiter used to separate fields in the file.
DEFAULT_FIELD_DELIMITER=","



def setup_logging():
    # Set up logging to both file and console with timestamp, level, and logger name
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    return logging.getLogger(__name__)


def parse_folder_args(args):
    # Parse command line arguments in key=value format into a dictionary
    """Parse command line arguments for folder paths in the format key=value."""
    folder_args = {}
    for arg in args:
        if "=" in arg:
            k, v = arg.split("=", 1)
            folder_args[k.strip().lower()] = v.strip()
    return folder_args


def ensure_folders_exist(folder_paths, logger):
    # Ensure archive and error folders exist, create if missing
    """Create archive and error folders if not present."""
    for key in ["archive", "error"]:
        path = folder_paths[key]
        if not os.path.isdir(path):
            try:
                os.makedirs(path, exist_ok=True)
                logger.info(f"Created missing folder: {key} at '{path}'")
            except Exception as e:
                logger.error(f"Failed to create folder '{key}' at '{path}': {e}")
                sys.exit(1)


def validate_folders(folder_paths, logger):
    # Validate that all required folders exist, exit if any are missing
    """Validate that all required folders exist."""
    for key, path in folder_paths.items():
        if not os.path.isdir(path):
            logger.error(f"Provided path for {key} '{path}' is not a valid directory.")
            sys.exit(1)


def process_files(source_folder, logger):
    # Main file processing logic:
    # 1. Initialize SAS CI360 client
    # 2. Get summary of all tables
    # 3. Loop through files in source folder
    #    - Skip non-CSV and empty files
    #    - Upload valid CSVs, collect job IDs
    #    - Move files to archive or error folder
    # 4. Poll job status for all jobs until complete
    # set up veloxpy
    logger.info("Initializing veloxpy with tenant-config.ini")
    initApp("tenant-config.ini")
    logger.info("Veloxpy initialized successfully.")

    # getting CI 360 API client.
    logger.info("Getting CI 360 API client.")
    ci36_apiClient = APIClient()
    logger.ci36_apiClient = ci36_apiClient
    logger.info("CI 360 API client obtained successfully.")

    # Return a summary of all tables
    allTables = ci36_apiClient.get_summary_of_all_tables(0, LIMIT_TABLE_COUNT)

    # if there are no tables found on the tenant, then no reason to proceed.
    if not allTables and "items" not in allTables:
        logger.error("There are no tables created on the tenant.")
        return

    logger.debug(f"Retrieved summary of all tables")
    # Log the number of tables found
    logger.allTables = allTables
    logger.info(f"Number of tables found: {len(allTables['items'])}")

    job_ids = []
    files = [
        f
        for f in os.listdir(source_folder)
        if os.path.isfile(os.path.join(source_folder, f))
    ]
    if not files:
        logger.info("No files found in the source folder.")
        return

    for filename in files:
        file_path = os.path.join(source_folder, filename)
        logger.info(f"Found file: {filename}")
        if not filename.lower().endswith(".csv"):
            logger.warning(f"Skipping non-CSV file: {filename}")
            move_to_folder(file_path, logger.error_folder, logger)
            continue
        if os.path.getsize(file_path) == 0:
            logger.warning(f"File is empty: {filename}. Moving to error folder.")
            move_to_folder(file_path, logger.error_folder, logger)
            continue
        try:
            job_id = upload_file(file_path, logger)
            if job_id:
                move_to_folder(file_path, logger.archive_folder, logger)
                job_ids.append(job_id)
            else:
                logger.error(
                    f"Upload failed for file: {filename}. Moving to error folder."
                )
                move_to_folder(file_path, logger.error_folder, logger)
        except Exception as e:
            logger.error(
                f"Exception during upload for file {filename}: {e}. Moving to error folder."
            )
            move_to_folder(file_path, logger.error_folder, logger)

    poll_job_status(job_ids, logger, DEFAULT_POLL_INTERVAL)


def poll_job_status(job_ids, logger, poll_interval=60):
    # Poll the status of all import jobs every poll_interval seconds until all are complete
    """Poll the status of all jobs until they are complete."""
    if not job_ids:
        return
    logger.info(f"Polling status for {len(job_ids)} jobs...")
    jobs_pending = set(job_ids)
    while jobs_pending:
        for job_id in list(jobs_pending):
            try:
                # logger.ci36_apiClient = APIClient()
                # logger.ci36_apiClient.get_details_of_import_request_by_job_ID()
                status = logger.ci36_apiClient.get_details_of_import_request_by_job_ID(
                    job_id
                )
                logger.debug(f"Job {job_id} status: {status}")
                logger.info(
                    f"Job ID: {job_id} | Table: {status.get('tableName', 'unknown')} | "
                    f"Job Name: {status.get('name', 'unknown')} | Status: {status.get('status', 'unknown')}"
                )

                if status.get('status', 'unknown') in ("completed", "failed", "cancelled","Imported","unknown"):
                    jobs_pending.remove(job_id)
            except Exception as e:
                logger.error(f"Error checking status for job {job_id}: {e}")
        if jobs_pending:
            logger.info(f"Waiting {poll_interval} seconds before next status check...")
            time.sleep(poll_interval)


def upload_file(file_path, logger):
    # Upload a single CSV file to SAS CI360:
    # 1. Extract table name from file name
    # 2. Find matching table in tenant
    # 3. Get signed URL for upload
    # 4. Upload file to signed URL
    # 5. Create and run import job, return job ID
    logger.info(f"Uploading CSV file: {file_path}")

    # Extract table name from file name
    filename = os.path.basename(file_path)
    name_part = filename.rsplit(".", 1)[0]  # Remove extension
    if "_" in name_part:
        table_name = name_part.rsplit(FILE_NAME_SEPARATOR, 1)[0]
    else:
        table_name = name_part
    logger.info(f"Extracted table name: {table_name}")
    table_id = None

    if logger.allTables:
        # loop through each items in allTables, and where the name matches, get the id of that table.
        for table in logger.allTables["items"]:
            if table["name"] == table_name:
                table_id = table["id"]
                logger.info(f"Found matching table '{table_name}' with ID: {table_id}")
                break
        if table_id is None:
            logger.error(
                f"No matching table found for extracted table name: '{table_name}'"
            )
            return None

        #code to get the type of the table
        table_details = logger.ci36_apiClient.get_table_object_by_ID(table_id)
        if(not table_details):
            logger.error(f"Failed to retrieve table details for table ID: {table_id}")
            return None

        # Get the type of the table
        table_type = table_details.get("type", "unknown")
        logger.info(f"Table '{table_name}' (ID: {table_id}) has type: {table_type}")
        if table_type.lower() == "transient":
            update_mode = "replace"
        else:
            update_mode = DEFAULT_UPDATE_MODE

        signed_url = (
            logger.ci36_apiClient.create_signed_URL_to_upload_files_for_customer_table()
        )
        logger.debug("Signed URL to upload files: %s", signed_url["signedURL"])
        location = signed_url["signedURL"]
        if not location:
            logger.error(f"Failed to retrieve signed URL for file '{file_path}'.")
            return None

        # code to upload file_path to signed url received above in location
        se_upload_status = upload_file_to_signed_url(file_path, location, logger)
        if not se_upload_status:
            logger.error(f"Failed to upload file '{file_path}' to signed URL.")
            return None

        # Create a table job
        logger.ci36_apiClient = APIClient()
        tableJob = logger.ci36_apiClient.create_and_run_import_request(

            name=f"{table_name} - upload process using file {filename}",
            dataDescriptorId=table_id,
            fieldDelimiter=DEFAULT_FIELD_DELIMITER,
            fileLocation=location,
            fileType=DEFAULT_FILE_TYPE,
            headerRowIncluded=HEADER_ROW_INCLUDED,
            recordLimit=0,
            updateMode=update_mode,
        )
        if not tableJob or tableJob.get("id", None) is None:
            logger.error(f"Failed to create and run table job for file '{file_path}'.")
            return None
        table_job_id = tableJob.get("id", None)
        logger.info(f"Created table job with ID: {table_job_id} for file '{file_path}'")
        return table_job_id

    return None


def move_to_folder(file_path, dest_folder, logger):
    # Move a file to the specified folder, renaming with a GUID for uniqueness
    import shutil
    import uuid

    try:
        if not os.path.isdir(dest_folder):
            os.makedirs(dest_folder, exist_ok=True)
        base, ext = os.path.splitext(os.path.basename(file_path))
        guid = str(uuid.uuid4())
        new_filename = f"{base}_{guid}{ext}"
        dest_path = os.path.join(dest_folder, new_filename)
        shutil.move(file_path, dest_path)
        logger.info(f"Moved and renamed file '{file_path}' to '{dest_path}'")
    except Exception as e:
        logger.error(f"Failed to move file '{file_path}' to '{dest_folder}': {e}")


def upload_file_to_signed_url(file_path, location, logger):
    # Upload file to signed URL using HTTP PUT, log result
    import requests

    logger.info(f"Uploading file '{file_path}' to signed URL: {location}")
    try:
        with open(file_path, "rb") as f:
            response = requests.put(location, data=f)
        if response.status_code in (200, 201):
            logger.info(f"Successfully uploaded file '{file_path}' to signed URL.")
            return True
        else:
            logger.error(
                f"Failed to upload file '{file_path}' to signed URL. Status code: {response.status_code}, Response: {response.text}"
            )
            return False
    except Exception as e:
        logger.error(
            f"Exception during upload to signed URL for file '{file_path}': {e}"
        )
        return False


def main():
    # Entry point: parse arguments, set up folders, start processing
    

    logger = setup_logging()
    required_folders = ["source", "archive", "error"]
    folder_args = parse_folder_args(sys.argv[1:])
    missing = [key for key in required_folders if key not in folder_args]
    if missing:
        logger.error(
            f"Missing required folder arguments: {', '.join(missing)}. Usage: python customer-table-upload.py source=<source_folder> archive=<archive_folder> error=<error_folder>"
        )
        sys.exit(1)
    folder_paths = {key: folder_args[key] for key in required_folders}
    ensure_folders_exist(folder_paths, logger)
    validate_folders(folder_paths, logger)
    logger.info(f"Processing files in source folder: {folder_paths['source']}")
    # Attach archive and error folder paths to logger for easy access
    logger.archive_folder = folder_paths["archive"]
    logger.error_folder = folder_paths["error"]

    process_files(folder_paths["source"], logger)


if __name__ == "__main__":
    main()
