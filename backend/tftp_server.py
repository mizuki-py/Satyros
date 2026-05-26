import asyncio
import logging
from pathlib import Path
import os
import py3tftp.file_io
from py3tftp.protocols import TFTPServerProtocol
from core.config import TFTP_PORT, DEFAULT_ROOT_DIR

logger = logging.getLogger(__name__)

class AsyncTFTPServer:
    def __init__(self, host='0.0.0.0', port=TFTP_PORT, root_dir=DEFAULT_ROOT_DIR, callback=None):
        self.host = host
        self.port = port
        self.root_dir = root_dir
        self.callback = callback
        self.transport = None

    async def start(self):
        loop = asyncio.get_running_loop()

        class MyTFTPServerProtocol(TFTPServerProtocol):
            def datagram_received(self_, data, addr):
                logger.debug('received: {}'.format(data.decode(errors='replace')))

                first_packet = self_.packet_factory.from_bytes(data)
                protocol = self_.select_protocol(first_packet)
                file_handler_cls = self_.select_file_handler(first_packet)

                def my_file_handler_cls(filename, opts):
                    def custom_sanitize_fname(fname):
                        path_str = os.fsdecode(fname).replace('\\', '/').lstrip('/')
                        try:
                            abs_path = (Path(self.root_dir) / path_str).resolve(strict=False)
                            root_path = Path(self.root_dir).resolve(strict=True)
                            abs_path.relative_to(root_path)
                        except (ValueError, FileNotFoundError, RuntimeError):
                            raise FileNotFoundError
                        if abs_path.is_reserved():
                            raise FileNotFoundError
                        return abs_path

                    orig_sanitize = py3tftp.file_io.sanitize_fname
                    py3tftp.file_io.sanitize_fname = custom_sanitize_fname
                    try:
                        handler = file_handler_cls(filename, opts)
                    finally:
                        py3tftp.file_io.sanitize_fname = orig_sanitize

                    ip = addr[0]
                    fname_str = filename.decode(errors='replace') if isinstance(filename, bytes) else str(filename)
                    
                    if hasattr(handler, 'read_chunk'):
                        orig_read_chunk = handler.read_chunk
                        def new_read_chunk(size=None):
                            chunk = orig_read_chunk(size)
                            handler._bytes_transferred = getattr(handler, '_bytes_transferred', 0) + len(chunk)
                            if self.callback:
                                self.callback(fname_str, ip, handler._bytes_transferred)
                            return chunk
                        handler.read_chunk = new_read_chunk
                    
                    if hasattr(handler, 'write_chunk'):
                        orig_write_chunk = handler.write_chunk
                        def new_write_chunk(chunk_data):
                            bytes_written = orig_write_chunk(chunk_data)
                            handler._bytes_transferred = getattr(handler, '_bytes_transferred', 0) + (bytes_written or 0)
                            if self.callback:
                                self.callback(fname_str, ip, handler._bytes_transferred)
                            return bytes_written
                        handler.write_chunk = new_write_chunk
                    return handler

                connect = self_.loop.create_datagram_endpoint(
                    lambda: protocol(data, my_file_handler_cls, addr, self_.extra_opts),
                    local_addr=(self_.host_interface, 0)
                )
                self_.loop.create_task(connect)

        listen = loop.create_datagram_endpoint(
            lambda: MyTFTPServerProtocol(self.host, loop, {}),
            local_addr=(self.host, self.port)
        )
        self.transport, self.protocol = await listen
        logger.info(f"TFTP server started at {self.host}:{self.port} (Root: {self.root_dir})")

    async def stop(self):
        if self.transport:
            self.transport.close()
        logger.info("TFTP server stopped")
