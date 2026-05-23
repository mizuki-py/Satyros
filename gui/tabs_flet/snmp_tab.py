import flet as ft
from core.config import get_local_ips
import datetime
import os
import asyncio
from backend.snmp_client import AsyncSNMPClient

class SNMPTab:
    def __init__(self, page: ft.Page, backend_runner):
        self.page = page
        self.backend_runner = backend_runner
        self.running = False
        self.traps = []
        self.client = AsyncSNMPClient()

    def build(self):
        ips = get_local_ips()
        
        # --- Trap Receiver Section ---
        self.trap_ip_input = ft.Dropdown(label="Listen IP", value="0.0.0.0", options=[ft.dropdown.Option(ip) for ip in ips], expand=True)
        self.trap_port_input = ft.TextField(label="Port", value="162", width=100)
        self.trap_v3_user = ft.TextField(label="v3 User", width=150)
        self.trap_v3_auth = ft.TextField(label="v3 Auth Key", width=150, password=True, can_reveal_password=True)
        self.trap_v3_priv = ft.TextField(label="v3 Priv Key", width=150, password=True, can_reveal_password=True)
        
        self.btn_toggle = ft.Button(
            content=ft.Text("Start Receiver"),
            on_click=self.toggle_server,
            style=ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=ft.Colors.PRIMARY)
        )

        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop', 'snmp_traps_export.csv')
        self.export_path = ft.TextField(label="Export Path", value=desktop_path, expand=True)

        def handle_export(e):
            path = self.export_path.value
            if not path:
                return
            import csv
            try:
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["Time", "Source IP", "Trap Content"])
                    for row in self.traps:
                        writer.writerow([row['time'], row['ip'], row['msg']])
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Saved to {path}"), open=True)
                self.page.update()
            except Exception as ex:
                self.page.snack_bar = ft.SnackBar(ft.Text(f"Save failed: {ex}"), open=True)
                self.page.update()

        self.btn_export = ft.Button(content=ft.Text("Export CSV"), on_click=handle_export)

        trap_controls = ft.Row([
            self.trap_ip_input, self.trap_port_input, 
            self.btn_toggle
        ])
        export_controls = ft.Row([
            self.export_path, self.btn_export
        ])
        trap_v3_controls = ft.Row([
            self.trap_v3_user, self.trap_v3_auth, self.trap_v3_priv
        ])

        self.trap_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Time")),
                ft.DataColumn(ft.Text("Source IP")),
                ft.DataColumn(ft.Text("Trap Content")),
            ],
            rows=[]
        )

        trap_card = ft.Card(
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Text("Trap Receiver", size=20, weight="bold"),
                    trap_controls,
                    export_controls,
                    trap_v3_controls,
                    ft.Container(
                        content=ft.Column([self.trap_table], scroll=ft.ScrollMode.AUTO),
                        height=200,
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

        # --- SNMP Manager Section ---
        self.mgr_ip_input = ft.TextField(label="Target IP", value="127.0.0.1", expand=True)
        self.mgr_port_input = ft.TextField(label="Port", value="161", width=100)
        self.mgr_oid_input = ft.TextField(label="OID", value="1.3.6.1.2.1.1.1.0", expand=True)
        self.mgr_community = ft.TextField(label="Community", value="public", width=150)
        self.mgr_version = ft.Dropdown(label="Version", value="2", options=[ft.dropdown.Option("1"), ft.dropdown.Option("2"), ft.dropdown.Option("3")], width=100)
        self.mgr_v3_user = ft.TextField(label="v3 User", width=150)
        self.mgr_v3_auth = ft.TextField(label="v3 Auth Key", width=150, password=True, can_reveal_password=True)
        self.mgr_v3_priv = ft.TextField(label="v3 Priv Key", width=150, password=True, can_reveal_password=True)

        self.btn_get = ft.Button(content=ft.Text("Get"), on_click=self.do_get)
        self.btn_walk = ft.Button(content=ft.Text("Walk"), on_click=self.do_walk)

        mgr_controls = ft.Row([
            self.mgr_ip_input, self.mgr_port_input, self.mgr_oid_input, self.mgr_community, self.mgr_version,
            self.btn_get, self.btn_walk
        ])
        mgr_v3_controls = ft.Row([
            self.mgr_v3_user, self.mgr_v3_auth, self.mgr_v3_priv
        ])

        self.mgr_results_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Result")),
            ],
            rows=[]
        )

        mgr_card = ft.Card(
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Text("SNMP Manager", size=20, weight="bold"),
                    mgr_controls,
                    mgr_v3_controls,
                    ft.Container(
                        content=ft.Column([self.mgr_results_table], scroll=ft.ScrollMode.AUTO),
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
            ),
            expand=True
        )

        res = ft.Column([trap_card, mgr_card], expand=True)
        
        # Restore traps on rebuild
        for t in self.traps:
            self.trap_table.rows.append(
                ft.DataRow(cells=[
                    ft.DataCell(ft.Text(t['time'])),
                    ft.DataCell(ft.Text(t['ip'])),
                    ft.DataCell(ft.Text(t['msg'])),
                ])
            )
            
        return res

    def append_trap(self, ip, msg):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.traps.append({"time": now, "ip": ip, "msg": msg})
        
        self.trap_table.rows.append(
            ft.DataRow(cells=[
                ft.DataCell(ft.Text(now)),
                ft.DataCell(ft.Text(ip)),
                ft.DataCell(ft.Text(msg)),
            ])
        )
        
        if len(self.trap_table.rows) > 100:
            self.trap_table.rows.pop(0)
            
        self.page.update()

    def toggle_server(self, e):
        self.running = not self.running
        if self.running:
            self.btn_toggle.content = ft.Text("Stop Receiver")
            self.btn_toggle.style = ft.ButtonStyle(bgcolor=ft.Colors.ERROR)
            kwargs = {}
            if self.trap_v3_user.value:
                kwargs['v3_user'] = self.trap_v3_user.value
            if self.trap_v3_auth.value:
                kwargs['v3_auth'] = self.trap_v3_auth.value
            if self.trap_v3_priv.value:
                kwargs['v3_priv'] = self.trap_v3_priv.value
            self.backend_runner.start_server('snmp_srv', self.trap_ip_input.value, self.trap_port_input.value, **kwargs)
        else:
            self.btn_toggle.content = ft.Text("Start Receiver")
            self.btn_toggle.style = ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY)
            self.backend_runner.stop_server('snmp_srv')
        self.page.update()

    def _get_mgr_args(self):
        kwargs = {
            'target_ip': self.mgr_ip_input.value,
            'oid': self.mgr_oid_input.value,
            'port': int(self.mgr_port_input.value),
            'community': self.mgr_community.value,
            'version': int(self.mgr_version.value)
        }
        if self.mgr_version.value == "3":
            if self.mgr_v3_user.value:
                kwargs['v3_user'] = self.mgr_v3_user.value
            if self.mgr_v3_auth.value:
                kwargs['v3_auth'] = self.mgr_v3_auth.value
            if self.mgr_v3_priv.value:
                kwargs['v3_priv'] = self.mgr_v3_priv.value
        return kwargs

    def do_get(self, e):
        self.mgr_results_table.rows.clear()
        self.page.update()
        try:
            kwargs = self._get_mgr_args()
            future = asyncio.run_coroutine_threadsafe(self.client.get(**kwargs), self.backend_runner.loop)
            res = future.result(timeout=5)
            self._display_mgr_result(res)
        except Exception as ex:
            self._display_mgr_result({"error": str(ex)})

    def do_walk(self, e):
        self.mgr_results_table.rows.clear()
        self.page.update()
        try:
            kwargs = self._get_mgr_args()
            future = asyncio.run_coroutine_threadsafe(self.client.walk(**kwargs), self.backend_runner.loop)
            res = future.result(timeout=10)
            self._display_mgr_result(res)
        except Exception as ex:
            self._display_mgr_result({"error": str(ex)})

    def _display_mgr_result(self, res):
        if "error" in res:
            self.mgr_results_table.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(f"Error: {res['error']}", color=ft.Colors.ERROR))]))
        else:
            for r in res.get("result", []):
                self.mgr_results_table.rows.append(ft.DataRow(cells=[ft.DataCell(ft.Text(r))]))
        self.page.update()
