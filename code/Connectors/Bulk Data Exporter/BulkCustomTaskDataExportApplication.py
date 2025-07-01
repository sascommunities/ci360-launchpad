from app import create_app
from logger import get_logger

log = get_logger(__name__)
log.info("Creating the app.")
app = create_app()

if __name__ == "__main__":
    host = app.config['FLASK_RUN_HOST']
    port = app.config['FLASK_RUN_PORT']
    log.info(f"Starting the Connector as a Flask service on {host}:{port}...")
    app.run(host=host, port=port)
