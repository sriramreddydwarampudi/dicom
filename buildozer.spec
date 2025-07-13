[app]
title = dicomlator
package.name = dicomlator
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1
requirements = 
    python3,
    kivy==2.3.0,
    pydicom==2.4.3,
    numpy==1.26.4,
    matplotlib==3.8.3,
    pillow==10.2.0,
    setuptools,
    certifi,
    urllib3
orientation = portrait
osx.kivy_version = 2.3.0
android.p4a_dir = ./p4a_cache
android.allow_backup = True
android.arch = arm64-v8a

[buildozer]
log_level = 2
warn_on_root = 1

[app.android]
android.api = 30
android.minapi = 21
android.ndk = 25b
android.sdk = 24
android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE,INTERNET
android.gradle_dependencies =
android.env_vars = MPLBACKEND=agg

[app.android.entrypoint]
main = main:DicomViewerApp().run()

[app:source.exclude_patterns]
*.pyc,*.pyo,*.pyd,*.git,*.md,*.txt,*.bat,*.exe
tests/,examples/,docs/,__pycache__/
