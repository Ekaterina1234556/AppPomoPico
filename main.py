from kivy.app import App
from kivy.lang import Builder
from kivy.event import EventDispatcher
from kivy.factory import Factory
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.popup import Popup
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.properties import (
    StringProperty, BooleanProperty, ObjectProperty,
    NumericProperty, ListProperty, DictProperty
)
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.graphics import Color, Line, Ellipse
from kivy.core.audio import SoundLoader
from datetime import datetime
import math, struct, wave, tempfile, os, json
import platform

import database as db_offline
import db_online as db_online


import os
import sys
import shutil

def get_resource_path(relative_path):
    """Возвращает абсолютный путь к ресурсу (для EXE и обычного запуска)."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def ensure_icons_available():
    """
    Копирует папку icons из временной папки PyInstaller 
    в текущую рабочую директорию, если её там нет.
    """
    if hasattr(sys, '_MEIPASS'):
        # Мы в упакованном EXE
        source_icons = os.path.join(sys._MEIPASS, 'icons')
        target_icons = os.path.join(os.path.abspath("."), 'icons')
        
        if os.path.exists(source_icons):
            try:
                if not os.path.exists(target_icons):
                    shutil.copytree(source_icons, target_icons)
                    print(f"Иконки скопированы в: {target_icons}")
                else:
                    # Проверяем, все ли файлы на месте
                    source_files = set(os.listdir(source_icons))
                    target_files = set(os.listdir(target_icons)) if os.path.exists(target_icons) else set()
                    missing = source_files - target_files
                    if missing:
                        for f in missing:
                            shutil.copy2(
                                os.path.join(source_icons, f),
                                os.path.join(target_icons, f)
                            )
                        print(f"Добавлено недостающих файлов: {len(missing)}")
            except Exception as e:
                print(f"Ошибка копирования иконок: {e}")

def get_resource_path(relative_path):
    """
    Возвращает абсолютный путь к ресурсу.
    Работает как при обычном запуске, так и в упакованном EXE.
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller создаёт временную папку _MEIPASS
        base_path = sys._MEIPASS
    else:
        # Обычный запуск через python main.py
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

CURRENT_MODE = "offline"
CURRENT_USER_ID = None
CURRENT_USERNAME = None
FIRST_OFFLINE_LAUNCH = True


def get_db():
    return db_online if CURRENT_MODE == "online" else db_offline


NOTE_FREQS = {
    "C4": 261.63, "C#4": 277.18, "D4": 293.66, "D#4": 311.13,
    "E4": 329.63, "F4": 349.23, "F#4": 369.99, "G4": 392.00,
    "G#4": 415.30, "A4": 440.00, "A#4": 466.16, "B4": 493.88,
    "C5": 523.25,
}
NOTE_NAMES = list(NOTE_FREQS.keys())


def generate_melody_wav(notes, bpm=120, total_steps=32):
    sample_rate = 44100
    step_dur = 60.0 / bpm / 4
    total_samples = int(total_steps * step_dur * sample_rate)
    samples = [0.0] * total_samples
    for step, note, dur in notes:
        freq = NOTE_FREQS.get(note)
        if not freq:
            continue
        start = int(step * step_dur * sample_rate)
        end = int((step + dur) * step_dur * sample_rate)
        note_len = end - start
        for i in range(start, min(end, total_samples)):
            t_local = (i - start) / sample_rate
            env = 1.0
            attack, release = 0.02, 0.1
            if t_local < attack:
                env = t_local / attack
            elif note_len > 0 and t_local > (note_len / sample_rate - release):
                env = max(0.0, ((note_len / sample_rate) - t_local) / release)
            samples[i] += 0.25 * env * math.sin(2 * math.pi * freq * t_local)
    mx = max((abs(s) for s in samples), default=1.0) or 1.0
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        for s in samples:
            v = max(-1.0, min(1.0, s / mx))
            w.writeframes(struct.pack("<h", int(v * 32000)))
    return path


def generate_alarm_wav():
    sample_rate = 44100
    duration = 3.0
    total_samples = int(duration * sample_rate)
    samples = []
    for i in range(total_samples):
        t = i / sample_rate
        freq = 800 if int(t * 2) % 2 == 0 else 600
        env = 0.3 * (1.0 - t / duration)
        samples.append(env * math.sin(2 * math.pi * freq * t))
    fd, path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        for s in samples:
            v = max(-1.0, min(1.0, s))
            w.writeframes(struct.pack("<h", int(v * 32000)))
    return path


def generate_celebration_wav():
    notes = [(0, "C5", 1), (1, "E5", 1), (2, "G5", 1), (3, "C6", 2)]
    return generate_melody_wav(notes, bpm=120, total_steps=8)


class OnlineRoot(BoxLayout):
    bg_color = [0.06, 0.10, 0.18, 1]
    accent = [0.29, 0.56, 0.89, 1]
    card_bg = [0.10, 0.15, 0.24, 1]


class OfflineRoot(BoxLayout):
    bg_color = [0.08, 0.08, 0.10, 1]
    accent = [0.91, 0.51, 0.17, 1]
    card_bg = [0.13, 0.13, 0.15, 1]


class StartScreen(Screen):
    def go_online(self):
        self.manager.current = "auth"

    def go_offline(self):
        # Убрали автоматическую очистку данных!
        # Теперь данные сохраняются между запусками
        self.manager.open_main(is_online=False)


class AuthScreen(Screen):
    error_text = StringProperty("")
    info_text = StringProperty("")

    def do_login(self):
        username = self.ids.username.text.strip()
        password = self.ids.password.text
        if not username or not password:
            self.error_text = "Введите логин и пароль"
            return
        uid, uname, err = db_online.login_user(username, password)
        if err:
            self.error_text = err
            return
        global CURRENT_USER_ID, CURRENT_USERNAME, CURRENT_MODE
        CURRENT_USER_ID = uid
        CURRENT_USERNAME = uname
        CURRENT_MODE = "online"
        self.info_text = f"Добро пожаловать, {uname}!"
        self.error_text = ""
        Clock.schedule_once(lambda dt: self.manager.open_main(is_online=True), 0.4)

    def do_register(self):
        username = self.ids.username.text.strip()
        email = self.ids.email.text.strip()
        password = self.ids.password.text
        if not username or not email or not password:
            self.error_text = "Заполните все поля"
            return
        uid, err = db_online.register_user(username, email, password)
        if err:
            self.error_text = err
            return
        global CURRENT_USER_ID, CURRENT_USERNAME, CURRENT_MODE
        CURRENT_USER_ID = uid
        CURRENT_USERNAME = username
        CURRENT_MODE = "online"
        self.info_text = f"Регистрация успешна! Входим как {username}..."
        self.error_text = ""
        Clock.schedule_once(lambda dt: self.manager.open_main(is_online=True), 0.6)

    def go_back(self):
        self.ids.username.text = ""
        self.ids.password.text = ""
        self.ids.email.text = ""
        self.error_text = ""
        self.info_text = ""
        self.manager.current = "start"


class SideMenu(RelativeLayout):
    is_open = BooleanProperty(False)
    is_online = BooleanProperty(False)
    accent = ObjectProperty([1, 1, 1, 1])
    main_screen = ObjectProperty(None)

    def toggle(self):
        if self.is_open:
            Animation(x=-self.width, d=0.25, t="out_quad").start(self)
            self.is_open = False
        else:
            Animation(x=0, d=0.25, t="out_quad").start(self)
            self.is_open = True

    def close(self):
        if self.is_open:
            Animation(x=-self.width, d=0.25, t="out_quad").start(self)
            self.is_open = False

    def logout(self):
        global CURRENT_MODE, CURRENT_USER_ID, CURRENT_USERNAME
        CURRENT_MODE = "offline"
        CURRENT_USER_ID = None
        CURRENT_USERNAME = None
        self.close()
        self.manager.current = "start"


