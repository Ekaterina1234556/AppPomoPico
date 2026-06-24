import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("app_data.db")


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS themes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        filename TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS animations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        data TEXT NOT NULL,
        is_public INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS sounds (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        data TEXT NOT NULL,
        is_public INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE
    );

    CREATE TABLE IF NOT EXISTS animation_tags (
        animation_id INTEGER,
        tag_id INTEGER,
        UNIQUE(animation_id, tag_id),
        FOREIGN KEY(animation_id) REFERENCES animations(id) ON DELETE CASCADE,
        FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS sound_tags (
        sound_id INTEGER,
        tag_id INTEGER,
        UNIQUE(sound_id, tag_id),
        FOREIGN KEY(sound_id) REFERENCES sounds(id) ON DELETE CASCADE,
        FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT,
        scheduled_at TEXT,
        duration_minutes INTEGER,
        animation_id INTEGER,
        is_completed INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY(animation_id) REFERENCES animations(id)
    );

    CREATE TABLE IF NOT EXISTS alarms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        alarm_time TEXT NOT NULL,
        alarm_date TEXT,
        is_active INTEGER DEFAULT 1,
        sound_id INTEGER
    );
    """)
    conn.commit()
    
    # Миграция: добавить sound_id если его нет (для старых БД)
    try:
        conn.execute("ALTER TABLE alarms ADD COLUMN sound_id INTEGER")
        conn.commit()
    except sqlite3.OperationalError:
        pass
    
    conn.close()


def clear_all_data():
    conn = get_connection()
    conn.executescript("""
    DELETE FROM tasks;
    DELETE FROM alarms;
    DELETE FROM animations;
    DELETE FROM sounds;
    DELETE FROM animation_tags;
    DELETE FROM sound_tags;
    DELETE FROM tags;
    DELETE FROM themes;
    """)
    conn.commit()
    conn.close()


# ---------- TASKS ----------
def get_tasks():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_task(task_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def add_task(name, description="", scheduled_at=None,
             duration_minutes=None, animation_id=None):
    if scheduled_at is None:
        scheduled_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO tasks
           (name, description, scheduled_at, duration_minutes, animation_id)
           VALUES (?, ?, ?, ?, ?)""",
        (name, description, scheduled_at, duration_minutes, animation_id)
    )
    conn.commit()
    tid = cur.lastrowid
    conn.close()
    return tid


def update_task(task_id, **fields):
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields.keys())
    vals = list(fields.values()) + [task_id]
    conn = get_connection()
    conn.execute(f"UPDATE tasks SET {sets} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def delete_task(task_id):
    conn = get_connection()
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()


def toggle_task(task_id, completed: bool):
    update_task(task_id, is_completed=int(completed))


# ---------- ALARMS ----------
def get_alarms():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM alarms ORDER BY alarm_time").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_alarm(name, alarm_time, alarm_date=None, is_active=True, sound_id=None):
    conn = get_connection()
    cur = conn.execute(
        """INSERT INTO alarms (name, alarm_time, alarm_date, is_active, sound_id)
           VALUES (?, ?, ?, ?, ?)""",
        (name, alarm_time, alarm_date, int(is_active), sound_id)
    )
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid


def update_alarm(alarm_id, **fields):
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields.keys())
    vals = list(fields.values()) + [alarm_id]
    conn = get_connection()
    conn.execute(f"UPDATE alarms SET {sets} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def delete_alarm(alarm_id):
    conn = get_connection()
    conn.execute("DELETE FROM alarms WHERE id = ?", (alarm_id,))
    conn.commit()
    conn.close()


# ---------- THEMES ----------
def get_themes():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM themes").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---------- TAGS ----------
def get_tags():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tags ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_tag(name):
    conn = get_connection()
    try:
        cur = conn.execute("INSERT INTO tags (name) VALUES (?)", (name,))
        conn.commit()
        tid = cur.lastrowid
    except sqlite3.IntegrityError:
        row = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()
        tid = row["id"] if row else None
    conn.close()
    return tid


def delete_tag(tag_id):
    conn = get_connection()
    conn.execute("DELETE FROM tags WHERE id = ?", (tag_id,))
    conn.commit()
    conn.close()


# ---------- ANIMATIONS ----------
def get_animations():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM animations ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_animation(name, data, is_public=False):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO animations (name, data, is_public) VALUES (?, ?, ?)",
        (name, data, int(is_public))
    )
    conn.commit()
    aid = cur.lastrowid
    conn.close()
    return aid


def update_animation(anim_id, **fields):
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields.keys())
    vals = list(fields.values()) + [anim_id]
    conn = get_connection()
    conn.execute(f"UPDATE animations SET {sets} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def delete_animation(anim_id):
    conn = get_connection()
    conn.execute("DELETE FROM animations WHERE id = ?", (anim_id,))
    conn.commit()
    conn.close()


def get_animation_tags(anim_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT t.id, t.name FROM tags t
        JOIN animation_tags at ON t.id = at.tag_id
        WHERE at.animation_id = ?
    """, (anim_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_animation_tags(anim_id, tag_ids):
    conn = get_connection()
    conn.execute("DELETE FROM animation_tags WHERE animation_id = ?", (anim_id,))
    conn.executemany(
        "INSERT INTO animation_tags (animation_id, tag_id) VALUES (?, ?)",
        [(anim_id, tid) for tid in tag_ids]
    )
    conn.commit()
    conn.close()


# ---------- SOUNDS ----------
def get_sounds():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM sounds ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_sound(name, data, is_public=False):
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO sounds (name, data, is_public) VALUES (?, ?, ?)",
        (name, data, int(is_public))
    )
    conn.commit()
    sid = cur.lastrowid
    conn.close()
    return sid


def update_sound(sound_id, **fields):
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields.keys())
    vals = list(fields.values()) + [sound_id]
    conn = get_connection()
    conn.execute(f"UPDATE sounds SET {sets} WHERE id = ?", vals)
    conn.commit()
    conn.close()


def delete_sound(sound_id):
    conn = get_connection()
    conn.execute("DELETE FROM sounds WHERE id = ?", (sound_id,))
    conn.commit()
    conn.close()


def get_sound_tags(sound_id):
    conn = get_connection()
    rows = conn.execute("""
        SELECT t.id, t.name FROM tags t
        JOIN sound_tags st ON t.id = st.tag_id
        WHERE st.sound_id = ?
    """, (sound_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_sound_tags(sound_id, tag_ids):
    conn = get_connection()
    conn.execute("DELETE FROM sound_tags WHERE sound_id = ?", (sound_id,))
    conn.executemany(
        "INSERT INTO sound_tags (sound_id, tag_id) VALUES (?, ?)",
        [(sound_id, tid) for tid in tag_ids]
    )
    conn.commit()
    conn.close()