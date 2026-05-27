import threading
import logging
import asyncio
import os
import datetime
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
try:
    from pyftpdlib.handlers import TLS_FTPHandler
except ImportError:
    TLS_FTPHandler = FTPHandler
    logger.warning("pyOpenSSL is not installed. FTPS will not be available.")
from pyftpdlib.servers import FTPServer
from core.config import DEFAULT_ROOT_DIR

logger = logging.getLogger(__name__)

def generate_self_signed_cert(cert_path, key_path):
    if os.path.exists(cert_path) and os.path.exists(key_path):
        return
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
    ])
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.now(datetime.timezone.utc)
    ).not_valid_after(
        datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=365)
    ).sign(key, hashes.SHA256())
    
    with open(key_path, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
    with open(cert_path, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

class NotifyingFTPHandler(FTPHandler):
    def on_file_sent(self, file):
        super().on_file_sent(file)
        if hasattr(self.server, 'callback') and self.server.callback:
            self.server.callback(os.path.basename(file), self.remote_ip, "downloaded")

    def on_file_received(self, file):
        super().on_file_received(file)
        if hasattr(self.server, 'callback') and self.server.callback:
            self.server.callback(os.path.basename(file), self.remote_ip, "uploaded")

if TLS_FTPHandler is FTPHandler:
    class NotifyingTLS_FTPHandler(NotifyingFTPHandler):
        pass
else:
    class NotifyingTLS_FTPHandler(TLS_FTPHandler, NotifyingFTPHandler):
        pass


class AsyncFTPServer:
    def __init__(self, host='0.0.0.0', port=21, root_dir=DEFAULT_ROOT_DIR, callback=None):
        self.host = host
        self.port = port
        self.root_dir = root_dir
        self.server = None
        self.thread = None
        self.callback = callback
        
        self.username = "admin"
        self.password = "password"
        self.allow_write = True
        self.use_ftps = False

    def _run_server(self):
        authorizer = DummyAuthorizer()
        perm = "elradfmwMT" if self.allow_write else "elr"
        try:
            authorizer.add_user(self.username, self.password, self.root_dir, perm=perm)
        except Exception as e:
            logger.error(f"FTP authorizer error: {e}")
            return
            
        if self.use_ftps:
            from core.config import BASE_DIR
            data_dir = os.path.join(BASE_DIR, "data")
            os.makedirs(data_dir, exist_ok=True)
            cert_path = os.path.join(data_dir, "cert.pem")
            key_path = os.path.join(data_dir, "key.pem")
            generate_self_signed_cert(cert_path, key_path)
            handler = NotifyingTLS_FTPHandler
            handler.certfile = cert_path
            handler.keyfile = key_path
            handler.tls_control_required = False
            handler.tls_data_required = False
        else:
            handler = NotifyingFTPHandler
            
        handler.authorizer = authorizer

        try:
            self.server = FTPServer((self.host, self.port), handler)
            self.server.callback = self.callback
            protocol = "FTPS" if self.use_ftps else "FTP"
            logger.info(f"{protocol} server started at {self.host}:{self.port} with user {self.username}")
            self.server.serve_forever()
        except Exception as e:
            logger.error(f"FTP server error: {e}")

    async def start(self):
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()

    async def stop(self):
        if self.server:
            self.server.close_all()
            self.server = None
            logger.info("FTP/FTPS server stopped")

