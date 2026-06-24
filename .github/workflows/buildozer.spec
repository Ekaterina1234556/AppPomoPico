[app]
title = AppPomodoro
package.name = apppomodoro
package.domain = org.pomodoro
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,sqlite3,wav,txt
version = 1.0.0

# ВАЖНО: НЕ указывайте psycopg2!
requirements = python3,kivy==2.3.0,pg8000,pillow,sqlite3,requests,certifi,urllib3,idna,charset-normalizer

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE,WAKE_LOCK,VIBRATE,ACCESS_NETWORK_STATE

android.api = 33
android.minapi = 21
android.ndk_api = 21
android.archs = arm64-v8a, armeabi-v7a

android.allow_backup = True

log_level = 2
warn_on_root = 0

[buildozer]
log_level = 2
warn_on_root = 0