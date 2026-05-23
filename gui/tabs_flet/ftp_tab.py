import flet as ft
from core.config import get_local_ips
import os

class FTPTab:
    def __init__(self, page: ft.Page, backend_runner):
        self.page = page
        self.backend_runner = backend_runner
        self.ftp_running = False
        self.sftp_running = False

    def build(self):
        ips = get_local_ips()
        self.ip_input = ft.Dropdown(label="Listen IP", value="0.0.0.0", options=[ft.dropdown.Option(ip) for ip in ips], expand=True)
        self.ftp_port_input = ft.TextField(label="FTP Port", value="21", width=100)
        self.sftp_port_input = ft.TextField(label="SFTP Port", value="22", width=100)
        
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
        self.root_input = ft.TextField(label="Root Directory", value=desktop_path, expand=True)

        self.user_input = ft.TextField(label="Username", value="admin", expand=True)
        self.pass_input = ft.TextField(label="Password", value="password", password=True, can_reveal_password=True, expand=True)
        self.write_chk = ft.Checkbox(label="Allow Write", value=True)
        self.ftps_chk = ft.Checkbox(label="Use FTPS (Implicit TLS)", value=False)
        self.btn_ftp = ft.ElevatedButton(content=ft.Text("Start FTP"), on_click=self.toggle_ftp)
        self.btn_sftp = ft.ElevatedButton(content=ft.Text("Start SFTP"), on_click=self.toggle_sftp)

        self.transfers_col = ft.Column()

        return ft.Card(
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Text("FTP / SFTP Server Settings", size=20, weight="bold"),
                    ft.Row([self.ip_input, self.ftp_port_input, self.sftp_port_input]),
                    ft.Row([
                        self.root_input
                    ]),
                    ft.Text("User Authentication & Security", weight="bold"),
                    ft.Row([self.user_input, self.pass_input, self.write_chk, self.ftps_chk]),
                    ft.Row([self.btn_ftp, self.btn_sftp]),
                    ft.Divider(),
                    ft.Text("Recent FTP Transfers", weight="bold"),
                    ft.Container(
                        content=ft.Column([self.transfers_col], scroll=ft.ScrollMode.AUTO),
                        height=150,
                        width=4000,
                        expand=True,
                        border=ft.Border(
                            top=ft.BorderSide(1, "#cccccc"),
                            right=ft.BorderSide(1, "#cccccc"),
                            bottom=ft.BorderSide(1, "#cccccc"),
                            left=ft.BorderSide(1, "#cccccc")
                        ),
                        border_radius=10,
                        padding=10
                    )
                ])
            )
        )

    def append_transfer(self, filename, ip, status):
        import datetime
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.transfers_col.controls.insert(0, ft.Text(f"[{now}] {ip} {status} '{filename}'"))
        if len(self.transfers_col.controls) > 50:
            self.transfers_col.controls.pop()
        self.page.update()

    def _update_auth(self, srv_name):
        srv = getattr(self.backend_runner, srv_name)
        srv.username = self.user_input.value
        srv.password = self.pass_input.value
        srv.allow_write = self.write_chk.value
        if srv_name == 'ftp_srv':
            srv.use_ftps = self.ftps_chk.value

    def toggle_ftp(self, e):
        self.ftp_running = not self.ftp_running
        if self.ftp_running:
            if isinstance(self.btn_ftp.content, ft.Text):
                self.btn_ftp.content.value = "Stop FTP / FTPS"
            else:
                self.btn_ftp.content = ft.Text("Stop FTP / FTPS")
            self.btn_ftp.style = ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=ft.Colors.ERROR)
            self._update_auth('ftp_srv')
            self.backend_runner.start_server('ftp_srv', self.ip_input.value, self.ftp_port_input.value, self.root_input.value)
        else:
            if isinstance(self.btn_ftp.content, ft.Text):
                self.btn_ftp.content.value = "Start FTP"
            else:
                self.btn_ftp.content = ft.Text("Start FTP")
            self.btn_ftp.style = ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=ft.Colors.PRIMARY)
            self.backend_runner.stop_server('ftp_srv')
        self.page.update()

    def toggle_sftp(self, e):
        self.sftp_running = not self.sftp_running
        if self.sftp_running:
            if isinstance(self.btn_sftp.content, ft.Text):
                self.btn_sftp.content.value = "Stop SFTP"
            else:
                self.btn_sftp.content = ft.Text("Stop SFTP")
            self.btn_sftp.style = ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=ft.Colors.ERROR)
            self._update_auth('sftp_srv')
            self.backend_runner.start_server('sftp_srv', self.ip_input.value, self.sftp_port_input.value, self.root_input.value)
        else:
            if isinstance(self.btn_sftp.content, ft.Text):
                self.btn_sftp.content.value = "Start SFTP"
            else:
                self.btn_sftp.content = ft.Text("Start SFTP")
            self.btn_sftp.style = ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=ft.Colors.PRIMARY)
            self.backend_runner.stop_server('sftp_srv')
        self.page.update()
