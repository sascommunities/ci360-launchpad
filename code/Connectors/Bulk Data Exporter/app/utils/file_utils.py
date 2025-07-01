import os
from logger import get_logger

log = get_logger(__name__)

def write_file(folder, name, content):
    """Write content to a file, creating directories if necessary"""
    if not os.path.exists(folder):
        os.makedirs(folder)
        log.info(f"Created directory: {folder}")
    log.info("File Name: " + name)
    if isinstance(content, bytes):
        mode = "wb"
        log.debug("Content: <binary content>")
    else:
        mode = "w"
        log.debug("Content: " + content)
    with open(os.path.join(folder, name), mode) as f:
        f.write(content)
    log.info(f"Successfully wrote to file: {os.path.join(folder, name)}")