class MainLayout(Screen):
    bg_color = ObjectProperty([0.06, 0.10, 0.18, 1])
    accent = ObjectProperty([0.29, 0.56, 0.89, 1])
    card_bg = ObjectProperty([0.10, 0.15, 0.24, 1])
    text_secondary = ObjectProperty([0.70, 0.78, 0.90, 1])
    title = StringProperty("Главная")
    is_online = BooleanProperty(False)
    username = StringProperty("")
    _alarm_check_event = ObjectProperty(None, allownone=True)
    _last_alarm_trigger = DictProperty({})
    _alarm_sound = ObjectProperty(None, allownone=True)

    def on_enter(self, *a):
        self.start_alarm_checker()

    def on_leave(self, *a):
        self.stop_alarm_checker()

    def start_alarm_checker(self):
        if self._alarm_check_event:
            self._alarm_check_event.cancel()
        self._alarm_check_event = Clock.schedule_interval(self.check_alarms, 1.0)

    def stop_alarm_checker(self):
        if self._alarm_check_event:
            self._alarm_check_event.cancel()
            self._alarm_check_event = None

    def check_alarms(self, dt):
        db = get_db()
        now = datetime.now()
        current_time = now.strftime("%H:%M")
        current_date = now.strftime("%Y-%m-%d")
        alarms = db.get_alarms(CURRENT_USER_ID) if CURRENT_MODE == "online" else db.get_alarms()
        for alarm in alarms:
            if not alarm.get("is_active"):
                continue
            if alarm["alarm_time"] == current_time:
                alarm_date = alarm.get("alarm_date")
                if alarm_date is None or alarm_date == current_date:
                    last_trigger_str = self._last_alarm_trigger.get(alarm["id"])
                    if last_trigger_str:
                        try:
                            last_trigger = datetime.strptime(last_trigger_str, "%Y-%m-%d %H:%M:%S")
                            if (now - last_trigger).total_seconds() < 60:
                                continue
                        except Exception:
                            pass
                    self._last_alarm_trigger[alarm["id"]] = now.strftime("%Y-%m-%d %H:%M:%S")
                    self.trigger_alarm(alarm)

    def trigger_alarm(self, alarm):
        sound_id = alarm.get("sound_id") if alarm else None
        path = None
        
        if sound_id:
            try:
                db = get_db()
                if CURRENT_MODE == "online":
                    sounds = db.get_sounds(CURRENT_USER_ID)
                else:
                    sounds = db.get_sounds()
                
                for s in sounds:
                    if s["id"] == sound_id:
                        data = json.loads(s["data"]) if isinstance(s["data"], str) else s["data"]
                        if data.get("type") == "melody":
                            notes = []
                            for n in data.get("notes", []):
                                notes.append((n["step"], n["note"], n.get("duration", 1)))
                            bpm = data.get("bpm", 120)
                            steps = data.get("steps", 32)
                            if notes:
                                path = generate_melody_wav(notes, bpm=bpm, total_steps=steps)
                        break
            except Exception as e:
                print(f"Ошибка загрузки звука будильника: {e}")
        
        if not path:
            path = generate_alarm_wav()
        
        if self._alarm_sound:
            try:
                self._alarm_sound.stop()
            except Exception:
                pass
        
        self._alarm_sound = SoundLoader.load(path)
        if self._alarm_sound:
            self._alarm_sound.loop = True
            self._alarm_sound.play()
        
        content = BoxLayout(orientation="vertical", padding=20, spacing=15)
        label = Label(text=alarm['name'], font_size=24, bold=True, color=(1, 1, 1, 1), size_hint_y=None, height=50)
        time_label = Label(text=alarm["alarm_time"], font_size=48, bold=True, color=self.accent, size_hint_y=None, height=80)
        btn_stop = Button(text="Остановить", size_hint_y=None, height=60,
                         background_color=[0.8, 0.2, 0.2, 1], color=(1, 1, 1, 1),
                         font_size=20, bold=True)
        content.add_widget(label)
        content.add_widget(time_label)
        content.add_widget(btn_stop)
        popup = Popup(title="Будильник", content=content, size_hint=(0.6, 0.5), auto_dismiss=False)
        
        def on_stop(instance):
            if self._alarm_sound:
                try:
                    self._alarm_sound.stop()
                except Exception:
                    pass
                self._alarm_sound = None
            popup.dismiss()
        
        btn_stop.bind(on_release=on_stop)
        popup.open()

    def open_section(self, section):
        self.ids.side_menu.close()
        sm = self.ids.content_sm
        mapping = {
            "home": lambda: None,
            "work": lambda: WorkScreen(bg_color=self.bg_color, accent=self.accent, card_bg=self.card_bg, text_secondary=self.text_secondary),
            "tasks": lambda: TasksScreen(bg_color=self.bg_color, accent=self.accent, card_bg=self.card_bg, text_secondary=self.text_secondary),
            "alarms": lambda: AlarmsScreen(bg_color=self.bg_color, accent=self.accent, card_bg=self.card_bg, text_secondary=self.text_secondary),
            "themes": lambda: ThemesScreen(bg_color=self.bg_color, accent=self.accent, card_bg=self.card_bg, text_secondary=self.text_secondary),
            "settings": lambda: SettingsScreen(bg_color=self.bg_color, accent=self.accent, card_bg=self.card_bg, text_secondary=self.text_secondary),
            "library": lambda: LibraryScreen(bg_color=self.bg_color, accent=self.accent, card_bg=self.card_bg, text_secondary=self.text_secondary),
            "animations": lambda: AnimationsScreen(bg_color=self.bg_color, accent=self.accent, card_bg=self.card_bg, text_secondary=self.text_secondary),
            "sounds": lambda: SoundsScreen(bg_color=self.bg_color, accent=self.accent, card_bg=self.card_bg, text_secondary=self.text_secondary),
        }
        titles = {
            "home": "Главная",
            "work": "Начать работу", "tasks": "Задачи", "alarms": "Будильники",
            "themes": "Тема", "settings": "Настройки",
            "library": "Библиотека", "animations": "Анимации",
            "sounds": "Звуки"
        }
        if section == "home":
            sm.current = "home"
            self.title = "Главная"
        elif section not in sm.screen_names:
            scr = mapping[section]()
            scr.name = section
            sm.add_widget(scr)
            sm.current = section
            self.title = titles.get(section, "Главная")
        else:
            sm.current = section
            self.title = titles.get(section, "Главная")


class WorkScreen(Screen):
    bg_color = ObjectProperty()
    accent = ObjectProperty()
    card_bg = ObjectProperty()
    text_secondary = ObjectProperty()

    def on_enter(self, *a):
        self.refresh()

    def refresh(self):
        data = []
        db = get_db()
        tasks = db.get_tasks(CURRENT_USER_ID) if CURRENT_MODE == "online" else db.get_tasks()
        for t in tasks:
            if t.get("is_completed"):
                continue
            data.append({
                "task_name": t["name"],
                "task_desc": t.get("description") or "",
                "task_date": t.get("scheduled_at") or "",
                "task_id": t["id"],
                "screen": self,
                "accent": self.accent,
            })
        self.ids.rv.data = data
        if not data:
            self.ids.empty_label.text = "Нет активных задач"
            self.ids.empty_label.opacity = 1
        else:
            self.ids.empty_label.opacity = 0

    def open_task(self, task_id):
        form = WorkTaskScreen(bg_color=self.bg_color, accent=self.accent, card_bg=self.card_bg,
                              task_id=task_id, screen=self, name="work_task")
        sm = self.manager
        if "work_task" in sm.screen_names:
            sm.remove_widget(sm.get_screen("work_task"))
        sm.add_widget(form)
        sm.current = "work_task"


class WorkTaskRow(RecycleDataViewBehavior, BoxLayout):
    task_name = StringProperty("")
    task_desc = StringProperty("")
    task_date = StringProperty("")
    task_id = NumericProperty(0)
    screen = ObjectProperty(None)
    accent = ObjectProperty([1, 1, 1, 1])

    def open_task(self):
        if self.screen:
            self.screen.open_task(self.task_id)


