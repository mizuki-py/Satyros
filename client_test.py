"""
Satyros Client Test Script
==========================
This script tests the Satyros servers by acting as a client.
It sends traffic to the specified IP address.
"""
import sys
import os
import socket
import time
import asyncio
import ftplib
import paramiko
import tempfile

TARGET_IP = "192.168.3.99"
PASS = "[ PASS ]"
FAIL = "[ FAIL ]"
results = []

def test(name, fn):
    try:
        fn()
        print(f"{PASS} {name}")
        results.append((name, True, ""))
    except Exception as e:
        print(f"{FAIL} {name}: {e}")
        results.append((name, False, str(e)))

print("=" * 60)
print(f"  Satyros Client Test Suite -> Target: {TARGET_IP}")
print("=" * 60)

test_dir = tempfile.mkdtemp(prefix="satyros_client_test_")

def test_syslog():
    print(f"\n--- 1. Syslog Test (UDP 514) ---")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Send Emergency (0)
    sock.sendto(b"<0>System is unusable (Emergency test)", (TARGET_IP, 514))
    time.sleep(0.5)
    # Send Warning (4)
    sock.sendto(b"<36>High memory usage (Warning test)", (TARGET_IP, 514))
    time.sleep(0.5)
    # Send Info (6)
    sock.sendto(b"<54>Normal operation resumed (Info test)", (TARGET_IP, 514))
    sock.close()
    print("Sent 3 syslog messages (Emergency, Warning, Info).")

test("Send Syslog messages", test_syslog)

def test_tftp():
    print(f"\n--- 2. TFTP Test (UDP 69) ---")
    # We use our own client to put a file
    from backend.tftp_client import TFTPClient
    client = TFTPClient()
    
    upload_file = os.path.join(test_dir, "tftp_test_2.txt")
    with open(upload_file, 'wb') as f:
        f.write(b"TFTP test data from automated script.")
    
    loop = asyncio.new_event_loop()
    try:
        coro = client.put_file(TARGET_IP, 69, upload_file, "tftp_test_3.txt", progress_cb=lambda b, d: None)
        loop.run_until_complete(coro)
        print("Sent TFTP file 'tftp_test_3.txt'.")
    except Exception as e:
        print(f"TFTP Error: {e}")

# test("Send TFTP file", test_tftp)

def test_ftp():
    print(f"\n--- 3. FTP Test (TCP 21) ---")
    ftp = ftplib.FTP()
    ftp.connect(TARGET_IP, 21, timeout=5)
    ftp.login("admin", "password")
    
    upload_file = os.path.join(test_dir, "ftp_test_2.txt")
    with open(upload_file, 'wb') as f:
        f.write(b"FTP test data from automated script.")
        
    with open(upload_file, 'rb') as f:
        ftp.storbinary("STOR ftp_test_2.txt", f)
        
    ftp.quit()
    print("Uploaded FTP file 'ftp_test_2.txt'.")

test("Upload FTP file", test_ftp)

def test_sftp():
    print(f"\n--- 4. SFTP Test (TCP 22) ---")
    transport = paramiko.Transport((TARGET_IP, 22))
    transport.connect(username="admin", password="password")
    sftp = paramiko.SFTPClient.from_transport(transport)
    
    upload_file = os.path.join(test_dir, "sftp_test_2.txt")
    with open(upload_file, 'wb') as f:
        f.write(b"SFTP test data from automated script.")
        
    sftp.put(upload_file, "/sftp_test_2.txt")
    sftp.close()
    transport.close()
    print("Uploaded SFTP file 'sftp_test_2.txt'.")

test("Upload SFTP file", test_sftp)

def test_snmp():
    print(f"\n--- 5. SNMP Trap Test (UDP 162) ---")
    import asyncio
    from pysnmp.hlapi.asyncio import SnmpEngine, send_notification, CommunityData, UdpTransportTarget, ContextData, NotificationType, ObjectIdentity
    
    async def run_trap():
        errorIndication, errorStatus, errorIndex, varBinds = await send_notification(
            SnmpEngine(),
            CommunityData('public', mpModel=1), # SNMPv2c
            UdpTransportTarget((TARGET_IP, 162)),
            ContextData(),
            'trap',
            NotificationType(ObjectIdentity('1.3.6.1.6.3.1.1.5.1')) # coldStart
        )
        if errorIndication:
            raise Exception(errorIndication)

    asyncio.run(run_trap())
    print("Sent SNMP coldStart trap.")

test("Send SNMP Trap", test_snmp)

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
    print("  All client tests passed!")
print("=" * 60)
sys.exit(0 if not failed else 1)
