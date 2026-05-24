# Satyros v0.3.2

Satyros is a networking tool. It provides a unified, graphical interface for running and managing essential network services (TFTP, FTP, SFTP, Syslog, and SNMP) in a single application.

## Features

- **TFTP Server & Client**
  - Run a TFTP server with configurable listen IP, port, and root directory.
  - View real-time active server transfers.
  - Use the built-in TFTP client to Get or Put files.

- **FTP / SFTP / FTPS Server**
  - Run a standard FTP server.
  - Enable FTPS (Implicit TLS) with automatic, on-the-fly self-signed certificate generation.
  - Run an SFTP server powered by `paramiko` for secure file transfers.
  - Shared user authentication and directory access controls.

- **Syslog Server**
  - Receive and view syslog messages in real-time.
  - Visual color-coding based on severity (Emergency/Alert/Critical = Red, Warning = Yellow, Info = White).
  - Search and filter logs instantly.
  - Export logs to a text file for further analysis.
  - Automatic log rotation (daily `syslog.log`).

- **SNMP Manager & Trap Receiver**
  - **Trap Receiver**: Listen for SNMP traps (v1/v2c/v3). Automatically decodes OIDs into human-readable strings using MIB dictionaries. Export traps to a CSV file.
  - **SNMP Manager**: Perform SNMP `Get` and `Walk` queries with support for SNMPv3 authentication and privacy protocols.

- **Modern GUI**
  - Built with Flet, offering a clean, responsive, and robust user interface.
  - Safe against UI rendering crashes even on older Flet clients.

## Running from Source

Install the required dependencies:
```bash
pip install -r requirements.txt
```

Launch the application:
```bash
python main.py
```

## Build

To compile Satyros into a standalone executable, use the Flet CLI:
```bash
flet pack main.py --icon icon.ico --name Satyros --product-name Satyros --product-version 0.3.2 --file-version 0.3.2.0 --file-description Satyros --company-name Satyros --copyright "2026 Satyros" --add-data "assets:assets"
```

## Notes on Execution

When you run the compiled standalone executable (`Satyros.exe`), please be aware of the following file system behaviors:
- **Temporary Files**: PyInstaller automatically extracts the Python runtime and application scripts to a temporary folder (`%TEMP%\_MEIxxxxxx`). This folder is automatically deleted when the application is closed.
- **Flet UI Cache**: The Flet GUI framework will extract its core UI engine and assets (such as fonts and shaders) into your user profile directory (`~/.flet/`). This is done only once to speed up subsequent launches and will remain on your system even after the application is closed.

## Credit
- mizuki-py
- Antigravity (Gemini,Claude)