class WorkTaskScreen(Screen):
    bg_color = ObjectProperty()
    accent = ObjectProperty()
    card_bg = ObjectProperty()
    task_id = NumericProperty(0)
    screen = ObjectProperty(None)
    task_name = StringProperty("")
    task_desc = StringProperty("")
    task_date = StringProperty("")
    duration = NumericProperty(25)
    remaining_seconds = NumericProperty(0)
    is_running = BooleanProperty(False)
    _timer_event = ObjectProperty(None, allownone=True)
    animation_frames = ListProperty([])
    animation_fps = NumericProperty(8)
    _play_event = ObjectProperty(None, allownone=True)
    _play_idx = NumericProperty(0)
    _wakelock = ObjectProperty(None, allownone=True)

    def on_enter(self, *a):
        db = get_db()
        task = db.get_task(CURRENT_USER_ID, self.task_id) if CURRENT_MODE == "online" else db.get_task(self.task_id)
        if task:
            self.task_name = task["name"]
            self.task_desc = task.get("description") or ""
            self.task_date = task.get("scheduled_at") or ""
            self.duration = task.get("duration_minutes") or 25
            self.remaining_seconds = self.duration * 60
            anim_id = task.get("animation_id")
            if anim_id:
                all_anims = db.get_animations(CURRENT_USER_ID) if CURRENT_MODE == "online" else db.get_animations()
                for a in all_anims:
                    if a["id"] == anim_id:
                        try:
                            data = json.loads(a["data"]) if isinstance(a["data"], str) else a["data"]
                            if data.get("type") == "character":
                                self.animation_frames = data.get("frames", [])
                                self.animation_fps = data.get("fps", 8)
                                if self.animation_frames:
                                    self.start_animation_preview()
                        except:
                            pass
                        break

    def start_timer(self):
        if self.is_running:
            return
        self.is_running = True
        self.acquire_wakelock()
        self._timer_event = Clock.schedule_interval(self.timer_tick, 1.0)

    def timer_tick(self, dt):
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
        else:
            self.complete_task()

    def pause_timer(self):
        if not self.is_running:
            return
        self.is_running = False
        if self._timer_event:
            self._timer_event.cancel()
            self._timer_event = None
        self.remaining_seconds += 300

    def complete_task(self):
        self.is_running = False
        if self._timer_event:
            self._timer_event.cancel()
            self._timer_event = None
        self.stop_animation_preview()
        self.release_wakelock()
        self.show_celebration()
        db = get_db()
        if CURRENT_MODE == "online":
            db.delete_task(CURRENT_USER_ID, self.task_id)
        else:
            db.delete_task(self.task_id)

    def acquire_wakelock(self):
        if platform.system() == "Android":
            try:
                from android import mActivity
                from jnius import autoclass
                context = mActivity.getApplicationContext()
                PowerManager = autoclass('android.os.PowerManager')
                pm = context.getSystemService(context.POWER_SERVICE)
                self._wakelock = pm.newWakeLock(
                    PowerManager.SCREEN_BRIGHT_WAKE_LOCK | PowerManager.ACQUIRE_CAUSES_WAKEUP,
                    "AppPomodoro::TaskWakeLock"
                )
                self._wakelock.acquire()
                print("WakeLock активирован (экран не гаснет)")
            except Exception as e:
                print(f"Не удалось активировать WakeLock: {e}")
                self._wakelock = None
        else:
            self._wakelock = None
            print("WakeLock активирован (эмуляция)")

    def release_wakelock(self):
        if self._wakelock is not None:
            try:
                self._wakelock.release()
                print("WakeLock освобождён")
            except Exception as e:
                print(f"Не удалось освободить WakeLock: {e}")
            self._wakelock = None

    def show_celebration(self):
        content = BoxLayout(orientation="vertical", padding=20, spacing=15)
        label = Label(text="Задача выполнена!", font_size=28, bold=True, color=self.accent, size_hint_y=None, height=50)
        char_widget = CharacterWidget(size_hint=(1, 0.7))
        btn_close = Button(text="Отлично!", size_hint_y=None, height=50, background_color=self.accent, color=(1, 1, 1, 1), font_size=18, bold=True)
        content.add_widget(label)
        content.add_widget(char_widget)
        content.add_widget(btn_close)
        popup = Popup(title="Поздравляем!", content=content, size_hint=(0.6, 0.7), auto_dismiss=False)
        celebration_frames = [
            {"left_shoulder": -90, "left_elbow": 0, "right_shoulder": -90, "right_elbow": 0,
             "left_hip": 0, "left_knee": 0, "right_hip": 0, "right_knee": 0},
            {"left_shoulder": -120, "left_elbow": -30, "right_shoulder": -120, "right_elbow": -30,
             "left_hip": -20, "left_knee": 20, "right_hip": 20, "right_knee": -20},
            {"left_shoulder": -60, "left_elbow": 30, "right_shoulder": -60, "right_elbow": 30,
             "left_hip": 20, "left_knee": -20, "right_hip": -20, "right_knee": 20},
        ]
        play_idx = [0]
        def play_step(dt):
            char_widget.pose = dict(celebration_frames[play_idx[0]])
            play_idx[0] = (play_idx[0] + 1) % len(celebration_frames)
        play_event = [Clock.schedule_interval(play_step, 0.3)]
        path = generate_celebration_wav()
        sound = SoundLoader.load(path)
        if sound:
            sound.play()
        def on_close(instance):
            play_event[0].cancel()
            if sound:
                sound.stop()
            popup.dismiss()
            if self.screen:
                self.screen.refresh()
            self.manager.current = "work"
        btn_close.bind(on_release=on_close)
        popup.open()

    def start_animation_preview(self):
        if not self.animation_frames:
            return
        self.stop_animation_preview()
        self._play_idx = 0
        interval = 1.0 / max(1, self.animation_fps)
        self._play_event = Clock.schedule_interval(self._play_step, interval)

    def _play_step(self, dt):
        if not self.animation_frames:
            return
        self._play_idx = (self._play_idx + 1) % len(self.animation_frames)

    def stop_animation_preview(self):
        if self._play_event:
            self._play_event.cancel()
            self._play_event = None

    def go_back(self):
        self.on_leave()
        if self.screen:
            self.screen.refresh()
        sm = self.manager
        if "work_task" in sm.screen_names:
            sm.remove_widget(sm.get_screen("work_task"))
        sm.current = "work"

    def on_leave(self, *a):
        if self._timer_event:
            self._timer_event.cancel()
            self._timer_event = None
        self.is_running = False
        self.stop_animation_preview()
        self.release_wakelock()


class TasksScreen(Screen):
    bg_color = ObjectProperty()
    accent = ObjectProperty()
    card_bg = ObjectProperty()
    text_secondary = ObjectProperty()

    def on_enter(self, *a):
        self.refresh()

    def refresh(self):
        data = []
        db = get_db()
        tasks = db.get_tasks(CURRENT_USER_ID) if CURRENT_MODE == "online" else db.get_tasks()
        for t in tasks:
            data.append({
                "task_name": t["name"],
                "task_desc": t.get("description") or "",
                "task_date": t.get("scheduled_at") or "",
                "is_completed": bool(t.get("is_completed", 0)),
                "task_id": t["id"],
                "screen": self,
                "accent": self.accent,
            })
        self.ids.rv.data = data
        if not data:
            self.ids.empty_label.text = "Нет задач"
            self.ids.empty_label.opacity = 1
        else:
            self.ids.empty_label.opacity = 0

    def open_task_form(self, task_id):
        form = TaskFormScreen(bg_color=self.bg_color, accent=self.accent, card_bg=self.card_bg,
                              task_id=task_id, screen=self, name="task_form")
        sm = self.manager
        if "task_form" in sm.screen_names:
            sm.remove_widget(sm.get_screen("task_form"))
        sm.add_widget(form)
        sm.current = "task_form"


class TaskRow(RecycleDataViewBehavior, BoxLayout):
    task_name = StringProperty("")
    task_desc = StringProperty("")
    task_date = StringProperty("")
    is_completed = BooleanProperty(False)
    task_id = NumericProperty(0)
    screen = ObjectProperty(None)
    accent = ObjectProperty([1, 1, 1, 1])

    def toggle(self, active):
        db = get_db()
        if CURRENT_MODE == "online":
            db.toggle_task(CURRENT_USER_ID, self.task_id, active)
        else:
            db.toggle_task(self.task_id, active)
        if self.screen:
            self.screen.refresh()

    def edit(self):
        if self.screen:
            self.screen.open_task_form(self.task_id)

    def remove(self):
        db = get_db()
        if CURRENT_MODE == "online":
            db.delete_task(CURRENT_USER_ID, self.task_id)
        else:
            db.delete_task(self.task_id)
        if self.screen:
            self.screen.refresh()


