pyinstaller collect_device_classes.py --clean --icon=trellix.ico --noconfirm --version-file=collect_device_classes.rc
pyinstaller windows_filter_driver_investigator.py --clean --icon=trellix.ico --noconfirm --version-file=windows_filter_driver_investigator.rc

if not exist bin (mkdir bin) && (for /r ".\dist\" %%i in (*.exe) do xcopy "%%i" ".\bin\" /y)