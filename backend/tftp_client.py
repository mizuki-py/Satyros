import asyncio
import logging
import socket
import struct
import os

logger = logging.getLogger(__name__)

class TFTPClient:
    OP_RRQ = 1
    OP_WRQ = 2
    OP_DATA = 3
    OP_ACK = 4
    OP_ERROR = 5

    def __init__(self):
        pass

    async def get_file(self, host, port, remote_filename, local_filename, progress_cb=None):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._get_file_sync, host, port, remote_filename, local_filename, progress_cb)

    def _get_file_sync(self, host, port, remote_filename, local_filename, progress_cb):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5.0)
        encoded_filename = remote_filename.encode()
        req = struct.pack(f">h{len(encoded_filename)}sB5sB", self.OP_RRQ, encoded_filename, 0, b"octet", 0)
        sock.sendto(req, (host, port))

        expected_block = 1
        bytes_received = 0
        try:
            with open(local_filename, "wb") as f:
                while True:
                    data, addr = sock.recvfrom(4096)
                    opcode, = struct.unpack(">h", data[:2])
                    
                    if opcode == self.OP_DATA:
                        block, = struct.unpack(">h", data[2:4])
                        if block == expected_block:
                            f.write(data[4:])
                            bytes_received += len(data[4:])
                            if progress_cb:
                                progress_cb(bytes_received, False) # (bytes, is_done)
                            
                            ack = struct.pack(">hh", self.OP_ACK, block)
                            sock.sendto(ack, addr)
                            expected_block = (expected_block + 1) & 0xFFFF
                            
                            if len(data[4:]) < 512:
                                if progress_cb: progress_cb(bytes_received, True)
                                break
                    elif opcode == self.OP_ERROR:
                        code, = struct.unpack(">h", data[2:4])
                        msg = data[4:-1]
                        logger.error(f"TFTP Error {code}: {msg.decode(errors='ignore')}")
                        raise Exception(f"TFTP Error {code}: {msg.decode(errors='ignore')}")
                        
        except Exception as e:
            logger.error(f"TFTP Get failed: {e}")
            raise
        finally:
            sock.close()

    async def put_file(self, host, port, local_filename, remote_filename, progress_cb=None):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._put_file_sync, host, port, local_filename, remote_filename, progress_cb)

    def _put_file_sync(self, host, port, local_filename, remote_filename, progress_cb):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(5.0)
        encoded_filename = remote_filename.encode()
        req = struct.pack(f">h{len(encoded_filename)}sB5sB", self.OP_WRQ, encoded_filename, 0, b"octet", 0)
        sock.sendto(req, (host, port))
        
        expected_block = 0
        bytes_sent = 0
        try:
            with open(local_filename, "rb") as f:
                while True:
                    data, addr = sock.recvfrom(4096)
                    opcode, = struct.unpack(">h", data[:2])
                    if opcode == self.OP_ACK:
                        block, = struct.unpack(">h", data[2:4])
                        if block == expected_block:
                            expected_block = (expected_block + 1) & 0xFFFF
                            chunk = f.read(512)
                            pkt = struct.pack(">hh", self.OP_DATA, expected_block) + chunk
                            sock.sendto(pkt, addr)
                            
                            bytes_sent += len(chunk)
                            if progress_cb:
                                progress_cb(bytes_sent, False)
                                
                            if len(chunk) < 512:
                                # wait for final ack
                                data, _ = sock.recvfrom(4096)
                                opcode, = struct.unpack(">h", data[:2])
                                if opcode == self.OP_ACK and progress_cb:
                                    progress_cb(bytes_sent, True)
                                break
                    elif opcode == self.OP_ERROR:
                        code, = struct.unpack(">h", data[2:4])
                        msg = data[4:-1]
                        logger.error(f"TFTP Error {code}: {msg.decode(errors='ignore')}")
                        raise Exception(f"TFTP Error {code}: {msg.decode(errors='ignore')}")
                        
        except Exception as e:
            logger.error(f"TFTP Put failed: {e}")
            raise
        finally:
            sock.close()
