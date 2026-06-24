from jnius import autoclass
from android import mActivity
from time import sleep

# Простая служба-таймер
PythonService = autoclass('org.kivy.android.PythonService')
PythonService.mService.setAutoRestartService(True)

while True:
    sleep(1)
    # Здесь логика таймера в фоне