class TaskFormScreen(Screen):
    bg_color = ObjectProperty()
    accent = ObjectProperty()
    card_bg = ObjectProperty()
    task_id = ObjectProperty(None)
    screen = ObjectProperty(None)
    name_init = StringProperty("")
    desc_init = StringProperty("")
    dur_init = StringProperty("")
    animation_options = ListProperty(["Без анимации"])
    animation_id_map = DictProperty({"Без анимации": None})
    animation_name_by_id = DictProperty({None: "Без анимации"})
    current_animation_id = ObjectProperty(None)

    def on_enter(self, *a):
        # Загружаем список анимаций для выбора
        db = get_db()
        if CURRENT_MODE == "online":
            all_anims = db.get_animations(CURRENT_USER_ID)
        else:
            all_anims = db.get_animations()
        
        options = ["Без анимации"]
        self.animation_id_map = {"Без анимации": None}
        self.animation_name_by_id = {None: "Без анимации"}
        for anim in all_anims:
            try:
                data = json.loads(anim["data"]) if isinstance(anim["data"], str) else anim["data"]
                if data.get("type") == "character":
                    options.append(anim["name"])
                    self.animation_id_map[anim["name"]] = anim["id"]
                    self.animation_name_by_id[anim["id"]] = anim["name"]
            except Exception:
                pass
        self.animation_options = options
        
        if self.task_id is not None:
            tasks = db.get_tasks(CURRENT_USER_ID) if CURRENT_MODE == "online" else db.get_tasks()
            for t in tasks:
                if t["id"] == self.task_id:
                    self.name_init = t["name"] or ""
                    self.desc_init = t.get("description") or ""
                    self.dur_init = str(t["duration_minutes"]) if t.get("duration_minutes") else ""
                    self.current_animation_id = t.get("animation_id")
                    break

    def save(self):
        name = self.ids.ti_name.text.strip()
        if not name:
            return
        desc = self.ids.ti_desc.text.strip()
        dur = self.ids.ti_dur.text.strip()
        dur = int(dur) if dur.isdigit() else None
        
        # Получаем выбранную анимацию
        selected_anim_name = self.ids.sp_animation.text
        animation_id = self.animation_id_map.get(selected_anim_name)
        
        db = get_db()
        if self.task_id is None:
            if CURRENT_MODE == "online":
                db.add_task(CURRENT_USER_ID, name, desc, scheduled_at=None, 
                           duration_minutes=dur, animation_id=animation_id)
            else:
                db.add_task(name, desc, scheduled_at=None, 
                           duration_minutes=dur, animation_id=animation_id)
        else:
            if CURRENT_MODE == "online":
                db.update_task(CURRENT_USER_ID, self.task_id, name=name, description=desc, 
                              duration_minutes=dur, animation_id=animation_id)
            else:
                db.update_task(self.task_id, name=name, description=desc, 
                              duration_minutes=dur, animation_id=animation_id)
        self.cancel()

    def cancel(self):
        if self.screen:
            self.screen.refresh()
        self.manager.current = "tasks"

class AlarmsScreen(Screen):
    bg_color = ObjectProperty()
    accent = ObjectProperty()
    card_bg = ObjectProperty()
    text_secondary = ObjectProperty()

    def on_enter(self, *a):
        self.refresh()

    def refresh(self):
        data = []
        db = get_db()
        alarms = db.get_alarms(CURRENT_USER_ID) if CURRENT_MODE == "online" else db.get_alarms()
        for a in alarms:
            data.append({
                "alarm_name": a["name"],
                "alarm_time": a["alarm_time"],
                "alarm_date": a.get("alarm_date") or "",
                "is_active": bool(a.get("is_active", 1)),
                "alarm_id": a["id"],
                "screen": self,
                "accent": self.accent,
            })
        self.ids.rv.data = data
        if not data:
            self.ids.empty_label.text = "Нет будильников"
            self.ids.empty_label.opacity = 1
        else:
            self.ids.empty_label.opacity = 0

    def open_alarm_form(self, alarm_id):
        db = get_db()
        alarm_data = None
        if CURRENT_MODE == "online":
            all_alarms = db.get_alarms(CURRENT_USER_ID)
        else:
            all_alarms = db.get_alarms()
        
        for a in all_alarms:
            if a["id"] == alarm_id:
                alarm_data = a
                break
        
        form = AlarmFormScreen(
            bg_color=self.bg_color, 
            accent=self.accent, 
            card_bg=self.card_bg,
            alarm_id=alarm_id, 
            screen=self, 
            name="alarm_form",
            name_init=alarm_data["name"] if alarm_data else "",
            time_init=alarm_data["alarm_time"] if alarm_data else "08:00",
            date_init=alarm_data.get("alarm_date", "") if alarm_data else ""
        )
        sm = self.manager
        if "alarm_form" in sm.screen_names:
            sm.remove_widget(sm.get_screen("alarm_form"))
        sm.add_widget(form)
        sm.current = "alarm_form"


class AlarmRow(RecycleDataViewBehavior, BoxLayout):
    alarm_name = StringProperty("")
    alarm_time = StringProperty("")
    alarm_date = StringProperty("")
    is_active = BooleanProperty(True)
    alarm_id = NumericProperty(0)
    screen = ObjectProperty(None)
    accent = ObjectProperty([1, 1, 1, 1])

    def toggle(self, active):
        db = get_db()
        if CURRENT_MODE == "online":
            db.update_alarm(CURRENT_USER_ID, self.alarm_id, is_active=int(active))
        else:
            db.update_alarm(self.alarm_id, is_active=int(active))

    def edit(self):
        if self.screen:
            self.screen.open_alarm_form(self.alarm_id)

    def remove(self):
        db = get_db()
        if CURRENT_MODE == "online":
            db.delete_alarm(CURRENT_USER_ID, self.alarm_id)
        else:
            db.delete_alarm(self.alarm_id)
        if self.screen:
            self.screen.refresh()


class AlarmFormScreen(Screen):
    bg_color = ObjectProperty()
    accent = ObjectProperty()
    card_bg = ObjectProperty()
    alarm_id = ObjectProperty(None)
    screen = ObjectProperty(None)
    name_init = StringProperty("")
    time_init = StringProperty("08:00")
    date_init = StringProperty("")
    sound_options = ListProperty(["Стандартная"])
    sound_id_map = DictProperty({"Стандартная": 0})
    sound_name_by_id = DictProperty({0: "Стандартная"})
    current_sound_id = NumericProperty(0)

    def on_enter(self, *a):
        db = get_db()
        if CURRENT_MODE == "online":
            sounds = db.get_sounds(CURRENT_USER_ID)
        else:
            sounds = db.get_sounds()
        
        options = ["Стандартная"]
        self.sound_id_map = {"Стандартная": 0}
        self.sound_name_by_id = {0: "Стандартная"}
        for s in sounds:
            options.append(s["name"])
            self.sound_id_map[s["name"]] = s["id"]
            self.sound_name_by_id[s["id"]] = s["name"]
        self.sound_options = options
        
        if self.alarm_id is not None:
            alarms = db.get_alarms(CURRENT_USER_ID) if CURRENT_MODE == "online" else db.get_alarms()
            for a in alarms:
                if a["id"] == self.alarm_id:
                    self.name_init = a["name"]
                    self.time_init = a["alarm_time"]
                    self.date_init = a.get("alarm_date") or ""
                    self.current_sound_id = a.get("sound_id") or 0
                    break

    def save(self):
        name = self.ids.ti_name.text.strip()
        time = self.ids.sp_hour.text + ":" + self.ids.sp_minute.text
        date = self.ids.ti_date.text.strip() or None
        
        selected_sound_name = self.ids.sp_sound.text
        sound_id = self.sound_id_map.get(selected_sound_name, 0)
        if sound_id == 0:
            sound_id = None
        
        if not name:
            return
        
        db = get_db()
        if self.alarm_id is None:
            if CURRENT_MODE == "online":
                db.add_alarm(CURRENT_USER_ID, name, time, date, sound_id=sound_id)
            else:
                db.add_alarm(name, time, date, sound_id=sound_id)
        else:
            if CURRENT_MODE == "online":
                db.update_alarm(CURRENT_USER_ID, self.alarm_id, 
                              name=name, alarm_time=time, alarm_date=date, sound_id=sound_id)
            else:
                db.update_alarm(self.alarm_id, 
                              name=name, alarm_time=time, alarm_date=date, sound_id=sound_id)
        self.cancel()

    def cancel(self):
        if self.screen:
            self.screen.refresh()
        self.manager.current = "alarms"

    def set_today(self):
        self.ids.ti_date.text = datetime.now().strftime("%Y-%m-%d")


def _make_tag_button(tag_name, accent_color, on_toggle):
    btn = ToggleButton(
        text=tag_name, size_hint=(None, None),
        width=100, height=40,
        background_normal="", background_down="",
        background_color=[0.3, 0.3, 0.35, 1],
        color=(1, 1, 1, 1),
    )
    btn.bind(state=lambda i, v, t=tag_name: _on_tag_state(i, v, t, accent_color, on_toggle))
    return btn


