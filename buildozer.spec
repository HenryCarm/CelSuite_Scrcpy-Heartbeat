[app]
title = ScrcpyLink
package.name = scrcpyheartbeat
package.domain = org.henry.scrcpy
source.dir = android
source.include_exts = py,png,jpg,kv,atlas
version = 26.08.04
android.numeric_version = 260804
requirements = python3,kivy==2.2.1,pyjnius
orientation = portrait
osx.python_version = 3
osx.kivy_version = 1.11.1
android.archs = arm64-v8a

android.gradle_dependencies = "dev.rikka.shizuku:api:13.1.5", "dev.rikka.shizuku:provider:13.1.5"
android.enable_androidx = True
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,MANAGE_EXTERNAL_STORAGE,moe.shizuku.manager.permission.API_V23
android.meta_data = moe.shizuku.client.V3_SUPPORT=true,com.thedjchi.shizuku.client.V3_SUPPORT=true
android.api = 33
android.minapi = 21
android.ndk = 25b
p4a.branch = master
android.accept_sdk_license = True
android.application = org.kivy.android.ScrcpyApplication

# App icon - use local icon in repo
icon.filename = icon.png

# Size optimizations - exclude unused directories and patterns
android.exclude_dirs = tests,__pycache__,.git,.github,docs,examples
android.exclude_patterns = *.pyc,*.pyo,*.pyd,*.so,*.dylib,*.dll,*.a,*.lib

# Conservative exclusions - only exclude truly unused large modules
android.exclude_modules = tkinter,test,unittest,doctest,pdb,profile,cProfile,lib2to3,distutils,venv,ensurepip
