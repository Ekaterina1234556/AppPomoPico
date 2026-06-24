[app]

# (str) Название приложения
title = Pomodoro Timer

# (str) Имя пакета
package.name = apppomodoro

# (str) Домен (замените на свой, например com.yourname)
package.domain = org.example

# (str) Главный файл
source.main_filename = main.py

# (str) Версия
version = 1.0.0

# (list) Расширения файлов для включения в сборку
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,otf,json,wav,mp3,ogg

# (list) Расширения для исключения
source.exclude_exts = spec,md,txt,log

# (list) Папки для исключения
source.exclude_dirs = tests,bin,.venv,__pycache__,.git,.github,.buildozer

# ============================================================
# ЗАВИСИМОСТИ (САМОЕ ВАЖНОЕ ДЛЯ POMODORO)
# ============================================================
# python3        - интерпретатор Python
# kivy           - графический фреймворк
# kivymd         - Material Design для Kivy
# pillow         - работа с изображениями
# plyer          - уведомления, вибрация, яркость
# android        - нативные Android API (уведомления, служба)
# pyjnius        - доступ к Java API Android
# certifi        - сертификаты для HTTPS (если нужно)
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,plyer,android,pyjnius,certifi

# (str) Иконка (раскомментируйте и укажите путь)
# icon.filename = %(source.dir)s/icon.png

# (str) Ориентация экрана
orientation = portrait

# (bool) Полноэкранный режим (0 = с статус-баром)
fullscreen = 0

# ============================================================
# РАЗРЕШЕНИЯ ANDROID (КРИТИЧНО ДЛЯ POMODORO!)
# ============================================================
# VIBRATE              - вибрация при завершении таймера
# WAKE_LOCK            - экран не гаснет во время работы таймера
# FOREGROUND_SERVICE   - работа таймера в фоне (служба)
# FOREGROUND_SERVICE_SPECIAL_USE - для Android 14+ (API 34)
# POST_NOTIFICATIONS   - отправка уведомлений (Android 13+)
# RECEIVE_BOOT_COMPLETED - автозапуск службы после перезагрузки
# SCHEDULE_EXACT_ALARM - точные таймеры (Android 12+)
# USE_EXACT_ALARM      - альтернатива для точных будильников
# ACCESS_NOTIFICATION_POLICY - управление режимом "Не беспокоить"
android.permissions = VIBRATE,WAKE_LOCK,FOREGROUND_SERVICE,FOREGROUND_SERVICE_SPECIAL_USE,POST_NOTIFICATIONS,RECEIVE_BOOT_COMPLETED,SCHEDULE_EXACT_ALARM,USE_EXACT_ALARM,ACCESS_NOTIFICATION_POLICY

# ============================================================
# СЛУЖБА В ФОНЕ (чтобы таймер работал при свёрнутом приложении)
# ============================================================
# Формат: ИмяСлужбы:путь_к_файлу:режим
# foreground - служба с приоритетом (не убивается системой)
android.services = PomodoroService:service.py:foreground

# ============================================================
# ВЕРСИИ ANDROID SDK/NDK
# ============================================================
# Target API (современный, но стабильный)
android.api = 33

# Минимальная версия Android (Android 7.0+)
android.minapi = 24

# NDK версия (совместима с Python 3.11)
android.ndk = 25b

# ============================================================
# АРХИТЕКТУРЫ (для современных устройств)
# ============================================================
android.archs = arm64-v8a, armeabi-v7a

# ============================================================
# НАСТРОЙКИ P4A (Python-for-Android)
# ============================================================
p4a.branch = master
p4a.bootstrap = sdl2

# Точка входа Android
android.entrypoint = org.kivy.android.PythonActivity

# Код версии (увеличивайте с каждым релизом)
android.numeric_version = 1

# Фильтры logcat для отладки
android.logcat_filters = *:S python:D

# Дополнительные аргументы для p4a
p4a.extra_args = --ignore-setup-py-requirements

# ============================================================
# ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ
# ============================================================
# Пресет темы (без заголовка)
android.manifest.application_attrs = android:theme=@android:style/Theme.NoTitleBar

# Активность для уведомлений (раскомментируйте если нужна)
# android.add_src = 

# Gradle зависимости (если нужны дополнительные библиотеки)
# android.gradle_dependencies = androidx.core:core:1.9.0

[buildozer]

# Отключаем предупреждение о root (для GitHub Actions)
warn_on_root = 0

# Уровень логирования (2 = подробный)
log_level = 2

# 0 = не показывать логи сборки, 1 = показывать
# 2 = показывать всё (для отладки)
