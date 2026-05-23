import flet as ft
import asyncio
from core.config import get_local_ips
import os

class TFTPTab:
    def __init__(self, page: ft.Page, backend_runner):
        self.page = page
        self.backend_runner = backend_runner
        self.server_running = False
        self.active_transfers = {}

    def update_progress(self, filename, ip, bytes_transferred):
        key = f"{ip} - {filename}"
        self.active_transfers[key] = bytes_transferred
        
        self.server_transfers_col.controls.clear()
        for k, v in self.active_transfers.items():
            self.server_transfers_col.controls.append(ft.Text(f"{k}: {v} bytes"))
            
        self.page.update()

    def build(self):
        # Server Controls
        ips = get_local_ips()
        self.ip_input = ft.Dropdown(label="Listen IP", value="0.0.0.0", options=[ft.dropdown.Option(ip) for ip in ips], expand=True)
        self.port_input = ft.TextField(label="Port", value="69", width=100)
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.root_input = ft.TextField(label="Root Directory", value=desktop_path, expand=True)
        
        self.btn_toggle = ft.ElevatedButton(
            content=ft.Text("Start Server"),
            on_click=self.toggle_server,
            style=ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=ft.Colors.PRIMARY)
        )

        self.server_transfers_col = ft.Column()

        server_card = ft.Card(
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Text("Server Settings", size=20, weight="bold"),
                    ft.Row([self.ip_input, self.port_input]),
                    ft.Row([
                        self.root_input
                    ]),
                    self.btn_toggle,
                    ft.Divider(),
                    ft.Text("Active Server Transfers", weight="bold"),
                    self.server_transfers_col
                ])
            )
        )

        # Client Controls
        self.client_ip = ft.TextField(label="Target IP", value="127.0.0.1", expand=True)
        self.client_remote = ft.TextField(label="Remote File", expand=True)
        self.client_local = ft.TextField(label="Local File", value=os.path.join(desktop_path, "local_file.txt"), expand=True)
        self.client_mode = ft.Dropdown(
            label="Mode",
            options=[ft.dropdown.Option("Get"), ft.dropdown.Option("Put")],
            value="Get",
            width=150
        )
        self.client_status = ft.Text("Ready")
        
        self.btn_exec = ft.Button(content=ft.Text("Execute"), on_click=self.run_client)
        
        client_card = ft.Card(
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Text("Client Settings", size=20, weight="bold"),
                    ft.Row([self.client_ip, self.client_mode]),
                    ft.Row([self.client_remote]),
                    ft.Row([
                        self.client_local
                    ]),
                    self.btn_exec,
                    self.client_status
                ])
            )
        )

        res = ft.Column([server_card, client_card], scroll=ft.ScrollMode.AUTO, expand=True)
        
        # Restore server transfers
        for k, v in self.active_transfers.items():
            self.server_transfers_col.controls.append(ft.Text(f"{k}: {v} bytes"))
            
        return res

    def toggle_server(self, e):
        self.server_running = not self.server_running
        if self.server_running:
            if isinstance(self.btn_toggle.content, ft.Text):
                self.btn_toggle.content.value = "Stop Server"
            else:
                self.btn_toggle.content = ft.Text("Stop Server")
            self.btn_toggle.style = ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=ft.Colors.ERROR)
            self.backend_runner.start_server('tftp_srv', self.ip_input.value, self.port_input.value, self.root_input.value)
        else:
            if isinstance(self.btn_toggle.content, ft.Text):
                self.btn_toggle.content.value = "Start Server"
            else:
                self.btn_toggle.content = ft.Text("Start Server")
            self.btn_toggle.style = ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=ft.Colors.PRIMARY)
            self.backend_runner.stop_server('tftp_srv')
        self.page.update()

    def run_client(self, e):
        self.client_status.value = "Executing..."
        self.client_status.color = ft.Colors.WARNING
        self.page.update()
        
        import threading
        from backend.tftp_client import TFTPClient
        
        host = self.client_ip.value
        remote = self.client_remote.value
        local = self.client_local.value
        mode = self.client_mode.value

        def progress_cb(bytes_transferred, is_done):
            def update_ui():
                if is_done:
                    self.client_status.value = f"Complete: {bytes_transferred} bytes"
                    self.client_status.color = ft.Colors.GREEN
                else:
                    self.client_status.value = f"Transferring: {bytes_transferred} bytes"
                self.page.update()
            update_ui()
            
        def _thread():
            client = TFTPClient()
            try:
                loop = self.backend_runner.loop
                if mode == "Get":
                    coro = client.get_file(host, 69, remote, local, progress_cb)
                else:
                    coro = client.put_file(host, 69, local, remote, progress_cb)
                asyncio.run_coroutine_threadsafe(coro, loop).result()
            except Exception as ex:
                self.client_status.value = f"Error: {ex}"
                self.client_status.color = ft.Colors.ERROR
                self.page.update()
                
        threading.Thread(target=_thread, daemon=True).start()
