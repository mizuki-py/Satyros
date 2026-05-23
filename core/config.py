import os

import sys

if getattr(sys, 'frozen', False):
    APP_DIR = sys._MEIPASS
    BASE_DIR = os.getcwd()
else:
    APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    BASE_DIR = APP_DIR

# Default Ports
TFTP_PORT = 69
FTP_PORT = 21
SFTP_PORT = 22
SYSLOG_PORT = 514
SNMP_TRAP_PORT = 162

import socket

def get_local_ips():
    ips = ["0.0.0.0", "127.0.0.1"]
    try:
        hostname = socket.gethostname()
        _, _, ip_list = socket.gethostbyname_ex(hostname)
        for ip in ip_list:
            if ip not in ips:
                ips.append(ip)
    except Exception:
        pass
    return ips

# Default Directories
DEFAULT_ROOT_DIR = os.path.join(BASE_DIR, "data", "root")
DEFAULT_LOG_DIR = os.path.join(BASE_DIR, "data", "logs")

# Ensure directories exist
os.makedirs(DEFAULT_ROOT_DIR, exist_ok=True)
os.makedirs(DEFAULT_LOG_DIR, exist_ok=True)
