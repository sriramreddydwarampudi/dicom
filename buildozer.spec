[app]
title = dicomlator
package.name = dicomlator
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0.0
version.code = 1
orientation = portrait
fullscreen = 0

# Set the entry point of your app
entrypoint = main.py

requirements = python3,kivy,pydicom,numpy,matplotlib

# Include icon if needed
# icon.filename = %(source.dir)/icon.png

# Permissions needed for accessing files
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# Make sure the app has access to external file systems
android.private_storage = False

# Don't use AndroidX unless needed
android.enable_androidx = False

# Optional: enforce minimum API level
android.minapi = 21
android.api = 33
android.ndk = 25b
android.gradle_dependencies = 

# (str) Presplash of the application
# presplash.filename = %(source.dir)/presplash.png

# Hide the title bar
android.hide_titlebar = 0

[buildozer]
log_level = 2
warn_on_root = 1
require_android = True
