import flet as ft

class VersionTab:
    def __init__(self, page: ft.Page):
        self.page = page

    def build(self):
        title = ft.Text("Satyros", size=32, weight="bold", color=ft.Colors.PRIMARY if hasattr(ft.Colors, 'PRIMARY') else "#4285F4")
        subtitle = ft.Text("Version 0.2.0", size=18, color="#555555")
        
        libraries = ft.Column([
            ft.Text("• Python 3.14.5 (Core Interpreter)"),
            ft.Text("• flet 0.85.1 (GUI Framework)"),
            ft.Text("• py3tftp 1.3.0 (TFTP Server)"),
            ft.Text("• pyftpdlib 2.2.0 (FTP/FTPS Server)"),
            ft.Text("• paramiko 5.0.0 (SFTP Server)"),
            ft.Text("• pyOpenSSL 26.2.0 (TLS Certificate Generation)"),
            ft.Text("• pysnmp 7.1.27 (SNMP Manager & Trap Receiver)")
        ])
        
        lib_section = ft.Container(
            content=ft.Column([
                ft.Text("Libraries Used", size=20, weight="bold"),
                ft.Container(height=10),
                libraries
            ]),
            padding=20,
            border=ft.Border(
                top=ft.BorderSide(1, "#cccccc"),
                right=ft.BorderSide(1, "#cccccc"),
                bottom=ft.BorderSide(1, "#cccccc"),
                left=ft.BorderSide(1, "#cccccc")
            ),
            border_radius=10,
            margin=ft.Margin(top=20, right=0, bottom=20, left=0)
        )
        
        credit = ft.Text("Made by Antigravity", size=16, weight="bold")

        return ft.Card(
            content=ft.Container(
                padding=40,
                content=ft.Column([
                    title,
                    subtitle,
                    lib_section,
                    credit
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
            ),
            expand=True
        )
