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
        
        self.btn_toggle = ft.ElevatedButton(
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

        self.btn_export = ft.ElevatedButton(content="Export CSV", on_click=handle_export)

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

        self.trap_list = ft.ListView(expand=True, spacing=10)

        trap_card = ft.Card(
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Text("Trap Receiver", size=20, weight="bold"),
                    trap_controls,
                    export_controls,
                    trap_v3_controls,
                    ft.Container(
                        content=self.trap_list,
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

        self.btn_get = ft.ElevatedButton(content="Get", on_click=self.do_get)
        self.btn_walk = ft.ElevatedButton(content="Walk", on_click=self.do_walk)

        mgr_controls = ft.Row([
            self.mgr_ip_input, self.mgr_port_input, self.mgr_oid_input, self.mgr_community, self.mgr_version,
            self.btn_get, self.btn_walk
        ])
        mgr_v3_controls = ft.Row([
            self.mgr_v3_user, self.mgr_v3_auth, self.mgr_v3_priv
        ])

        self.mgr_list = ft.ListView(expand=True, spacing=10)

        mgr_card = ft.Card(
            content=ft.Container(
                padding=20,
                content=ft.Column([
                    ft.Text("SNMP Manager", size=20, weight="bold"),
                    mgr_controls,
                    mgr_v3_controls,
                    ft.Container(
                        content=self.mgr_list,
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
        for i, t in enumerate(self.traps):
            bg_color = ft.Colors.SURFACE_CONTAINER if i % 2 == 0 else ft.Colors.TRANSPARENT
            self.trap_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"Time: {t['time']} | Source IP: {t['ip']}", weight="bold", color=ft.Colors.BLUE_300),
                        ft.Text(t['msg'], selectable=True)
                    ]),
                    padding=10,
                    bgcolor=bg_color,
                    border=ft.Border(bottom=ft.BorderSide(1, "#444444")),
                    border_radius=5
                )
            )
            
        return res

    def append_trap(self, ip, msg):
        msg = msg.replace('\r', '').replace('\n', ' ').strip()
        now = datetime.datetime.now().strftime("%H:%M:%S")
        self.traps.append({"time": now, "ip": ip, "msg": msg})
        
        bg_color = ft.Colors.SURFACE_CONTAINER if len(self.traps) % 2 != 0 else ft.Colors.TRANSPARENT
        self.trap_list.controls.append(
            ft.Container(
                content=ft.Column([
                    ft.Text(f"Time: {now} | Source IP: {ip}", weight="bold", color=ft.Colors.BLUE_300),
                    ft.Text(msg, selectable=True)
                ]),
                padding=10,
                bgcolor=bg_color,
                border=ft.Border(bottom=ft.BorderSide(1, "#444444")),
                border_radius=5
            )
        )
        
        if len(self.trap_list.controls) > 100:
            self.trap_list.controls.pop(0)
            
        self.page.update()

    def toggle_server(self, e):
        self.running = not self.running
        if self.running:
            if isinstance(self.btn_toggle.content, ft.Text):
                self.btn_toggle.content.value = "Stop Receiver"
            else:
                self.btn_toggle.content = ft.Text("Stop Receiver")
            self.btn_toggle.style = ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=ft.Colors.ERROR)
            kwargs = {}
            if self.trap_v3_user.value:
                kwargs['v3_user'] = self.trap_v3_user.value
            if self.trap_v3_auth.value:
                kwargs['v3_auth'] = self.trap_v3_auth.value
            if self.trap_v3_priv.value:
                kwargs['v3_priv'] = self.trap_v3_priv.value
            self.backend_runner.start_server('snmp_srv', self.trap_ip_input.value, self.trap_port_input.value, **kwargs)
        else:
            if isinstance(self.btn_toggle.content, ft.Text):
                self.btn_toggle.content.value = "Start Receiver"
            else:
                self.btn_toggle.content = ft.Text("Start Receiver")
            self.btn_toggle.style = ft.ButtonStyle(color=ft.Colors.ON_PRIMARY, bgcolor=ft.Colors.PRIMARY)
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
        self.mgr_list.controls.clear()
        self.page.update()
        try:
            kwargs = self._get_mgr_args()
            future = asyncio.run_coroutine_threadsafe(self.client.get(**kwargs), self.backend_runner.loop)
            res = future.result(timeout=5)
            self._display_mgr_result(res)
        except Exception as ex:
            self._display_mgr_result({"error": str(ex)})

    def do_walk(self, e):
        self.mgr_list.controls.clear()
        self.page.update()
        try:
            kwargs = self._get_mgr_args()
            future = asyncio.run_coroutine_threadsafe(self.client.walk(**kwargs), self.backend_runner.loop)
            res = future.result(timeout=10)
            self._display_mgr_result(res)
        except Exception as ex:
            self._display_mgr_result({"error": str(ex)})

    def _display_mgr_result(self, res):
        now = datetime.datetime.now().strftime("%H:%M:%S")
        target_ip = self.mgr_ip_input.value
        
        if "error" in res:
            self.mgr_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Text(f"Time: {now} | Target IP: {target_ip}", weight="bold", color=ft.Colors.ERROR),
                        ft.Text(f"Error: {res['error']}", selectable=True, color=ft.Colors.ERROR)
                    ]),
                    padding=10,
                    bgcolor=ft.Colors.SURFACE_CONTAINER,
                    border=ft.Border(bottom=ft.BorderSide(1, "#444444")),
                    border_radius=5
                )
            )
        else:
            for i, r in enumerate(res.get("result", [])):
                bg_color = ft.Colors.SURFACE_CONTAINER if i % 2 == 0 else ft.Colors.TRANSPARENT
                self.mgr_list.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"Time: {now} | Target IP: {target_ip}", weight="bold", color=ft.Colors.BLUE_300),
                            ft.Text(r, selectable=True)
                        ]),
                        padding=10,
                        bgcolor=bg_color,
                        border=ft.Border(bottom=ft.BorderSide(1, "#444444")),
                        border_radius=5
                    )
                )
        self.page.update()
