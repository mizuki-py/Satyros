import sys
import os
import zipfile

def setup_flet_view():
    if getattr(sys, 'frozen', False):
        bundle_zip = os.path.join(sys._MEIPASS, 'flet_desktop', 'app', 'flet-windows.zip')
        if os.path.exists(bundle_zip):
            extract_dir = os.path.join(sys._MEIPASS, 'flet_engine_extracted')
            if not os.path.exists(extract_dir):
                with zipfile.ZipFile(bundle_zip, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            os.environ['FLET_VIEW_PATH'] = extract_dir

setup_flet_view()

# Monkey patch flet.utils.deprecated_enum to fix Python 3.12+ compatibility issue
try:
    import flet.utils.deprecated_enum
    orig_getattr = flet.utils.deprecated_enum.DeprecatedEnumMeta.__getattr__
    def fixed_getattr(cls, name):
        try:
            return orig_getattr(cls, name)
        except AttributeError as e:
            if "'super' object has no attribute '__getattr__'" in str(e):
                raise AttributeError(f"'{cls.__name__}' object has no attribute '{name}'")
            raise
    flet.utils.deprecated_enum.DeprecatedEnumMeta.__getattr__ = fixed_getattr
except ImportError:
    pass

import asyncio
import threading
from backend.syslog_server import SyslogServer
from backend.tftp_server import AsyncTFTPServer
from backend.ftp_server import AsyncFTPServer
from backend.sftp_server import AsyncSFTPServer
from backend.snmp_server import AsyncSNMPServer

class BackendRunner:
    def __init__(self, log_queue):
        self.log_queue = log_queue
        
        def syslog_cb(ip, msg, severity=6):
            self.log_queue.put({"type": "syslog", "ip": ip, "message": msg, "severity": severity})
            
        def snmp_cb(ip, msg):
            self.log_queue.put({"type": "snmp", "ip": ip, "message": msg})

        def tftp_cb(filename, ip, bytes_transferred):
            self.log_queue.put({"type": "tftp", "filename": filename, "ip": ip, "bytes": bytes_transferred})

        def ftp_cb(filename, ip, status):
            self.log_queue.put({"type": "ftp", "filename": filename, "ip": ip, "status": status})

        self.syslog_srv = SyslogServer(callback=syslog_cb)
        self.tftp_srv = AsyncTFTPServer(callback=tftp_cb)
        self.ftp_srv = AsyncFTPServer(callback=ftp_cb)
        self.sftp_srv = AsyncSFTPServer()
        self.snmp_srv = AsyncSNMPServer(callback=snmp_cb)
        
        self.loop = asyncio.new_event_loop()

    def run_loop_in_thread(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def start(self):
        t = threading.Thread(target=self.run_loop_in_thread, daemon=True)
        t.start()
        
    def start_server(self, srv_name, host, port, root_dir=None, **kwargs):
        srv = getattr(self, srv_name)
        srv.host = host
        
        try:
            parsed_port = int(port)
            if not (1 <= parsed_port <= 65535):
                raise ValueError("Port must be between 1 and 65535")
            srv.port = parsed_port
        except ValueError as e:
            msg = f"Invalid port for {srv_name}: {e}"
            print(msg)
            self.log_queue.put({"type": "error", "message": msg})
            # Let the GUI button state be reset if needed, but we don't start the server
            return

        if root_dir is not None:
            srv.root_dir = root_dir
            
        def done_callback(fut):
            try:
                fut.result()
            except Exception as e:
                msg = f"Failed to start {srv_name} on {host}:{port}. Error: {e}"
                print(msg)
                self.log_queue.put({"type": "error", "message": msg})
                
        future = asyncio.run_coroutine_threadsafe(srv.start(**kwargs), self.loop)
        future.add_done_callback(done_callback)

    def stop_server(self, srv_name):
        srv = getattr(self, srv_name)
        asyncio.run_coroutine_threadsafe(srv.stop(), self.loop)

def main():
    import ctypes
    import sys
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.satyros.app.v2")
        except Exception:
            pass
    
    import queue
    log_queue = queue.Queue()
    runner = BackendRunner(log_queue)
    runner.start()
    
    try:
        from gui.flet_app import start_flet_app
        start_flet_app(runner, log_queue)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
