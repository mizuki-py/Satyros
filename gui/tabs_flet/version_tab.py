import flet as ft

class VersionTab:
    def __init__(self, page: ft.Page):
        self.page = page

    def build(self):
        title = ft.Text("Satyros", size=32, weight="bold", color=ft.Colors.PRIMARY if hasattr(ft.Colors, 'PRIMARY') else "#4285F4")
        subtitle = ft.Text("Version 0.3.2", size=18, color="#555555")
        
        import sys
        
        def get_ver(module_name, attr='__version__'):
            try:
                mod = __import__(module_name)
                return getattr(mod, attr, 'Unknown')
            except ImportError:
                return 'Not Installed'
                
        py_ver = sys.version.split()[0]
        flet_ver = get_ver('flet')
        py3tftp_ver = get_ver('py3tftp')
        try:
            import pyftpdlib
            pyftpdlib_ver = getattr(pyftpdlib, '__ver__', getattr(pyftpdlib, '__version__', 'Unknown'))
        except ImportError:
            pyftpdlib_ver = 'Not Installed'
        paramiko_ver = get_ver('paramiko')
        openssl_ver = get_ver('OpenSSL')
        pysnmp_ver = get_ver('pysnmp')
        
        libraries = ft.Column([
            ft.Text(f"• Python {py_ver} (Core Interpreter)"),
            ft.Text(f"• flet {flet_ver} (GUI Framework)"),
            ft.Text(f"• py3tftp {py3tftp_ver} (TFTP Server)"),
            ft.Text(f"• pyftpdlib {pyftpdlib_ver} (FTP/FTPS Server)"),
            ft.Text(f"• paramiko {paramiko_ver} (SFTP Server)"),
            ft.Text(f"• pyOpenSSL {openssl_ver} (TLS Certificate Generation)"),
            ft.Text(f"• pysnmp {pysnmp_ver} (SNMP Manager & Trap Receiver)")
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
