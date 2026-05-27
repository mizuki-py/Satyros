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
        sock.settimeout(1.0) # Set timeout to 1.0 second for active retransmissions
        encoded_filename = remote_filename.encode()
        req = struct.pack(f">h{len(encoded_filename)}sB5sB", self.OP_RRQ, encoded_filename, 0, b"octet", 0)
        
        last_packet_sent = req
        last_addr = (host, port)
        sock.sendto(last_packet_sent, last_addr)

        expected_block = 1
        bytes_received = 0
        retries = 0
        MAX_RETRIES = 5
        
        try:
            with open(local_filename, "wb") as f:
                while True:
                    try:
                        data, addr = sock.recvfrom(4096)
                        retries = 0 # Reset retries on successful packet receipt
                    except socket.timeout:
                        retries += 1
                        if retries > MAX_RETRIES:
                            raise Exception("TFTP transfer timed out (max retries exceeded)")
                        logger.warning(f"Timeout occurred, retransmitting last packet (retry {retries}/{MAX_RETRIES})")
                        sock.sendto(last_packet_sent, last_addr)
                        continue

                    opcode, = struct.unpack(">h", data[:2])
                    
                    if opcode == self.OP_DATA:
                        block, = struct.unpack(">H", data[2:4])
                        if block == expected_block:
                            f.write(data[4:])
                            bytes_received += len(data[4:])
                            if progress_cb:
                                progress_cb(bytes_received, False)
                            
                            ack = struct.pack(">hH", self.OP_ACK, block)
                            last_packet_sent = ack
                            last_addr = addr
                            sock.sendto(ack, addr)
                            expected_block = (expected_block + 1) & 0xFFFF
                            
                            if len(data[4:]) < 512:
                                if progress_cb: progress_cb(bytes_received, True)
                                break
                        elif block == (expected_block - 1) & 0xFFFF:
                            # Re-send ACK for duplicate block (Bug 19)
                            ack = struct.pack(">hH", self.OP_ACK, block)
                            sock.sendto(ack, addr)
                    elif opcode == self.OP_ERROR:
                        code, = struct.unpack(">h", data[2:4])
                        msg = data[4:-1]
                        raise Exception(f"TFTP Error {code}: {msg.decode(errors='ignore')}")
                        
        except Exception as e:
            logger.error(f"TFTP Get failed: {e}")
            if os.path.exists(local_filename):
                try:
                    os.remove(local_filename)
                except OSError:
                    pass
            raise
        finally:
            sock.close()

    async def put_file(self, host, port, local_filename, remote_filename, progress_cb=None):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._put_file_sync, host, port, local_filename, remote_filename, progress_cb)

    def _put_file_sync(self, host, port, local_filename, remote_filename, progress_cb):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(1.0) # Set timeout to 1.0 second for active retransmissions
        encoded_filename = remote_filename.encode()
        req = struct.pack(f">h{len(encoded_filename)}sB5sB", self.OP_WRQ, encoded_filename, 0, b"octet", 0)
        
        last_packet_sent = req
        last_addr = (host, port)
        sock.sendto(last_packet_sent, last_addr)
        
        expected_block = 0
        bytes_sent = 0
        retries = 0
        MAX_RETRIES = 5
        
        try:
            with open(local_filename, "rb") as f:
                current_chunk = b""
                is_last_chunk = False
                
                while True:
                    try:
                        data, addr = sock.recvfrom(4096)
                        retries = 0 # Reset retries on successful packet receipt
                    except socket.timeout:
                        retries += 1
                        if retries > MAX_RETRIES:
                            raise Exception("TFTP transfer timed out (max retries exceeded)")
                        logger.warning(f"Timeout occurred, retransmitting last packet (retry {retries}/{MAX_RETRIES})")
                        sock.sendto(last_packet_sent, last_addr)
                        continue

                    opcode, = struct.unpack(">h", data[:2])
                    if opcode == self.OP_ACK:
                        block, = struct.unpack(">H", data[2:4])
                        if block == expected_block:
                            if is_last_chunk:
                                # Received final ACK for the last sent block
                                if progress_cb:
                                    progress_cb(bytes_sent, True)
                                break
                            
                            expected_block = (expected_block + 1) & 0xFFFF
                            current_chunk = f.read(512)
                            pkt = struct.pack(">hH", self.OP_DATA, expected_block) + current_chunk
                            
                            last_packet_sent = pkt
                            last_addr = addr
                            sock.sendto(pkt, addr)
                            
                            bytes_sent += len(current_chunk)
                            if progress_cb:
                                progress_cb(bytes_sent, False)
                                
                            if len(current_chunk) < 512:
                                is_last_chunk = True
                        elif block == (expected_block - 1) & 0xFFFF:
                            # Server re-sent ACK for previous block, indicating it missed our last DATA packet
                            logger.info(f"Duplicate ACK received for block {block}, retransmitting last packet")
                            sock.sendto(last_packet_sent, last_addr)
                    elif opcode == self.OP_ERROR:
                        code, = struct.unpack(">h", data[2:4])
                        msg = data[4:-1]
                        raise Exception(f"TFTP Error {code}: {msg.decode(errors='ignore')}")
                        
        except Exception as e:
            logger.error(f"TFTP Put failed: {e}")
            raise
        finally:
            sock.close()
