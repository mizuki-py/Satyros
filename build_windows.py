import os
import shutil
import tempfile
import uuid
import zipfile

import sys
from pathlib import Path

# Flet / PyInstaller utilities
try:
    import pefile
    from packaging import version
    from PyInstaller.utils.win32 import versioninfo
    from PyInstaller.utils.win32.icon import IconFile, normalize_icon_type
    from PyInstaller.compat import win32api
    from flet_desktop import ensure_client_cached
except ImportError as e:
    print(f"Required module not found: {e}")
    print("Please ensure you have flet, pyinstaller, and pefile installed.")
    sys.exit(1)

def update_flet_view_icon(exe_path, icon_path):
    print(f"Updating Flet View icon: {exe_path} with {icon_path}")
    RT_ICON = 3
    RT_GROUP_ICON = 14

    normalized_icon_path = normalize_icon_type(icon_path, ("exe", "ico"), "ico", os.getcwd())
    icon = IconFile(normalized_icon_path)
    print(f"Copying icons from {normalized_icon_path}")

    hdst = win32api.BeginUpdateResource(exe_path, 0)
    
    # Write to BOTH Language 0 (Neutral) and 1033 (English) to ensure no default logos remain
    for lang in [0, 1033]:
        i = 101
        data = icon.grp_icon_dir()
        data = data + icon.grp_icondir_entries(1)
        win32api.UpdateResource(hdst, RT_GROUP_ICON, i, data, lang)
        
        iconid = 1
        for img_data in icon.images:
            win32api.UpdateResource(hdst, RT_ICON, iconid, img_data, lang)
            iconid += 1

    win32api.EndUpdateResource(hdst, 0)


def update_flet_view_version_info(
    exe_path, product_name, file_description, product_version, file_version, company_name, copyright
) -> str:
    print(f"Updating Flet View version info: {exe_path}")
    
    if versioninfo.read_version_info_from_executable:
        vs = versioninfo.read_version_info_from_executable(exe_path)
    else:
        vs = versioninfo.decode(exe_path)

    if file_version:
        pv = version.parse(file_version)
        filevers = (pv.major, pv.minor, pv.micro, 0)
        vs.ffi.fileVersionMS = (filevers[0] << 16) | (filevers[1] & 0xFFFF)
        vs.ffi.fileVersionLS = (filevers[2] << 16) | (filevers[3] & 0xFFFF)

    for k in vs.kids[0].kids[0].kids:
        if k.name == "ProductName":
            k.val = product_name or ""
        elif k.name == "FileDescription":
            k.val = file_description or ""
        elif k.name == "ProductVersion":
            k.val = product_version or ""
        elif k.name == "FileVersion" and file_version:
            k.val = file_version or ""
        elif k.name == "CompanyName":
            k.val = company_name or ""
        elif k.name == "LegalCopyright":
            k.val = copyright or ""

    version_info_path = str(Path(tempfile.gettempdir()).joinpath(str(uuid.uuid4())))
    with open(version_info_path, "w", encoding="utf-8") as f:
        f.write(str(vs))

    pe = pefile.PE(exe_path, fast_load=True)
    overlay_before = pe.get_overlay()
    pe.close()

    hdst = win32api.BeginUpdateResource(exe_path, 0)
    win32api.UpdateResource(hdst, pefile.RESOURCE_TYPE["RT_VERSION"], 1, vs.toRaw(), 1033)
    win32api.EndUpdateResource(hdst, 0)

    if overlay_before:
        pe = pefile.PE(exe_path, fast_load=True)
        overlay_after = pe.get_overlay()
        pe.close()
        if not overlay_after:
            with open(exe_path, "ab") as exef:
                exef.write(overlay_before)

    return version_info_path


def compress_flet_client_dir(bin_dir, zip_filename):
    zip_path = os.path.join(bin_dir, zip_filename)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(os.path.join(bin_dir, "flet")):
            for file in files:
                file_path = os.path.join(root, file)
                # Preserve the 'flet' directory prefix in the zip!
                zipf.write(file_path, os.path.relpath(file_path, bin_dir))


def main():
    print("Initializing custom Satyros Windows build...")
    
    # 1. Fetch default Flet client
    cache_dir = ensure_client_cached()
    if not cache_dir or not cache_dir.exists():
        print("Failed to locate Flet client cache.")
        sys.exit(1)
        
    # 2. Create an isolated temp directory for our custom engine
    temp_bin_dir = Path(tempfile.gettempdir()).joinpath(str(uuid.uuid4()))
    flet_dest = temp_bin_dir.joinpath("flet")
    shutil.copytree(cache_dir.joinpath("flet"), flet_dest)
    
    exe_path = str(flet_dest.joinpath("flet.exe"))
    
    # 3. Patch the isolated flet.exe
    icon_path = os.path.abspath("icon.ico")
    if os.path.exists(icon_path):
        update_flet_view_icon(exe_path, icon_path)
    else:
        print("WARNING: icon.ico not found, skipping icon update.")
        
    version_file = update_flet_view_version_info(
        exe_path=exe_path,
        product_name="Satyros",
        file_description="Satyros",
        product_version="0.3.2",
        file_version="0.3.2.0",
        company_name="Satyros",
        copyright="2026 Satyros"
    )
    
    # 4. Repackage into flet-windows.zip
    compress_flet_client_dir(str(temp_bin_dir), "flet-windows.zip")
    
    # Remove the uncompressed flet.exe to save space, pyinstaller hook only needs the zip
    shutil.rmtree(flet_dest, ignore_errors=True)
    
    # 5. Set environment variable so Flet's PyInstaller hook finds it
    os.environ["FLET_VIEW_PATH"] = str(temp_bin_dir)
    print(f"Set FLET_VIEW_PATH to {temp_bin_dir}")
    
    # 6. Run PyInstaller
    # We call PyInstaller directly with our custom arguments
    pyinstaller_args = [
        "main.py",
        "--clean",
        "--noconfirm",
        "--noconsole",
        "--icon", "icon.ico",
        "--name", "Satyros",
        "--distpath", "dist",
        "--add-data", "assets:assets",
        "--onefile",
        "--version-file", version_file
    ]
    
    import PyInstaller.__main__
    print("Running PyInstaller...")
    PyInstaller.__main__.run(pyinstaller_args)
    
    # Cleanup
    print(f"Cleaning up temp directory: {temp_bin_dir}")
    shutil.rmtree(temp_bin_dir, ignore_errors=True)
    
    print("Build completed successfully! You can find the executable in the 'dist' folder.")

if __name__ == "__main__":
    main()
