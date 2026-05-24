import flet as ft
from core.config import BASE_DIR
import os

def main(page: ft.Page, backend_runner, log_queue):
    page.title = "Satyros"
    page.window.icon = "app_icon.png"
    page.window_width = 1000
    page.window_height = 800
    page.theme_mode = ft.ThemeMode.LIGHT
    
    # Modern theme colors inspired by Google
    page.theme = ft.Theme(
        color_scheme_seed="#4285F4",
        use_material3=True,
    )
    page.padding = 0

    # Components
    from gui.tabs_flet.tftp_tab import TFTPTab
    from gui.tabs_flet.ftp_tab import FTPTab
    from gui.tabs_flet.syslog_tab import SyslogTab
    from gui.tabs_flet.snmp_tab import SNMPTab
    from gui.tabs_flet.version_tab import VersionTab

    tftp_tab = TFTPTab(page, backend_runner)
    ftp_tab = FTPTab(page, backend_runner)
    syslog_tab = SyslogTab(page, backend_runner)
    snmp_tab = SNMPTab(page, backend_runner)
    version_tab = VersionTab(page)

    tftp_content = tftp_tab.build()
    ftp_content = ftp_tab.build()
    syslog_content = syslog_tab.build()
    snmp_content = snmp_tab.build()
    version_content = version_tab.build()

    content_area = ft.Container(
        content=tftp_content,
        expand=True,
        padding=20,
        bgcolor="#f4f6f8",
        border_radius=ft.BorderRadius(top_left=20, bottom_left=20, top_right=0, bottom_right=0),
    )

    def change_tab(e):
        idx = e.control.selected_index
        if idx == 0:
            content_area.content = tftp_content
        elif idx == 1:
            content_area.content = ftp_content
        elif idx == 2:
            content_area.content = syslog_content
        elif idx == 3:
            content_area.content = snmp_content
        elif idx == 4:
            content_area.content = version_content
        page.update()

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icon(ft.Icons.FOLDER, color=ft.Colors.GREEN_500),
                label="TFTP",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icon(ft.Icons.FOLDER, color=ft.Colors.BLUE_500),
                label="FTP",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icon(ft.Icons.ARTICLE, color=ft.Colors.ORANGE_500),
                label="Syslog",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icon(ft.Icons.ARTICLE, color=ft.Colors.PURPLE_500),
                label="SNMP",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icon(ft.Icons.INFO, color=ft.Colors.GREY_500),
                label="Version",
            ),
        ],
        on_change=change_tab,
    )

    # Queue processing loop
    def check_queue():
        while True:
            import queue
            try:
                msg = log_queue.get_nowait()
                if msg["type"] == "syslog":
                    syslog_tab.append_log(msg["ip"], msg["message"], msg.get("severity", 6))
                elif msg["type"] == "snmp":
                    snmp_tab.append_trap(msg["ip"], msg["message"])
                elif msg["type"] == "tftp":
                    tftp_tab.update_progress(msg["filename"], msg["ip"], msg["bytes"])
                elif msg["type"] == "ftp":
                    ftp_tab.append_transfer(msg["filename"], msg["ip"], msg["status"])
                elif msg["type"] == "error":
                    page.snack_bar = ft.SnackBar(ft.Text(msg["message"], color=ft.Colors.ERROR), open=True)
                    page.update()
            except queue.Empty:
                break
                
    import threading
    import time
    def run_queue_checker():
        while True:
            check_queue()
            time.sleep(0.1)

    threading.Thread(target=run_queue_checker, daemon=True).start()

    page.add(
        ft.Row(
            [
                rail,
                ft.VerticalDivider(width=1),
                content_area,
            ],
            expand=True,
            spacing=0,
        )
    )

from core.config import BASE_DIR, APP_DIR
import os

def start_flet_app(backend_runner, log_queue):
    assets_path = os.path.join(APP_DIR, "assets")
    ft.app(target=lambda page: main(page, backend_runner, log_queue), assets_dir=assets_path)
