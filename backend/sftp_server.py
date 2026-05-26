import threading
import logging
import socket
import paramiko
import os
from core.config import DEFAULT_ROOT_DIR

logger = logging.getLogger(__name__)

class DummySFTPAuth(paramiko.ServerInterface):
    def __init__(self, username, password):
        self.valid_username = username
        self.valid_password = password
        
    def check_auth_password(self, username, password):
        if username == self.valid_username and password == self.valid_password:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED
        
    def get_allowed_auths(self, username):
        return "password"

    def check_channel_subsystem_request(self, channel, name):
        if name == b"sftp" or name == "sftp":
            return True
        return False

def make_sftp_server_class(root_dir, allow_write):
    class StubSFTPHandle(paramiko.SFTPHandle):
        def __init__(self, flags, path):
            super().__init__(flags)
            os_flags = flags | getattr(os, 'O_BINARY', 0)
            self.fd = os.open(path, os_flags, 0o666)
            self.flags = flags

        def read(self, offset, length):
            if (self.flags & os.O_WRONLY) and not (self.flags & os.O_RDWR):
                return paramiko.SFTP_PERMISSION_DENIED
            os.lseek(self.fd, offset, os.SEEK_SET)
            return os.read(self.fd, length)

        def write(self, offset, data):
            if (self.flags & (os.O_WRONLY | os.O_RDWR)) == 0:
                return paramiko.SFTP_PERMISSION_DENIED
            if not (self.flags & os.O_APPEND):
                os.lseek(self.fd, offset, os.SEEK_SET)
            os.write(self.fd, data)
            return paramiko.SFTP_OK

        def close(self):
            os.close(self.fd)

    class SFTPInterface(paramiko.SFTPServerInterface):
        def _realpath(self, path):
            # Normalize separators and strip leading slashes/backslashes
            # to prevent absolute path injection on Windows (V-02)
            clean = path.replace('\\', '/').lstrip('/')
            # Join with root and normalize to resolve ../ sequences (V-01)
            resolved = os.path.normpath(os.path.join(root_dir, clean))
            # Boundary check: ensure the resolved path stays within root_dir
            root_normalized = os.path.normpath(root_dir)
            if not (resolved == root_normalized or resolved.startswith(root_normalized + os.sep)):
                raise PermissionError("Access denied: path escapes root directory")
            return resolved

        def list_folder(self, path):
            path = self._realpath(path)
            try:
                out = []
                for f in os.listdir(path):
                    attr = paramiko.SFTPAttributes.from_stat(os.stat(os.path.join(path, f)))
                    attr.filename = f
                    out.append(attr)
                return out
            except OSError:
                return paramiko.SFTP_NO_SUCH_FILE

        def stat(self, path):
            path = self._realpath(path)
            try:
                return paramiko.SFTPAttributes.from_stat(os.stat(path))
            except OSError:
                return paramiko.SFTP_NO_SUCH_FILE

        def lstat(self, path):
            return self.stat(path)

        def open(self, path, flags, attr):
            path = self._realpath(path)
            if not allow_write and (flags & (os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC)):
                return paramiko.SFTP_PERMISSION_DENIED
            try:
                return StubSFTPHandle(flags, path)
            except OSError as e:
                return paramiko.SFTP_PERMISSION_DENIED

        def remove(self, path):
            if not allow_write:
                return paramiko.SFTP_PERMISSION_DENIED
            path = self._realpath(path)
            try:
                os.remove(path)
                return paramiko.SFTP_OK
            except OSError:
                return paramiko.SFTP_NO_SUCH_FILE

        def rename(self, oldpath, newpath):
            if not allow_write:
                return paramiko.SFTP_PERMISSION_DENIED
            oldpath = self._realpath(oldpath)
            newpath = self._realpath(newpath)
            try:
                os.rename(oldpath, newpath)
                return paramiko.SFTP_OK
            except OSError:
                return paramiko.SFTP_NO_SUCH_FILE

        def mkdir(self, path, attr):
            if not allow_write:
                return paramiko.SFTP_PERMISSION_DENIED
            path = self._realpath(path)
            try:
                os.mkdir(path)
                return paramiko.SFTP_OK
            except OSError:
                return paramiko.SFTP_NO_SUCH_FILE

        def rmdir(self, path):
            if not allow_write:
                return paramiko.SFTP_PERMISSION_DENIED
            path = self._realpath(path)
            try:
                os.rmdir(path)
                return paramiko.SFTP_OK
            except OSError:
                return paramiko.SFTP_NO_SUCH_FILE
    return SFTPInterface

class AsyncSFTPServer:
    def __init__(self, host='0.0.0.0', port=22, root_dir=DEFAULT_ROOT_DIR):
        self.host = host
        self.port = port
        self.root_dir = root_dir
        self.server_socket = None
        self.thread = None
        self.running = False
        
        self.username = "admin"
        self.password = "password"
        self.allow_write = True

    def _run_server(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.server_socket.settimeout(1.0)
            logger.info(f"SFTP server started at {self.host}:{self.port} with user {self.username}")
            
            # Generate host key once per server instance to avoid CPU spikes
            # and allow clients to trust/pin the key (V-06)
            host_key = paramiko.RSAKey.generate(2048)
            
            def handle_client(client_conn):
                try:
                    transport = paramiko.Transport(client_conn)
                    transport.add_server_key(host_key)
                    
                    sftp_cls = make_sftp_server_class(self.root_dir, self.allow_write)
                    transport.set_subsystem_handler("sftp", paramiko.SFTPServer, sftp_cls)
                    
                    server_if = DummySFTPAuth(self.username, self.password)
                    transport.start_server(server=server_if)
                    
                    chan = transport.accept(20)
                    if chan is None:
                        return
                        
                    # Keep thread alive to prevent garbage collection of transport/socket
                    import time
                    while transport.is_active():
                        time.sleep(1)
                except Exception as ex:
                    logger.error(f"SFTP handler error: {ex}")

            while self.running:
                try:
                    conn, addr = self.server_socket.accept()
                    threading.Thread(target=handle_client, args=(conn,), daemon=True).start()
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"SFTP connection error: {e}")
        except Exception as e:
            logger.error(f"SFTP server failed: {e}")
            raise
        finally:
            if self.server_socket:
                self.server_socket.close()

    async def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()

    async def stop(self):
        self.running = False
        if self.thread:
            pass
        logger.info("SFTP server stopped")
