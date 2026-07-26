[app]
title = ScrcpyLink
package.name = scrcpyheartbeat
package.domain = org.henry.scrcpy
source.dir = android
source.include_exts = py,png,jpg,kv,atlas
version = 4.26.7
requirements = python3,kivy,requests,pyjnius
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

# App icon - use local icon in repo
icon.filename = icon.png

# Size optimizations - exclude unused directories and patterns
android.exclude_dirs = tests,__pycache__,.git,.github,docs,examples
android.exclude_patterns = *.pyc,*.pyo,*.pyd,*.so,*.dylib,*.dll,*.a,*.lib

# Conservative exclusions - only exclude truly unused large modules
# DO NOT exclude: socket, threading, json, ssl, time, os, sys, requests, kivy
android.exclude_modules = \
    tkinter,tkinter.ttk,tkinter.tix,tkinter,\
    test,unittest,doctest,pdb,profile,cProfile,\
    lib2to3,distutils,venv,ensurepip,\
    csv,html,xml,xmlrpc,email,mailbox,mailcap,mimetypes,\
    ftplib,imaplib,nntplib,poplib,smtplib,telnetlib,\
    sqlite3,dbm,bz2,lzma,gzip,zipfile,tarfile,\
    fractions,decimal,numbers,statistics,\
    ctypes,_ctypes,_ctypes_test,\
    _ssl,_hashlib,_sha1,_sha2,_sha3,_md5,_blake2,_bisect,\
    _heapq,_random,_json,_csv,_pickle,_elementtree,_sqlite3,\
    _testbuffer,_testcapi,_testclinic,_testclinic_limited,\
    _testimportmultiple,_testinternalcapi,\
    aifc,antigravity,audioop,chunk,colorsys,imghdr,sndhdr,\
    ossaudiodev,spwd,grp,pwd,crypt,termios,tty,\
    resource,select,selectors,asyncio,asyncore,asynchat,\
    socketserver,http.server,http.client,http.cookiejar,\
    http.cookies,webbrowser,cgi,cgitb,\
    wsgiref,xml.etree,xml.dom,xml.sax,xml.parsers,xmlrpc,\
    plistlib,formatter,calendar,timeit,traceback,\
    trace,tracemalloc,faulthandler,inspect,linecache,\
    pdb,bdb,cmd,code,codeop,rlcompleter,readline,\
    curses,curses.ascii,curses.panel,curses.textpad,\
    locale,gettext,optparse,argparse,shlex,\
    string,stringprep,textwrap,unicodedata,reprlib,\
    difflib,struct,array,weakref,copy,copyreg,\
    operator,keyword,token,tokenize,tabnanny,pyclbr,\
    symbol,symtable,parser,compileall,py_compile,\
    importlib.abc,importlib.machinery,importlib.util,\
    importlib.metadata,importlib.resources,importlib.readers,\
    zipimport,zipapp,site,sysconfig,platform,posixpath,\
    glob,fnmatch,stat,filecmp,shutil,tempfile,fileinput,\
    aifc,audioop,sunau,wave,chunk,colorsys,imghdr,\
    sndhdr,ossaudiodev,spwd,grp,pwd,crypt,termios,tty,\
    resource,select,selectors,asyncio,asyncore,asynchat,\
    socketserver,http,urllib,xml,xmlrpc,html,\
    email,mailbox,mailcap,mimetypes,ftplib,imaplib,\
    nntplib,poplib,smtplib,telnetlib,sqlite3,dbm,\
    csv,configparser,ctypes,ctypes.util,ctypes.wintypes,\
    _ctypes_test,_ctypes,_ssl,_hashlib,_sha1,_sha2,_sha3,_md5,\
    _blake2,_bisect,_heapq,_random,_json,_csv,_pickle,\
    _elementtree,_sqlite3,_statistics,_struct,_sysconfigdata,\
    _testbuffer,_testcapi,_testclinic,_testclinic_limited,\
    _testimportmultiple,_testinternalcapi,_asyncio,\
    _codecs_cn,_codecs_hk,_codecs_iso2022,_codecs_jp,\
    _codecs_kr,_codecs_tw,_csv,_ctypes,_ctypes_test,\
    _decimal,_elementtree,_hashlib,_heapq,_hmac,\
    _interpchannels,_interpqueues,_interpreters,_json,\
    _lsprof,_md5,_multibytecodec,_pickle,_posixsubprocess,\
    _queue,_random,_sha1,_sha2,_sha3,_socket,_sqlite3,\
    _ssl,_statistics,_struct,_sysconfigdata,\
    _testbuffer,_testcapi,_testclinic,_testclinic_limited,\
    _testimportmultiple,_testinternalcapi

# Keep essential: os, sys, json, socket, threading, time, ssl, requests, kivy

# Quick Settings Tile service
android.manifest = <service android:name="org.henry.scrcpy.ScrcpyTileService" android:label="Scrcpy Heartbeat" android:permission="android.permission.BIND_QUICK_SETTINGS_TILE" android:exported="true"><intent-filter><action android:name="android.service.quicksettings.action.QS_TILE" /></intent-filter></service>