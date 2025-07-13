[app]
title = dicomlator
package.name = dicomlator
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1
requirements = python3==3.11.6,kivy==2.3.0,pydicom==2.4.3,numpy==1.26.4
orientation = portrait

[buildozer]
log_level = 2
warn_on_root = 1

[app.android]
android.api = 30
android.minapi = 21
android.ndk = 26b
android.sdk = 24
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,INTERNET
android.arch = arm64-v8a,armeabi-v7a
p4a.branch = master
android.allow_backup = True
android.adaptive_icon = True
android.gradle_dependencies = 'com.android.support:support-v4:28.0.0'

# Icon and splash
# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/splash.png
