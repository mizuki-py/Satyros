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
        srv.port = int(port)
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
