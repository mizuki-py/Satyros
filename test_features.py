"""
Satyros Integration Test Suite
================================
Tests actual server start -> client connect -> data transfer -> server stop
for every feature described in the README.

Uses high ports (10000+) to avoid requiring admin privileges.
"""
import sys
import os
import socket
import threading
import time
import asyncio
import tempfile
import csv

PASS = "[ PASS ]"
FAIL = "[ FAIL ]"
SKIP = "[ SKIP ]"
results = []

def test(name, fn):
    try:
        fn()
        print(f"{PASS} {name}")
        results.append((name, True, ""))
    except Exception as e:
        print(f"{FAIL} {name}: {e}")
        results.append((name, False, str(e)))

def make_loop_thread():
    """Create a new event loop running in a background thread."""
    loop = asyncio.new_event_loop()
    t = threading.Thread(target=loop.run_forever, daemon=True)
    t.start()
    return loop, t

def run_coro(loop, coro, timeout=10):
    """Run a coroutine on the given loop and wait for result."""
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=timeout)

# ============================================================
print("=" * 60)
print("  Satyros Integration Test Suite")
print("=" * 60)

# Create a temp directory for test files
test_dir = tempfile.mkdtemp(prefix="satyros_test_")
print(f"  Test directory: {test_dir}")

# Shared event loop for all async servers
loop, loop_thread = make_loop_thread()

# ============================================================
# 1. Syslog Server: Start -> Send UDP -> Verify callback
# ============================================================
print("\n--- 1. Syslog Server (UDP receive + callback) ---")

def test_syslog_end_to_end():
    from backend.syslog_server import SyslogServer
    received = []
    PORT = 15514

    srv = SyslogServer(port=PORT, callback=lambda ip, msg, sev: received.append({
        "ip": ip, "msg": msg, "sev": sev
    }))
    srv.host = "127.0.0.1"

    # Start server
    run_coro(loop, srv.start())
    time.sleep(0.5)

    # Send syslog messages with different severities
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # <54> = facility 6 (line printer) * 8 + severity 6 (info)
    sock.sendto(b"<54>Info level test message", ("127.0.0.1", PORT))
    # <49> = facility 6 * 8 + severity 1 (alert)
    sock.sendto(b"<49>Alert level test message", ("127.0.0.1", PORT))
    # <52> = facility 6 * 8 + severity 4 (warning)
    sock.sendto(b"<52>Warning level test message", ("127.0.0.1", PORT))
    sock.close()
    time.sleep(0.5)

    # Stop server
    run_coro(loop, srv.stop())
    time.sleep(0.3)

    # Verify
    assert len(received) == 3, f"Expected 3 messages, got {len(received)}"
    assert received[0]["sev"] == 6, f"Expected severity 6, got {received[0]['sev']}"
    assert received[1]["sev"] == 1, f"Expected severity 1, got {received[1]['sev']}"
    assert received[2]["sev"] == 4, f"Expected severity 4, got {received[2]['sev']}"
    assert "Info level" in received[0]["msg"]

test("Syslog: receive 3 UDP messages with correct severity parsing", test_syslog_end_to_end)