def _on_tag_state(instance, state, tag_name, accent_color, on_toggle):
    instance.background_color = accent_color if state == "down" else [0.3, 0.3, 0.35, 1]
    if on_toggle:
        on_toggle(tag_name, state)


class AnimationsScreen(Screen):
    bg_color = ObjectProperty()
    accent = ObjectProperty()
    card_bg = ObjectProperty()
    text_secondary = ObjectProperty()
    search_text = StringProperty("")
    selected_tags = ListProperty([])

    def on_enter(self, *a):
        self.refresh()

    def _fetch_animations(self):
        db = get_db()
        all_anims = db.get_animations(CURRENT_USER_ID) if CURRENT_MODE == "online" else db.get_animations()
        if self.search_text:
            all_anims = [a for a in all_anims if self.search_text.lower() in a["name"].lower()]
        if self.selected_tags:
            filtered = []
            for a in all_anims:
                tag_names = [t["name"] for t in db.get_animation_tags(a["id"])]
                if any(tag in tag_names for tag in self.selected_tags):
                    filtered.append(a)
            all_anims = filtered
        return all_anims

    def refresh(self):
        db = get_db()
        all_anims = self._fetch_animations()
        data = []
        for a in all_anims:
            tags = db.get_animation_tags(a["id"])
            is_own = CURRENT_MODE == "online" and a.get("author_id") == CURRENT_USER_ID
            data.append({
                "anim_name": a["name"], "anim_data": a["data"],
                "anim_tags": ", ".join(t["name"] for t in tags),
                "anim_id": a["id"],
                "is_public": bool(a.get("is_public", 0)),
                "is_own": is_own,
                "screen": self,
                "accent": self.accent,
            })
        self.ids.rv.data = data
        if not data:
            self.ids.empty_label.text = "Нет анимаций"
            self.ids.empty_label.opacity = 1
        else:
            self.ids.empty_label.opacity = 0
        self.ids.tags_grid.clear_widgets()
        for tag in db.get_tags():
            btn = _make_tag_button(tag["name"], self.accent, self.toggle_tag)
            if tag["name"] in self.selected_tags:
                btn.state = "down"
                btn.background_color = self.accent
            self.ids.tags_grid.add_widget(btn)

    def toggle_tag(self, tag_name, state):
        if state == "down":
            if tag_name not in self.selected_tags:
                self.selected_tags.append(tag_name)
        else:
            if tag_name in self.selected_tags:
                self.selected_tags.remove(tag_name)
        self._refresh_list_only()

    def _refresh_list_only(self):
        db = get_db()
        all_anims = self._fetch_animations()
        data = []
        for a in all_anims:
            tags = db.get_animation_tags(a["id"])
            is_own = CURRENT_MODE == "online" and a.get("author_id") == CURRENT_USER_ID
            data.append({
                "anim_name": a["name"], "anim_data": a["data"],
                "anim_tags": ", ".join(t["name"] for t in tags),
                "anim_id": a["id"],
                "is_public": bool(a.get("is_public", 0)),
                "is_own": is_own,
                "screen": self,
                "accent": self.accent,
            })
        self.ids.rv.data = data
        if not data:
            self.ids.empty_label.text = "Нет анимаций"
            self.ids.empty_label.opacity = 1
        else:
            self.ids.empty_label.opacity = 0

    def open_anim_form(self, anim_id):
        db = get_db()
        anim_data = None
        if CURRENT_MODE == "online":
            all_anims = db.get_animations(CURRENT_USER_ID)
        else:
            all_anims = db.get_animations()
        
        for a in all_anims:
            if a["id"] == anim_id:
                anim_data = a
                break
        
        form = AnimationFormScreen(
            bg_color=self.bg_color, 
            accent=self.accent, 
            card_bg=self.card_bg,
            anim_id=anim_id, 
            screen=self, 
            name="anim_form",
            name_init=anim_data["name"] if anim_data else "",
            data_init=anim_data["data"] if anim_data else ""
        )
        sm = self.manager
        if "anim_form" in sm.screen_names:
            sm.remove_widget(sm.get_screen("anim_form"))
        sm.add_widget(form)
        sm.current = "anim_form"


class AnimationRow(RecycleDataViewBehavior, BoxLayout):
    anim_name = StringProperty("")
    anim_data = StringProperty("")
    anim_tags = StringProperty("")
    anim_id = NumericProperty(0)
    is_public = BooleanProperty(False)
    is_own = BooleanProperty(False)
    screen = ObjectProperty(None)
    accent = ObjectProperty([1, 1, 1, 1])

    def edit(self):
        if self.screen:
            self.screen.open_anim_form(self.anim_id)

    def remove(self):
        db = get_db()
        if CURRENT_MODE == "online":
            db.delete_animation(CURRENT_USER_ID, self.anim_id)
        else:
            db.delete_animation(self.anim_id)
        if self.screen:
            self.screen.refresh()

    def publish(self):
        if CURRENT_MODE == "online" and self.is_own:
            db_online.update_animation(CURRENT_USER_ID, self.anim_id, is_public=True)
            if self.screen:
                self.screen.refresh()

    def preview(self):
        try:
            data = json.loads(self.anim_data) if isinstance(self.anim_data, str) else self.anim_data
            if data.get("type") == "character":
                frames = data.get("frames", [])
                fps = data.get("fps", 8)
                if frames:
                    show_animation_preview(self.anim_name, frames, fps)
        except Exception as e:
            print(f"Ошибка превью: {e}")


class SoundRow(RecycleDataViewBehavior, BoxLayout):
    sound_name = StringProperty("")
    sound_data = StringProperty("")
    sound_tags = StringProperty("")
    sound_id = NumericProperty(0)
    is_public = BooleanProperty(False)
    is_own = BooleanProperty(False)
    screen = ObjectProperty(None)
    accent = ObjectProperty([1, 1, 1, 1])

    def edit(self):
        if self.screen:
            self.screen.open_sound_form(self.sound_id)

    def remove(self):
        db = get_db()
        if CURRENT_MODE == "online":
            db.delete_sound(CURRENT_USER_ID, self.sound_id)
        else:
            db.delete_sound(self.sound_id)
        if self.screen:
            self.screen.refresh()

    def publish(self):
        if CURRENT_MODE == "online" and self.is_own:
            db_online.update_sound(CURRENT_USER_ID, self.sound_id, is_public=True)
            if self.screen:
                self.screen.refresh()

    def preview(self):
        try:
            data = json.loads(self.sound_data) if isinstance(self.sound_data, str) else self.sound_data
            if data.get("type") == "melody":
                notes = []
                for n in data.get("notes", []):
                    notes.append((n["step"], n["note"], n.get("duration", 1)))
                bpm = data.get("bpm", 120)
                steps = data.get("steps", 32)
                if notes:
                    path = generate_melody_wav(notes, bpm=bpm, total_steps=steps)
                    sound = SoundLoader.load(path)
                    if sound:
                        sound.play()
                        show_sound_preview(self.sound_name, sound)
        except Exception as e:
            print(f"Ошибка превью: {e}")


JOINT_NAMES = [
    "left_shoulder", "left_elbow",
    "right_shoulder", "right_elbow",
    "left_hip", "left_knee",
    "right_hip", "right_knee",
]
DEFAULT_POSE = {j: 0 for j in JOINT_NAMES}


