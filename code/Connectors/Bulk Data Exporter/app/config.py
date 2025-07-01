import os

class Config:
    # Enable or disable debug mode
    DEBUG = os.environ.get('DEBUG', True)  # Example: True or False

    # Folder to store export data files
    EXPORT_DATA_FOLDER = os.path.abspath(os.getcwd() + "/export_data")  # Example: /path/to/export_data

    # Folder to store other data files
    DATA_FOLDER = os.path.abspath(os.getcwd() + "/data")  # Example: /path/to/data

    # Host address for running the Flask application
    FLASK_RUN_HOST = os.environ.get('FLASK_RUN_HOST', '0.0.0.0')  # Example: '127.0.0.1' or '0.0.0.0'

    # Port number for running the Flask application
    FLASK_RUN_PORT = int(os.environ.get('FLASK_RUN_PORT', 5000))  # Example: 5000

    # Proxy URL for making external requests
    PROXY_URL = os.environ.get('PROXY_URL')  # Example: 'http://proxy.example.com:8080'

    # Username for proxy authentication
    PROXY_USERNAME = os.environ.get('PROXY_USERNAME')  # Example: 'proxyuser'

    # Password for proxy authentication
    PROXY_PASSWORD = os.environ.get('PROXY_PASSWORD')  # Example: 'proxypassword'

    # Pattern for generating file names
    FILE_NAME_PATTERN = os.environ.get('FILE_NAME_PATTERN', '{outboundEventName}-{occurrenceId}')  # Example: '{outboundEventName}-{occurrenceId}'