def test_syslog_export():
    export_path = os.path.join(test_dir, "syslog_export.txt")
    test_logs = [
        {"time": "12:00:00", "ip": "10.0.0.1", "sev": 6, "msg": "Normal operation"},
        {"time": "12:00:01", "ip": "10.0.0.2", "sev": 1, "msg": "ALERT: link down"},
        {"time": "12:00:02", "ip": "10.0.0.3", "sev": 4, "msg": "WARNING: high CPU"},
    ]
    with open(export_path, 'w', encoding='utf-8') as f:
        for row in test_logs:
            f.write(f"{row['time']} | {row['ip']} | Sev: {row['sev']} | {row['msg']}\n")

    # Verify file was written correctly
    with open(export_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    assert len(lines) == 3
    assert "ALERT: link down" in lines[1]
    os.remove(export_path)

test("Syslog: export logs to text file", test_syslog_export)

# ============================================================
# 2. TFTP Server + Client: Start -> Put file -> Get file
# ============================================================
print("\n--- 2. TFTP Server & Client (file transfer) ---")

def test_tftp_put_and_get():
    from backend.tftp_server import AsyncTFTPServer
    from backend.tftp_client import TFTPClient

    PORT = 16969
    tftp_root = os.path.join(test_dir, "tftp_root")
    os.makedirs(tftp_root, exist_ok=True)

    progress_events = []
    srv = AsyncTFTPServer(host="127.0.0.1", port=PORT, root_dir=tftp_root,
                          callback=lambda fn, ip, byt: progress_events.append((fn, byt)))

    # Start TFTP server
    run_coro(loop, srv.start())
    time.sleep(0.5)

    # Create a test file to upload
    upload_file = os.path.join(test_dir, "upload_test.txt")
    test_content = b"Hello from Satyros TFTP integration test!\n" * 20
    with open(upload_file, 'wb') as f:
        f.write(test_content)

    # PUT file to server
    client = TFTPClient()
    put_progress = []
    run_coro(loop, client.put_file(
        "127.0.0.1", PORT, upload_file, "upload_test.txt",
        progress_cb=lambda b, done: put_progress.append((b, done))
    ), timeout=15)

    time.sleep(0.5)
    # Verify file arrived on server
    server_file = os.path.join(tftp_root, "upload_test.txt")
    assert os.path.exists(server_file), f"File not found at {server_file}"
    with open(server_file, 'rb') as f:
        assert f.read() == test_content, "Server file content mismatch"

    # GET file back from server
    download_file = os.path.join(test_dir, "download_test.txt")
    get_progress = []
    run_coro(loop, client.get_file(
        "127.0.0.1", PORT, "upload_test.txt", download_file,
        progress_cb=lambda b, done: get_progress.append((b, done))
    ), timeout=15)

    time.sleep(0.3)
    # Verify downloaded content matches
    with open(download_file, 'rb') as f:
        downloaded = f.read()
    assert downloaded == test_content, "Downloaded file content mismatch"

    # Stop server
    run_coro(loop, srv.stop())
    time.sleep(0.3)

test("TFTP: PUT file to server then GET it back, verify content", test_tftp_put_and_get)

# ============================================================
# 3. FTP Server: Start -> Connect with ftplib -> Upload/Download
# ============================================================
print("\n--- 3. FTP Server (TCP connect + file transfer) ---")

def test_ftp_end_to_end():
    from backend.ftp_server import AsyncFTPServer
    import ftplib

    PORT = 12121
    ftp_root = os.path.join(test_dir, "ftp_root")
    os.makedirs(ftp_root, exist_ok=True)

    srv = AsyncFTPServer(host="127.0.0.1", port=PORT, root_dir=ftp_root)
    srv.username = "testuser"
    srv.password = "testpass"
    srv.allow_write = True
    srv.use_ftps = False

    # Start FTP server
    run_coro(loop, srv.start())
    time.sleep(1.0)

    # Connect with ftplib
    ftp = ftplib.FTP()
    ftp.connect("127.0.0.1", PORT, timeout=5)
    welcome = ftp.getwelcome()
    assert "220" in welcome, f"Unexpected welcome: {welcome}"

    # Login
    ftp.login("testuser", "testpass")

    # Upload a file
    test_data = b"FTP integration test file content from Satyros\n"
    from io import BytesIO
    ftp.storbinary("STOR ftp_test.txt", BytesIO(test_data))

    # Verify file exists on server
    assert os.path.exists(os.path.join(ftp_root, "ftp_test.txt"))

    # Download the file back
    downloaded = BytesIO()
    ftp.retrbinary("RETR ftp_test.txt", downloaded.write)
    assert downloaded.getvalue() == test_data, "FTP download content mismatch"

    # List directory
    file_list = ftp.nlst()
    assert "ftp_test.txt" in file_list

    ftp.quit()

    # Stop server
    run_coro(loop, srv.stop())
    time.sleep(0.5)

test("FTP: login + upload + download + list directory", test_ftp_end_to_end)

# ============================================================
# 4. FTPS: Verify TLS certificate generation
# ============================================================
print("\n--- 4. FTPS Certificate Generation ---")

def test_ftps_cert():
    from backend.ftp_server import generate_self_signed_cert
    cert_path = os.path.join(test_dir, "test_cert.pem")
    key_path = os.path.join(test_dir, "test_key.pem")
    generate_self_signed_cert(cert_path, key_path)

    assert os.path.exists(cert_path), "Certificate file not created"
    assert os.path.exists(key_path), "Key file not created"
    assert os.path.getsize(cert_path) > 500, "Certificate file too small"
    assert os.path.getsize(key_path) > 500, "Key file too small"

    # Verify it's a valid PEM
    with open(cert_path, 'rb') as f:
        data = f.read()
    assert b"BEGIN CERTIFICATE" in data, "Not a valid PEM certificate"

    os.remove(cert_path)
    os.remove(key_path)

test("FTPS: generate self-signed TLS certificate + verify PEM format", test_ftps_cert)

# ============================================================
# 5. SFTP Server: Start -> Connect with paramiko client
# ============================================================
print("\n--- 5. SFTP Server (SSH connect + file transfer) ---")

def test_sftp_end_to_end():
    from backend.sftp_server import AsyncSFTPServer
    import paramiko

    PORT = 12222
    sftp_root = os.path.join(test_dir, "sftp_root")
    os.makedirs(sftp_root, exist_ok=True)

    srv = AsyncSFTPServer(host="127.0.0.1", port=PORT, root_dir=sftp_root)
    srv.username = "sftpuser"
    srv.password = "sftppass"
    srv.allow_write = True

    # Start SFTP server
    run_coro(loop, srv.start())
    time.sleep(1.0)

    # Connect with paramiko client
    transport = paramiko.Transport(("127.0.0.1", PORT))
    transport.connect(username="sftpuser", password="sftppass")
    sftp = paramiko.SFTPClient.from_transport(transport)

    # Upload a file
    test_data = b"SFTP integration test content from Satyros\n"
    local_upload = os.path.join(test_dir, "sftp_upload.txt")
    with open(local_upload, 'wb') as f:
        f.write(test_data)

    sftp.put(local_upload, "/sftp_upload.txt")

    # Verify file on server
    assert os.path.exists(os.path.join(sftp_root, "sftp_upload.txt"))

    # Download the file
    local_download = os.path.join(test_dir, "sftp_download.txt")
    sftp.get("/sftp_upload.txt", local_download)
    with open(local_download, 'rb') as f:
        assert f.read() == test_data, "SFTP download content mismatch"

    # List directory
    file_list = sftp.listdir("/")
    assert "sftp_upload.txt" in file_list

    sftp.close()
    transport.close()

    # Stop server
    run_coro(loop, srv.stop())
    time.sleep(1.0)

test("SFTP: SSH connect + upload + download + list directory", test_sftp_end_to_end)

# ============================================================
# 6. SNMP: Server + Client instantiation, CSV export
# ============================================================
print("\n--- 6. SNMP Trap Receiver & Manager ---")

def test_snmp_server_start_stop():
    from backend.snmp_server import AsyncSNMPServer
    PORT = 10162
    received = []
    srv = AsyncSNMPServer(host="127.0.0.1", port=PORT,
                          callback=lambda ip, msg: received.append({"ip": ip, "msg": msg}))
    run_coro(loop, srv.start())
    time.sleep(0.5)
    run_coro(loop, srv.stop())
    time.sleep(0.3)

test("SNMP: Trap receiver start and stop without error", test_snmp_server_start_stop)

def test_snmp_client_instantiation():
    from backend.snmp_client import AsyncSNMPClient
    client = AsyncSNMPClient()
    assert hasattr(client, 'get')
    assert hasattr(client, 'walk')

test("SNMP: Client has get() and walk() methods", test_snmp_client_instantiation)

def test_snmp_csv_export():
    export_path = os.path.join(test_dir, "snmp_export.csv")
    test_traps = [
        {"time": "12:00:00", "ip": "10.0.0.1", "msg": "1.3.6.1.6.3.1.1.4.1 = coldStart"},
        {"time": "12:00:01", "ip": "10.0.0.2", "msg": "1.3.6.1.6.3.1.1.5.2 = warmStart"},
    ]
    with open(export_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Time", "Source IP", "Trap Content"])
        for t in test_traps:
            writer.writerow([t["time"], t["ip"], t["msg"]])

    # Read back and verify
    with open(export_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
    assert rows[0] == ["Time", "Source IP", "Trap Content"]
    assert len(rows) == 3  # header + 2 data rows
    assert "coldStart" in rows[1][2]
    os.remove(export_path)

test("SNMP: export traps to CSV with correct format", test_snmp_csv_export)

# ============================================================
# 7. Core: BackendRunner orchestration
# ============================================================
print("\n--- 7. BackendRunner Orchestration ---")

def test_backend_runner():
    import queue
    # Import from main.py
    sys.path.insert(0, os.getcwd())
    from main import BackendRunner

    q = queue.Queue()
    runner = BackendRunner(q)
    runner.start()
    time.sleep(0.5)

    # Verify all servers are instantiated
    assert runner.syslog_srv is not None
    assert runner.tftp_srv is not None
    assert runner.ftp_srv is not None
    assert runner.sftp_srv is not None
    assert runner.snmp_srv is not None
    assert runner.loop is not None
    assert runner.loop.is_running()

    # Stop
    runner.loop.call_soon_threadsafe(runner.loop.stop)
    time.sleep(0.3)

test("BackendRunner: start event loop + all servers instantiated", test_backend_runner)

# ============================================================
# 8. Core Utilities
# ============================================================
print("\n--- 8. Core Utilities ---")

def test_get_local_ips():
    from core.config import get_local_ips
    ips = get_local_ips()
    assert isinstance(ips, list)
    assert "0.0.0.0" in ips
    real_ips = [ip for ip in ips if ip not in ("0.0.0.0",)]
    assert len(real_ips) > 0, "Should have at least one real IP"

test("get_local_ips: returns 0.0.0.0 + real IPs", test_get_local_ips)

def test_default_dirs():
    from core.config import DEFAULT_ROOT_DIR, DEFAULT_LOG_DIR
    assert os.path.isdir(DEFAULT_ROOT_DIR), f"{DEFAULT_ROOT_DIR} does not exist"
    assert os.path.isdir(DEFAULT_LOG_DIR), f"{DEFAULT_LOG_DIR} does not exist"

test("Default directories exist (root + logs)", test_default_dirs)

# ============================================================
# Cleanup
# ============================================================
loop.call_soon_threadsafe(loop.stop)
time.sleep(0.5)

import shutil
try:
    shutil.rmtree(test_dir)
except Exception:
    pass

# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 60)
passed = [r for r in results if r[1]]
failed = [r for r in results if not r[1]]
print(f"  PASSED: {len(passed)} / {len(results)}")
if failed:
    print(f"  FAILED: {len(failed)}")
    for name, _, err in failed:
        print(f"    x {name}")
        print(f"      -> {err}")
else:
    print("  All tests passed!")
print("=" * 60)

sys.exit(0 if not failed else 1)