class CharacterWidget(Widget):
    pose = DictProperty(DEFAULT_POSE.copy())

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._redraw, size=self._redraw, pose=self._redraw)
        Clock.schedule_once(lambda dt: self._redraw(), 0)

    def _redraw(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(0.9, 0.9, 0.95, 1)
            cx = self.x + self.width / 2
            cy = self.y + self.height * 0.55
            head_r = min(self.width, self.height) * 0.08
            torso_len = min(self.width, self.height) * 0.22
            limb_len = min(self.width, self.height) * 0.18
            Ellipse(pos=(cx - head_r, cy + torso_len / 2), size=(head_r * 2, head_r * 2))
            neck_y = cy + torso_len / 2
            hip_y = cy - torso_len / 2
            Line(points=[cx, neck_y, cx, hip_y], width=2)
            p = self.pose
            ls = p.get("left_shoulder", 0)
            le = p.get("left_elbow", 0)
            rs = p.get("right_shoulder", 0)
            re = p.get("right_elbow", 0)
            lh = p.get("left_hip", 0)
            lk = p.get("left_knee", 0)
            rh = p.get("right_hip", 0)
            rk = p.get("right_knee", 0)
            self._draw_limb(cx, neck_y, ls, le, limb_len, side=-1)
            self._draw_limb(cx, neck_y, rs, re, limb_len, side=1)
            self._draw_limb(cx, hip_y, lh + 180, lk, limb_len, side=-1)
            self._draw_limb(cx, hip_y, rh + 180, rk, limb_len, side=1)

    def _draw_limb(self, x, y, ang1, ang2, length, side):
        a1 = math.radians(ang1)
        x1 = x + side * length * math.sin(a1)
        y1 = y - length * math.cos(a1)
        a2 = math.radians(ang1 + ang2)
        x2 = x1 + side * length * math.sin(a2) * 0.5
        y2 = y1 - length * math.cos(a2) * 0.8
        Line(points=[x, y, x1, y1, x2, y2], width=2)


def show_animation_preview(name, frames, fps):
    content = BoxLayout(orientation="vertical", padding=10, spacing=10)
    char_widget = CharacterWidget(size_hint=(1, 0.8))
    char_widget.pose = dict(frames[0]) if frames else dict(DEFAULT_POSE)
    label = Label(text=name, size_hint_y=None, height=40, font_size=18, bold=True, color=(1, 1, 1, 1))
    btn_close = Button(text="Закрыть", size_hint_y=None, height=50, background_color=[0.5, 0.5, 0.55, 1], color=(1, 1, 1, 1))
    content.add_widget(label)
    content.add_widget(char_widget)
    content.add_widget(btn_close)
    popup = Popup(title="Превью анимации", content=content, size_hint=(0.6, 0.7), auto_dismiss=False)
    play_event = [None]
    play_idx = [0]
    def play_step(dt):
        if not frames:
            return
        char_widget.pose = dict(frames[play_idx[0]])
        play_idx[0] = (play_idx[0] + 1) % len(frames)
    def on_close(instance):
        if play_event[0]:
            play_event[0].cancel()
        popup.dismiss()
    btn_close.bind(on_release=on_close)
    popup.bind(on_dismiss=on_close)
    interval = 1.0 / max(1, fps)
    play_event[0] = Clock.schedule_interval(play_step, interval)
    popup.open()


def show_sound_preview(name, sound):
    content = BoxLayout(orientation="vertical", padding=20, spacing=15)
    label = Label(text=name, size_hint_y=None, height=40, font_size=18, bold=True, color=(1, 1, 1, 1))
    btn_stop = Button(text="Остановить", size_hint_y=None, height=50, background_color=[0.7, 0.2, 0.2, 1], color=(1, 1, 1, 1))
    btn_close = Button(text="Закрыть", size_hint_y=None, height=50, background_color=[0.5, 0.5, 0.55, 1], color=(1, 1, 1, 1))
    content.add_widget(label)
    content.add_widget(btn_stop)
    content.add_widget(btn_close)
    popup = Popup(title="Воспроизведение", content=content, size_hint=(0.5, 0.4), auto_dismiss=False)
    def on_stop(instance):
        if sound:
            sound.stop()
    def on_close(instance):
        if sound:
            sound.stop()
        popup.dismiss()
    btn_stop.bind(on_release=on_stop)
    btn_close.bind(on_release=on_close)
    popup.bind(on_dismiss=on_close)
    popup.open()


class JointSlider(BoxLayout):
    label = StringProperty("")
    value = NumericProperty(0)
    
    def __init__(self, **kwargs):
        self.register_event_type('on_slider_value')
        super().__init__(**kwargs)
    
    def on_slider_value(self, *args):
        pass
    
    def _on_slider_change(self, value):
        self.value = int(value)
        self.dispatch('on_slider_value', self.value)


class AnimationFormScreen(Screen):
    bg_color = ObjectProperty()
    accent = ObjectProperty()
    card_bg = ObjectProperty()
    anim_id = ObjectProperty(None)
    screen = ObjectProperty(None)
    name_init = StringProperty("")
    data_init = StringProperty("")
    frames = ListProperty([])
    current_pose = DictProperty(DEFAULT_POSE.copy())
    current_idx = NumericProperty(-1)
    fps = NumericProperty(8)
    _play_event = ObjectProperty(None, allownone=True)
    _play_idx = NumericProperty(0)

    def on_enter(self, *a):
        self.ids.tags_grid.clear_widgets()
        current_tag_ids = []
        db = get_db()
        if self.anim_id is not None:
            all_anims = db.get_animations(CURRENT_USER_ID) if CURRENT_MODE == "online" else db.get_animations()
            for a in all_anims:
                if a["id"] == self.anim_id:
                    self.name_init = a["name"]
                    self.data_init = a["data"] if isinstance(a["data"], str) else json.dumps(a["data"])
                    break
            for t in db.get_animation_tags(self.anim_id):
                current_tag_ids.append(t["id"])
            try:
                d = json.loads(self.data_init)
                if d.get("type") == "character":
                    self.frames = d.get("frames", [])
                    self.fps = d.get("fps", 8)
                    if self.frames:
                        self.current_pose = dict(self.frames[0])
                        self.current_idx = 0
            except Exception:
                pass
        for tag in db.get_tags():
            btn = _make_tag_button(tag["name"], self.accent, None)
            if tag["id"] in current_tag_ids:
                btn.state = "down"
                btn.background_color = self.accent
            self.ids.tags_grid.add_widget(btn)
        self._build_frames_list()

    def _build_frames_list(self):
        grid = self.ids.frames_grid
        grid.clear_widgets()
        for i, frame in enumerate(self.frames):
            b = Button(
                text=f"#{i+1}",
                size_hint=(None, None), width=60, height=60,
                background_color=self.accent if i == self.current_idx else [0.3, 0.3, 0.35, 1],
                color=(1, 1, 1, 1),
            )
            b.bind(on_release=lambda inst, idx=i: self.select_frame(idx))
            grid.add_widget(b)

    def select_frame(self, idx):
        self.current_idx = idx
        self.current_pose = dict(self.frames[idx])
        self._build_frames_list()

    def add_frame(self):
        self.frames.append(dict(self.current_pose))
        self.current_idx = len(self.frames) - 1
        self._build_frames_list()

    def delete_frame(self):
        if 0 <= self.current_idx < len(self.frames):
            self.frames.pop(self.current_idx)
            if self.frames:
                self.current_idx = min(self.current_idx, len(self.frames) - 1)
                self.current_pose = dict(self.frames[self.current_idx])
            else:
                self.current_idx = -1
                self.current_pose = dict(DEFAULT_POSE)
            self._build_frames_list()

    def duplicate_frame(self):
        if self.current_idx >= 0:
            self.frames.insert(self.current_idx + 1, dict(self.frames[self.current_idx]))
            self.current_idx += 1
            self._build_frames_list()

    def on_current_pose(self, *args):
        if 0 <= self.current_idx < len(self.frames):
            self.frames[self.current_idx] = dict(self.current_pose)

    def play_animation(self):
        if not self.frames:
            return
        self.stop_animation()
        self._play_idx = 0
        interval = 1.0 / max(1, self.fps)
        self._play_event = Clock.schedule_interval(self._play_step, interval)

    def _play_step(self, dt):
        if not self.frames:
            self.stop_animation()
            return
        self.current_pose = dict(self.frames[self._play_idx])
        self.current_idx = self._play_idx
        self._build_frames_list()
        self._play_idx = (self._play_idx + 1) % len(self.frames)

    def stop_animation(self):
        if self._play_event:
            self._play_event.cancel()
            self._play_event = None

    def save(self):
        name = self.ids.ti_name.text.strip()
        if not name:
            return
        data = json.dumps({
            "type": "character",
            "fps": int(self.fps),
            "frames": [dict(f) for f in self.frames],
        })
        db = get_db()
        if self.anim_id is None:
            if CURRENT_MODE == "online":
                aid = db.add_animation(CURRENT_USER_ID, name, data)
            else:
                aid = db.add_animation(name, data)
        else:
            if CURRENT_MODE == "online":
                db.update_animation(CURRENT_USER_ID, self.anim_id, name=name, data=data)
                aid = self.anim_id
            else:
                db.update_animation(self.anim_id, name=name, data=data)
                aid = self.anim_id
        tag_ids = []
        for child in self.ids.tags_grid.children:
            if child.state == "down":
                tag_id = db.add_tag(child.text)
                if tag_id:
                    tag_ids.append(tag_id)
        db.set_animation_tags(aid, tag_ids)
        self.cancel()

    def cancel(self):
        self.stop_animation()
        if self.screen:
            self.screen.refresh()
        self.manager.current = "animations"


class SoundsScreen(Screen):
    bg_color = ObjectProperty()
    accent = ObjectProperty()
    card_bg = ObjectProperty()
    text_secondary = ObjectProperty()
    search_text = StringProperty("")
    selected_tags = ListProperty([])

    def on_enter(self, *a):
        self.refresh()

    def _fetch_sounds(self):
        db = get_db()
        all_sounds = db.get_sounds(CURRENT_USER_ID) if CURRENT_MODE == "online" else db.get_sounds()
        if self.search_text:
            all_sounds = [s for s in all_sounds if self.search_text.lower() in s["name"].lower()]
        if self.selected_tags:
            filtered = []
            for s in all_sounds:
                tag_names = [t["name"] for t in db.get_sound_tags(s["id"])]
                if any(tag in tag_names for tag in self.selected_tags):
                    filtered.append(s)
            all_sounds = filtered
        return all_sounds

    def refresh(self):
        db = get_db()
        all_sounds = self._fetch_sounds()
        data = []
        for s in all_sounds:
            tags = db.get_sound_tags(s["id"])
            is_own = CURRENT_MODE == "online" and s.get("author_id") == CURRENT_USER_ID
            data.append({
                "sound_name": s["name"], "sound_data": s["data"],
                "sound_tags": ", ".join(t["name"] for t in tags),
                "sound_id": s["id"],
                "is_public": bool(s.get("is_public", 0)),
                "is_own": is_own,
                "screen": self,
                "accent": self.accent,
            })
        self.ids.rv.data = data
        if not data:
            self.ids.empty_label.text = "Нет звуков"
            self.ids.empty_label.opacity = 1
        else:
            self.ids.empty_label.opacity = 0
        self.ids.tags_grid.clear_widgets()
        for tag in db.get_tags():
            btn = _make_tag_button(tag["name"], self.accent, self.toggle_tag)
            if tag["name"] in self.selected_tags:
                btn.state = "down"
                btn.background_color = self.accent
            self.ids.tags_grid.add_widget(btn)

    def toggle_tag(self, tag_name, state):
        if state == "down":
            if tag_name not in self.selected_tags:
                self.selected_tags.append(tag_name)
        else:
            if tag_name in self.selected_tags:
                self.selected_tags.remove(tag_name)
        self._refresh_list_only()

    def _refresh_list_only(self):
        db = get_db()
        all_sounds = self._fetch_sounds()
        data = []
        for s in all_sounds:
            tags = db.get_sound_tags(s["id"])
            is_own = CURRENT_MODE == "online" and s.get("author_id") == CURRENT_USER_ID
            data.append({
                "sound_name": s["name"], "sound_data": s["data"],
                "sound_tags": ", ".join(t["name"] for t in tags),
                "sound_id": s["id"],
                "is_public": bool(s.get("is_public", 0)),
                "is_own": is_own,
                "screen": self,
                "accent": self.accent,
            })
        self.ids.rv.data = data
        if not data:
            self.ids.empty_label.text = "Нет звуков"
            self.ids.empty_label.opacity = 1
        else:
            self.ids.empty_label.opacity = 0

    def open_sound_form(self, sound_id):
        db = get_db()
        sound_data = None
        if CURRENT_MODE == "online":
            all_sounds = db.get_sounds(CURRENT_USER_ID)
        else:
            all_sounds = db.get_sounds()
        
        for s in all_sounds:
            if s["id"] == sound_id:
                sound_data = s
                break
        
        form = SoundFormScreen(
            bg_color=self.bg_color, 
            accent=self.accent, 
            card_bg=self.card_bg,
            sound_id=sound_id, 
            screen=self, 
            name="sound_form",
            name_init=sound_data["name"] if sound_data else "",
            data_init=sound_data["data"] if sound_data else ""
        )
        sm = self.manager
        if "sound_form" in sm.screen_names:
            sm.remove_widget(sm.get_screen("sound_form"))
        sm.add_widget(form)
        sm.current = "sound_form"


STEPS_COUNT = 32


class SoundFormScreen(Screen):
    bg_color = ObjectProperty()
    accent = ObjectProperty()
    card_bg = ObjectProperty()
    sound_id = ObjectProperty(None)
    screen = ObjectProperty(None)
    name_init = StringProperty("")
    data_init = StringProperty("")
    grid = DictProperty({})
    bpm = NumericProperty(120)
    _current_sound = ObjectProperty(None, allownone=True)

    def on_enter(self, *a):
        self.ids.tags_grid.clear_widgets()
        current_tag_ids = []
        db = get_db()
        if self.sound_id is not None:
            all_sounds = db.get_sounds(CURRENT_USER_ID) if CURRENT_MODE == "online" else db.get_sounds()
            for s in all_sounds:
                if s["id"] == self.sound_id:
                    self.name_init = s["name"]
                    self.data_init = s["data"] if isinstance(s["data"], str) else json.dumps(s["data"])
                    break
            for t in db.get_sound_tags(self.sound_id):
                current_tag_ids.append(t["id"])
            try:
                d = json.loads(self.data_init)
                if d.get("type") == "melody":
                    self.bpm = d.get("bpm", 120)
                    self.grid = {}
                    for n in d.get("notes", []):
                        step = n["step"]
                        note = n["note"]
                        if note in NOTE_NAMES:
                            ni = NOTE_NAMES.index(note)
                            self.grid.setdefault(step, {})[ni] = True
            except Exception:
                pass
        for tag in db.get_tags():
            btn = _make_tag_button(tag["name"], self.accent, None)
            if tag["id"] in current_tag_ids:
                btn.state = "down"
                btn.background_color = self.accent
            self.ids.tags_grid.add_widget(btn)
        self._build_piano_roll()

    def _build_piano_roll(self):
        grid_w = self.ids.piano_grid
        grid_w.clear_widgets()
        for note_idx in range(len(NOTE_NAMES) - 1, -1, -1):
            note_name = NOTE_NAMES[note_idx]
            lbl = Label(text=note_name, size_hint=(None, None),
                        width=40, height=24, color=(1, 1, 1, 0.8), font_size=11)
            grid_w.add_widget(lbl)
            for step in range(STEPS_COUNT):
                active = note_idx in self.grid.get(step, {})
                btn = ToggleButton(
                    text="", size_hint=(None, None),
                    width=22, height=24,
                    background_normal="", background_down="",
                    background_color=self.accent if active else [0.25, 0.27, 0.33, 1],
                    state="down" if active else "normal",
                    group=f"step_{step}_{note_idx}",
                )
                btn.bind(state=lambda inst, val, s=step, ni=note_idx: self._cell_toggled(s, ni, val, inst))
                grid_w.add_widget(btn)
        grid_w.cols = STEPS_COUNT + 1

    def _cell_toggled(self, step, note_idx, state, instance):
        if state == "down":
            self.grid.setdefault(step, {})[note_idx] = True
            instance.background_color = self.accent
        else:
            if step in self.grid and note_idx in self.grid[step]:
                del self.grid[step][note_idx]
                if not self.grid[step]:
                    del self.grid[step]
            instance.background_color = [0.25, 0.27, 0.33, 1]

    def clear_grid(self):
        self.grid = {}
        self._build_piano_roll()

    def play_melody(self):
        self.stop_melody()
        notes = []
        for step, note_dict in self.grid.items():
            for note_idx in note_dict.keys():
                notes.append((step, NOTE_NAMES[note_idx], 1))
        if not notes:
            return
        path = generate_melody_wav(notes, bpm=int(self.bpm), total_steps=STEPS_COUNT)
        self._current_sound = SoundLoader.load(path)
        self._current_sound.play()

    def stop_melody(self):
        if self._current_sound:
            self._current_sound.stop()
            self._current_sound = None

    def save(self):
        name = self.ids.ti_name.text.strip()
        if not name:
            return
        notes = []
        for step, note_dict in self.grid.items():
            for note_idx in note_dict.keys():
                notes.append({"step": step, "note": NOTE_NAMES[note_idx], "duration": 1})
        data = json.dumps({
            "type": "melody",
            "bpm": int(self.bpm),
            "steps": STEPS_COUNT,
            "notes": notes,
        })
        db = get_db()
        if self.sound_id is None:
            if CURRENT_MODE == "online":
                sid = db.add_sound(CURRENT_USER_ID, name, data)
            else:
                sid = db.add_sound(name, data)
        else:
            if CURRENT_MODE == "online":
                db.update_sound(CURRENT_USER_ID, self.sound_id, name=name, data=data)
                sid = self.sound_id
            else:
                db.update_sound(self.sound_id, name=name, data=data)
                sid = self.sound_id
        tag_ids = []
        for child in self.ids.tags_grid.children:
            if child.state == "down":
                tag_id = db.add_tag(child.text)
                if tag_id:
                    tag_ids.append(tag_id)
        db.set_sound_tags(sid, tag_ids)
        self.cancel()

    def cancel(self):
        self.stop_melody()
        if self.screen:
            self.screen.refresh()
        self.manager.current = "sounds"


class ThemesScreen(Screen):
    bg_color = ObjectProperty()
    accent = ObjectProperty()
    card_bg = ObjectProperty()
    text_secondary = ObjectProperty()

    def on_enter(self, *a):
        self.ids.grid.clear_widgets()
        for th in get_db().get_themes():
            b = Button(text=th["name"], size_hint_y=None, height=60,
                       background_color=self.accent, color=(1, 1, 1, 1))
            self.ids.grid.add_widget(b)


class SettingsScreen(Screen):
    bg_color = ObjectProperty()
    accent = ObjectProperty()
    card_bg = ObjectProperty()
    text_secondary = ObjectProperty()

    def change_mode(self):
        content = BoxLayout(orientation="vertical", padding=20, spacing=15)
        label = Label(text="Выберите режим работы:", font_size=18, 
                     color=(1, 1, 1, 1), size_hint_y=None, height=40)
        btn_online = Button(text="Онлайн", size_hint_y=None, height=50,
                           background_color=[0.20, 0.55, 0.95, 1], color=(1, 1, 1, 1),
                           font_size=16, bold=True)
        btn_offline = Button(text="Оффлайн", size_hint_y=None, height=50,
                            background_color=[0.78, 0.42, 0.12, 1], color=(1, 1, 1, 1),
                            font_size=16, bold=True)
        btn_cancel = Button(text="Отмена", size_hint_y=None, height=40,
                           background_color=[0.35, 0.38, 0.45, 1], color=(1, 1, 1, 1))
        content.add_widget(label)
        content.add_widget(btn_online)
        content.add_widget(btn_offline)
        content.add_widget(btn_cancel)
        
        popup = Popup(title="Смена режима", content=content, 
                     size_hint=(0.7, 0.5), auto_dismiss=False)
        
        def on_online(instance):
            global CURRENT_MODE, CURRENT_USER_ID, CURRENT_USERNAME
            if CURRENT_MODE != "online":
                CURRENT_MODE = "online"
                CURRENT_USER_ID = None
                CURRENT_USERNAME = None
            popup.dismiss()
            # Переходим на экран авторизации
            self.manager.parent.current = "auth"
        
        def on_offline(instance):
            global CURRENT_MODE, CURRENT_USER_ID, CURRENT_USERNAME
            if CURRENT_MODE != "offline":
                CURRENT_MODE = "offline"
                CURRENT_USER_ID = None
                CURRENT_USERNAME = None
            popup.dismiss()
            # Возвращаемся на главный экран
            self.manager.parent.current = "start"
        
        def on_cancel(instance):
            popup.dismiss()
        
        btn_online.bind(on_release=on_online)
        btn_offline.bind(on_release=on_offline)
        btn_cancel.bind(on_release=on_cancel)
        popup.open()

class LibraryScreen(Screen):
    bg_color = ObjectProperty()
    accent = ObjectProperty()
    card_bg = ObjectProperty()
    text_secondary = ObjectProperty()

    def on_enter(self, *a):
        self.ids.grid.clear_widgets()
        db = get_db()
        if CURRENT_MODE == "online":
            all_anims = db.get_animations(CURRENT_USER_ID)
            pub_anims = [a for a in all_anims if a.get("is_public")]
            for a in pub_anims:
                b = Button(text=a['name'], size_hint_y=None, height=60,
                           background_color=self.accent, color=(1, 1, 1, 1))
                b.bind(on_release=lambda inst, anim=a: self.preview_animation(anim))
                self.ids.grid.add_widget(b)
            all_sounds = db.get_sounds(CURRENT_USER_ID)
            pub_sounds = [s for s in all_sounds if s.get("is_public")]
            for s in pub_sounds:
                b = Button(text=s['name'], size_hint_y=None, height=60,
                           background_color=self.accent, color=(1, 1, 1, 1))
                b.bind(on_release=lambda inst, sound=s: self.preview_sound(sound))
                self.ids.grid.add_widget(b)
            if not pub_anims and not pub_sounds:
                self.ids.grid.add_widget(Label(text="Пока нет публичного контента",
                                                size_hint_y=None, height=40,
                                                color=(0.8, 0.8, 0.85, 1)))

    def preview_animation(self, anim):
        try:
            data = json.loads(anim["data"]) if isinstance(anim["data"], str) else anim["data"]
            if data.get("type") == "character":
                frames = data.get("frames", [])
                fps = data.get("fps", 8)
                if frames:
                    show_animation_preview(anim["name"], frames, fps)
        except Exception as e:
            print(f"Ошибка превью: {e}")

    def preview_sound(self, sound):
        try:
            data = json.loads(sound["data"]) if isinstance(sound["data"], str) else sound["data"]
            if data.get("type") == "melody":
                notes = []
                for n in data.get("notes", []):
                    notes.append((n["step"], n["note"], n.get("duration", 1)))
                bpm = data.get("bpm", 120)
                steps = data.get("steps", 32)
                if notes:
                    path = generate_melody_wav(notes, bpm=bpm, total_steps=steps)
                    snd = SoundLoader.load(path)
                    if snd:
                        snd.play()
                        show_sound_preview(sound["name"], snd)
        except Exception as e:
            print(f"Ошибка превью: {e}")


class RootSM(ScreenManager):
    def open_main(self, is_online: bool):
        if is_online:
            root = OnlineRoot()
            bg, ac, cb = root.bg_color, root.accent, root.card_bg
            ts = [0.75, 0.85, 1, 1]
        else:
            root = OfflineRoot()
            bg, ac, cb = root.bg_color, root.accent, root.card_bg
            ts = [0.75, 0.75, 0.78, 1]
        layout = MainLayout(bg_color=bg, accent=ac, card_bg=cb,
                            text_secondary=ts,
                            is_online=is_online,
                            username=CURRENT_USERNAME or "",
                            title="Главная", name="main")
        if "main" in self.screen_names:
            self.remove_widget(self.get_screen("main"))
        self.add_widget(layout)
        self.current = "main"


for name, cls in [
    ("OnlineRoot", OnlineRoot), ("OfflineRoot", OfflineRoot),
    ("StartScreen", StartScreen), ("AuthScreen", AuthScreen),
    ("SideMenu", SideMenu), ("MainLayout", MainLayout),
    ("WorkScreen", WorkScreen), ("WorkTaskRow", WorkTaskRow), ("WorkTaskScreen", WorkTaskScreen),
    ("TasksScreen", TasksScreen), ("TaskRow", TaskRow), ("TaskFormScreen", TaskFormScreen),
    ("AlarmsScreen", AlarmsScreen), ("AlarmRow", AlarmRow), ("AlarmFormScreen", AlarmFormScreen),
    ("AnimationsScreen", AnimationsScreen), ("AnimationRow", AnimationRow),
    ("AnimationFormScreen", AnimationFormScreen), ("CharacterWidget", CharacterWidget),
    ("SoundsScreen", SoundsScreen), ("SoundRow", SoundRow),
    ("SoundFormScreen", SoundFormScreen),
    ("JointSlider", JointSlider),
    ("ThemesScreen", ThemesScreen), ("SettingsScreen", SettingsScreen),
    ("LibraryScreen", LibraryScreen), ("RootSM", RootSM),
]:
    Factory.register(name, cls=cls)


class AppPomodoro(App):
    def build(self):
        self.title = "AppPomodoro"
        
        # Копируем иконки при запуске EXE
        ensure_icons_available()
        
        db_offline.init_db()
        
        try:
            db_online.migrate()
        except Exception as e:
            print(f"Online migration error: {e}")
        
        kv_path = get_resource_path("app.kv")
        Builder.load_file(kv_path)
        
        root = RootSM()
        root.add_widget(StartScreen(name="start"))
        root.add_widget(AuthScreen(name="auth"))
        root.current = "start"
        return root


if __name__ == "__main__":
    AppPomodoro().run()