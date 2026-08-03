[app]
title = ScrcpyLink
package.name = scrcpyheartbeat
package.domain = org.henry.scrcpy
source.dir = android
source.include_exts = py,png,jpg,kv,atlas
version = 268.03.6
requirements = python3,kivy==2.2.1,pyjnius
orientation = portrait
osx.python_version = 3
osx.kivy_version = 1.11.1
android.archs = arm64-v8a
android.add_src = src/java
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE,moe.shizuku.manager.permission.API_V23
android.meta_data = moe.shizuku.client.V3_SUPPORT=true,com.thedjchi.shizuku.client.V3_SUPPORT=true
android.api = 33
android.minapi = 21
android.ndk = 25b
p4a.branch = v2024.01.21
android.application = org.kivy.android.ScrcpyApplication

# App icon - use local icon in repo
icon.filename = icon.png

# Size optimizations - exclude unused directories and patterns
android.exclude_dirs = tests,__pycache__,.git,.github,docs,examples
android.exclude_patterns = *.pyc,*.pyo,*.pyd,*.so,*.dylib,*.dll,*.a,*.lib

# Conservative exclusions - only exclude truly unused large modules
android.exclude_modules = tkinter,test,unittest,doctest,pdb,profile,cProfile,lib2to3,distutils,venv,ensurepip

# Quick Settings Tile service
android.manifest = <service android:name="org.henry.scrcpy.ScrcpyTileService" android:label="Scrcpy Heartbeat" android:permission="android.permission.BIND_QUICK_SETTINGS_TILE" android:exported="true"><intent-filter><action android:name="android.service.quicksettings.action.QS_TILE" /></intent-filter></service>