import asyncio
import logging
import re
import os
from logging.handlers import TimedRotatingFileHandler
from core.config import DEFAULT_LOG_DIR

logger = logging.getLogger(__name__)

# Setup file logger for syslog
syslog_file_logger = logging.getLogger("syslog_file")
syslog_file_logger.setLevel(logging.INFO)
os.makedirs(DEFAULT_LOG_DIR, exist_ok=True)
handler = TimedRotatingFileHandler(os.path.join(DEFAULT_LOG_DIR, "syslog.log"), when="midnight", interval=1, backupCount=7)
handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
syslog_file_logger.addHandler(handler)

class SyslogProtocol(asyncio.DatagramProtocol):
    def __init__(self, callback):
        self.callback = callback
        # PRI is like <34>
        self.pri_regex = re.compile(r'^<(\d+)>')

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        msg = data.decode(errors='replace').replace('\x00', '').replace('\r', '').strip()
        ip = addr[0]
        
        # Parse Severity
        severity = 6 # Default to Info
        match = self.pri_regex.search(msg)
        if match:
            pri = int(match.group(1))
            severity = pri % 8
            
        syslog_file_logger.info(f"{ip} - {msg}")
        
        if self.callback:
            self.callback(ip, msg, severity)

class SyslogServer:
    def __init__(self, port=514, callback=None):
        self.host = '0.0.0.0'
        self.port = port
        self.callback = callback
        self.transport = None

    async def start(self):
        loop = asyncio.get_running_loop()
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: SyslogProtocol(self.callback),
            local_addr=(self.host, self.port)
        )
        logger.info(f"Syslog server started at {self.host}:{self.port}")

    async def stop(self):
        if self.transport:
            self.transport.close()
            logger.info("Syslog server stopped")
