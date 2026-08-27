import os
import configparser
import sys

def get_sql_config():
    """
    Safely reads, validates, and loads local INI connection secrets.
    """
    config = configparser.ConfigParser()
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.join(os.path.dirname(__file__), "..")
    config_path = os.path.join(base_dir, "config.ini")
        
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file missing at: {os.path.abspath(config_path)}")
        
    config.read(config_path)
    if "SQL_SERVER" not in config:
        raise KeyError("Section [SQL_SERVER] is missing inside config.ini configuration.")
        
    return {
        "Driver": config.get("SQL_SERVER", "Driver", fallback="{ODBC Driver 17 for SQL Server}"),
        "Server": config.get("SQL_SERVER", "Server"),
        "Database": config.get("SQL_SERVER", "Database"),
        "UID": config.get("SQL_SERVER", "UID"),
        "PWD": config.get("SQL_SERVER", "PWD"),
        "Timeout": config.getint("SQL_SERVER", "Timeout", fallback=5)
    }
