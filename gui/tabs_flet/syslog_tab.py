import flet as ft
from core.config import get_local_ips
import datetime
import os

class SyslogTab:
    def __init__(self, page: ft.Page, backend_runner):
        self.page = page
        self.backend_runner = backend_runner
        self.running = False
        self.logs = []
        self.search_filter = ""

    def build(self):
        ips = get_local_ips()
        self.ip_input = ft.Dropdown(label="Listen IP", value="0.0.0.0", options=[ft.dropdown.Option(ip) for ip in ips], expand=True)
        self.port_input = ft.TextField(label="Port", value="514", width=100)
        
        self.btn_toggle = ft.Button(
            content=ft.Text("Start Server"),
            on_click=self.toggle_server,
            style=ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=ft.Colors.PRIMARY)
        )
        
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'syslog_export.txt')
        self.export_path = ft.TextField(label="Export Path", value=desktop_path, expand=True)
        
        def handle_export(e):
            path = self.export_path.value
            if not path:
                return
            try:
                with open(path, 'w', encoding='utf-8') as f:
                    for row in self.logs:
                        f.write(f"{row['time']} | {row['ip']} | Sev: {row['sev']} | {row['msg']}\n")
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Saved to {path}"), open=True)
                self.page.update()
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Save failed: {ex}"), open=True)
                self.page.update()

        self.btn_export = ft.Button(content=ft.Text("Export TXT"), on_click=handle_export)

        def on_search(e):
            self.search_filter = e.control.value.lower()
            self._render_table()
            
        self.search_input = ft.TextField(
            label="Search Logs", 
            on_change=on_search,
            expand=True,
            prefix_icon=ft.Icons.SEARCH if hasattr(ft.Icons, 'SEARCH') else None
        )

        self.log_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Time")),
                ft.DataColumn(ft.Text("Source IP")),
                ft.DataColumn(ft.Text("Severity")),
                ft.DataColumn(ft.Text("Message")),
            ],
            rows=[]
        )

        controls = ft.Card(
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Text("Syslog Server Settings", size=20, weight="bold"),
                    ft.Row([self.ip_input, self.port_input, self.btn_toggle]),
                    ft.Row([self.export_path, self.btn_export]),
                    ft.Row([self.search_input])
                ])
            )
        )

        log_view = ft.Container(
            content=ft.Column([self.log_table], scroll=ft.ScrollMode.AUTO),
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

        res = ft.Column([controls, log_view], expand=True)
        self._render_table()
        return res

    def _render_table(self):
        self.log_table.rows.clear()
        
        # Limit logs to latest 100 for performance
        logs_to_show = self.logs[-100:]
        
        for row in logs_to_show:
            if self.search_filter and self.search_filter not in row['msg'].lower() and self.search_filter not in row['ip']:
                continue
                
            color = None
            if row['sev'] <= 2: # Emergency, Alert, Critical
                color = ft.Colors.RED if hasattr(ft.Colors, 'RED') else "red"
            elif row['sev'] == 4: # Warning
                color = ft.Colors.YELLOW if hasattr(ft.Colors, 'YELLOW') else "yellow"
            elif row['sev'] == 6: # Info
                color = ft.Colors.WHITE if hasattr(ft.Colors, 'WHITE') else "white"
                
            cells = [
                ft.DataCell(ft.Text(row['time'])),
                ft.DataCell(ft.Text(row['ip'])),
                ft.DataCell(ft.Text(str(row['sev']))),
                ft.DataCell(ft.Text(row['msg'])),
            ]
            self.log_table.rows.append(ft.DataRow(cells=cells, color=color))
            
        self.page.update()

    def append_log(self, ip, msg, severity):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.logs.append({"time": now, "ip": ip, "sev": severity, "msg": msg})
        
        if len(self.logs) > 1000: # Keep maximum 1000 logs in memory
            self.logs.pop(0)
            
        self._render_table()

    def toggle_server(self, e):
        self.running = not self.running
        if self.running:
            self.btn_toggle.content = ft.Text("Stop Server")
            self.btn_toggle.style = ft.ButtonStyle(bgcolor=ft.Colors.ERROR)
            self.backend_runner.start_server('syslog_srv', self.ip_input.value, self.port_input.value)
        else:
            self.btn_toggle.content = ft.Text("Start Server")
            self.btn_toggle.style = ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY)
            self.backend_runner.stop_server('syslog_srv')
        self.page.update()
