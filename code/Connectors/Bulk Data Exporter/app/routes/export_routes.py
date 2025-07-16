from flask import Blueprint, request, jsonify, current_app
import uuid
import json
import pandas as pd
from io import BytesIO
from app.utils.file_utils import write_file
from app.utils.url_utils import get_meta_url, get_data_url, download_url_content
from logger import get_logger, get_log_level
from pyarrow import parquet as pq

export_bp = Blueprint('export', __name__)
log = get_logger(__name__)
log_levels = get_log_level()

def generate_file_name(pattern, data):
    """Generate a file name based on the given pattern and data"""
    try:
        return pattern.format(**data)
    except KeyError as e:
        log.error(f"KeyError: {e} not found in data. Using default file_id.")
        return str(uuid.uuid4())

@export_bp.route('/export', methods=['POST'])
def export():
    try:
        log.info("Request received, URL: " + request.url)

        if not request.data:
            log.error("No data found in the request.")
            return jsonify({"error": "No data found in the request."}), 400

        data = request.data.decode("utf-8")
        log.debug(f"Request Body: {data}")
        body_json = json.loads(data)
        file_name_pattern = current_app.config['FILE_NAME_PATTERN']
        file_name = generate_file_name(file_name_pattern, {**body_json.get('task', {}), **body_json.get('contactResponse', {})})
        log.debug(f"Generated file name: {file_name}")

        log.info("Writing the request payload. File name: "+ file_name + "-" + "-payload.json");
        write_file(current_app.config['EXPORT_DATA_FOLDER'], file_name + "-" + "-payload.json", data)

        meta_url = get_meta_url(data)
        if meta_url:
            log.debug(f"Metadata URL: {meta_url}")
            metadata_content = download_url_content(meta_url)
            if metadata_content:
                metadata_content = metadata_content.decode("utf-8")  # Decode bytes to string
                metadata = json.loads(metadata_content)
                column_names = [col['columnName'] for col in metadata]  # Access list elements correctly
                log.info("Identified the column names from metadata.")
                log.debug(f"Column Names: {column_names}")
            else:
                log.error("Failed to download metadata content.")
                return jsonify({"error": "Failed to download metadata content."}), 500

        data_url = get_data_url(data)
        if data_url:
            log.debug(f"Data URL: {data_url}")
            log.info("Reading the data content from the S3 URL.")
            data_content = download_url_content(data_url)
            if data_content:
                format = request.args.get('format', 'csv').lower()
                log.info(f"Requested format: {format}")
                try:
                    df = pd.read_csv(BytesIO(data_content), dtype=str, header=None)
                    df.columns = column_names
                    if format == 'csv':
                        csv_content = df.to_csv(index=False, line_terminator='\n')
                        write_file(current_app.config['EXPORT_DATA_FOLDER'], file_name + "-data.csv", csv_content)
                    elif format == 'parquet':
                        parquet_content = BytesIO()
                        df.to_parquet(parquet_content, index=False)
                        write_file(current_app.config['EXPORT_DATA_FOLDER'], file_name + "-data.parquet", parquet_content.getvalue())
                    elif format == 'json':
                        json_content = df.to_json(orient='records')
                        write_file(current_app.config['EXPORT_DATA_FOLDER'], file_name + "-data.json", json_content)
                    else:
                        log.error(f"Unsupported format requested: {format}")
                        return jsonify({"error": f"Unsupported format requested: {format}"}), 400
                    log.info(f"Data content written to file: {file_name}-data.{format}")
                except Exception as e:
                    log.error(f"Error processing data content: {e}")
                    return jsonify({"error": f"Error processing data content: {e}"}), 500
            else:
                log.error("Failed to download data content.")
                return jsonify({"error": "Failed to download data content."}), 500

        if request.headers:
            headers = json.dumps({k: v for k, v in request.headers.items()})
            log.debug(f"Request Headers: {headers}")
        if request.args:
            args = json.dumps({k: v for k, v in request.args.items()})
            log.debug(f"Request URL Params: {args}")
        return jsonify({"message": "Success."})

    except KeyError as e:
        log.error(f"KeyError: {e}")
        return jsonify({"error": f"KeyError: {e}"}), 400
    except ValueError as e:
        log.error(f"ValueError: {e}")
        return jsonify({"error": f"ValueError: {e}"}), 400
    except Exception as e:
        log.error(f"An error occurred: {e}")
        return jsonify({"error": "An internal error occurred."}), 500