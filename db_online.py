import pg8000
import hashlib
import os
import json
from datetime import datetime

# Настройка pg8000 для использования %s плейсхолдеров (как в psycopg2)
pg8000.paramstyle = 'format'

PG_CONFIG = {
    "host":     "bswemuptkafjoojbg39u-postgresql.services.clever-cloud.com",
    "port":     50013,
    "database": "bswemuptkafjoojbg39u",  # pg8000 использует 'database' вместо 'dbname'
    "user":     "ud4wv3foiaqb2bjzxsrb",
    "password": "BWE6Ogunxf2yh6dXkSxl18I8tHHy0f",
}


def get_connection():
    conn = pg8000.connect(**PG_CONFIG)
    return conn


def migrate():
    """Добавляет недостающие колонки в существующие таблицы"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("ALTER TABLE alarms ADD COLUMN sound_id INTEGER")
            conn.commit()
        except Exception:
            conn.rollback()
    except Exception as e:
        print(f"Migration error: {e}")
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def _hash_password(password: str, salt: bytes = None):
    if salt is None:
        salt = os.urandom(16)
    if isinstance(password, str):
        password = password.encode("utf-8")
    h = hashlib.pbkdf2_hmac("sha256", password, salt, 100000)
    return salt.hex(), h.hex()


def register_user(username: str, email: str, password: str):
    username = username.strip()
    email = email.strip()
    if not username or not email or not password:
        return None, "Все поля обязательны"
    if len(password) < 4:
        return None, "Пароль слишком короткий"
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM users WHERE username = %s OR email = %s", (username, email))
        if cur.fetchone():
            return None, "Пользователь или email уже существует"
        salt_hex, hash_hex = _hash_password(password)
        full_hash = salt_hex + ":" + hash_hex
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
            (username, email, full_hash)
        )
        uid = cur.fetchone()[0]
        conn.commit()
        return uid, None
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except:
                pass
        return None, f"Ошибка БД: {e}"
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def login_user(username: str, password: str):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, username, password_hash FROM users WHERE username = %s", (username,))
        row = cur.fetchone()
        if not row:
            return None, None, "Пользователь не найден"
        uid, uname, stored_hash = row
        try:
            salt_hex, hash_hex = stored_hash.split(":", 1)
        except ValueError:
            return None, None, "Неверный формат пароля в БД"
        _, new_hash = _hash_password(password, bytes.fromhex(salt_hex))
        if new_hash != hash_hex:
            return None, None, "Неверный пароль"
        return uid, uname, None
    except Exception as e:
        return None, None, f"Ошибка: {e}"
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def _row_to_dict(row, columns):
    d = dict(zip(columns, row))
    for k, v in list(d.items()):
        if isinstance(v, (dict, list)):
            d[k] = json.dumps(v, ensure_ascii=False)
        if isinstance(v, bool):
            d[k] = int(v)
    return d


def get_tags():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name FROM tags ORDER BY name")
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1]} for r in rows]
    except Exception as e:
        print(f"get_tags error: {e}")
        return []
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def add_tag(name):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("INSERT INTO tags (name) VALUES (%s) RETURNING id", (name,))
            row = cur.fetchone()
            conn.commit()
            return row[0] if row else None
        except Exception:
            conn.rollback()
            cur.execute("SELECT id FROM tags WHERE name = %s", (name,))
            row = cur.fetchone()
            return row[0] if row else None
    except Exception as e:
        print(f"add_tag error: {e}")
        return None
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def get_tasks(user_id):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, description, scheduled_at, duration_minutes, animation_id, is_completed, created_at
            FROM tasks WHERE user_id = %s ORDER BY created_at DESC
        """, (user_id,))
        cols = ["id", "name", "description", "scheduled_at", "duration_minutes",
                "animation_id", "is_completed", "created_at"]
        rows = cur.fetchall()
        out = []
        for r in rows:
            d = _row_to_dict(r, cols)
            if d["scheduled_at"]:
                d["scheduled_at"] = d["scheduled_at"].strftime("%Y-%m-%d %H:%M") if hasattr(d["scheduled_at"], "strftime") else str(d["scheduled_at"])
            if d["created_at"] and hasattr(d["created_at"], "strftime"):
                d["created_at"] = d["created_at"].strftime("%Y-%m-%d %H:%M")
            out.append(d)
        return out
    except Exception as e:
        print(f"get_tasks error: {e}")
        return []
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def get_task(user_id, task_id):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, description, scheduled_at, duration_minutes, animation_id, is_completed, created_at
            FROM tasks WHERE id = %s AND user_id = %s
        """, (task_id, user_id))
        cols = ["id", "name", "description", "scheduled_at", "duration_minutes",
                "animation_id", "is_completed", "created_at"]
        row = cur.fetchone()
        if not row:
            return None
        d = _row_to_dict(row, cols)
        if d["scheduled_at"] and hasattr(d["scheduled_at"], "strftime"):
            d["scheduled_at"] = d["scheduled_at"].strftime("%Y-%m-%d %H:%M")
        if d["created_at"] and hasattr(d["created_at"], "strftime"):
            d["created_at"] = d["created_at"].strftime("%Y-%m-%d %H:%M")
        return d
    except Exception as e:
        print(f"get_task error: {e}")
        return None
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def add_task(user_id, name, description="", scheduled_at=None, duration_minutes=None, animation_id=None):
    if scheduled_at is None:
        scheduled_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO tasks (user_id, name, description, scheduled_at, duration_minutes, animation_id)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (user_id, name, description, scheduled_at, duration_minutes, animation_id))
        tid = cur.fetchone()[0]
        conn.commit()
        return tid
    except Exception as e:
        print(f"add_task error: {e}")
        return None
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def update_task(user_id, task_id, **fields):
    if not fields:
        return
    conn = None
    try:
        sets = ", ".join(f"{k} = %s" for k in fields.keys())
        vals = list(fields.values()) + [task_id, user_id]
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"UPDATE tasks SET {sets} WHERE id = %s AND user_id = %s", vals)
        conn.commit()
    except Exception as e:
        print(f"update_task error: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def delete_task(user_id, task_id):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s", (task_id, user_id))
        conn.commit()
    except Exception as e:
        print(f"delete_task error: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def toggle_task(user_id, task_id, completed: bool):
    update_task(user_id, task_id, is_completed=completed)


def get_alarms(user_id):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, name, alarm_time, alarm_date, is_active, sound_id FROM alarms
            WHERE user_id = %s ORDER BY alarm_time
        """, (user_id,))
        cols = ["id", "name", "alarm_time", "alarm_date", "is_active", "sound_id"]
        rows = cur.fetchall()
        out = []
        for r in rows:
            d = _row_to_dict(r, cols)
            if d["alarm_time"] and hasattr(d["alarm_time"], "strftime"):
                d["alarm_time"] = d["alarm_time"].strftime("%H:%M")
            if d["alarm_date"] and hasattr(d["alarm_date"], "strftime"):
                d["alarm_date"] = d["alarm_date"].strftime("%Y-%m-%d")
            out.append(d)
        return out
    except Exception as e:
        print(f"get_alarms error: {e}")
        return []
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def add_alarm(user_id, name, alarm_time, alarm_date=None, is_active=True, sound_id=None):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO alarms (user_id, name, alarm_time, alarm_date, is_active, sound_id)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
        """, (user_id, name, alarm_time, alarm_date, bool(is_active), sound_id))
        aid = cur.fetchone()[0]
        conn.commit()
        return aid
    except Exception as e:
        print(f"add_alarm error: {e}")
        return None
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def update_alarm(user_id, alarm_id, **fields):
    if not fields:
        return
    if "is_active" in fields:
        fields["is_active"] = bool(fields["is_active"])
    conn = None
    try:
        sets = ", ".join(f"{k} = %s" for k in fields.keys())
        vals = list(fields.values()) + [alarm_id, user_id]
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(f"UPDATE alarms SET {sets} WHERE id = %s AND user_id = %s", vals)
        conn.commit()
    except Exception as e:
        print(f"update_alarm error: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def delete_alarm(user_id, alarm_id):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM alarms WHERE id = %s AND user_id = %s", (alarm_id, user_id))
        conn.commit()
    except Exception as e:
        print(f"delete_alarm error: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def get_themes():
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, name, filename FROM themes")
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1], "filename": r[2]} for r in rows]
    except Exception as e:
        print(f"get_themes error: {e}")
        return []
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def get_animations(user_id):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, author_id, name, data, is_public, created_at
            FROM animations WHERE author_id = %s OR is_public = TRUE ORDER BY name
        """, (user_id,))
        cols = ["id", "author_id", "name", "data", "is_public", "created_at"]
        rows = cur.fetchall()
        return [_row_to_dict(r, cols) for r in rows]
    except Exception as e:
        print(f"get_animations error: {e}")
        return []
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def add_animation(user_id, name, data, is_public=False):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        # pg8000 не поддерживает ::jsonb cast напрямую, используем %s::jsonb
        cur.execute(
            "INSERT INTO animations (author_id, name, data, is_public) VALUES (%s, %s, %s::jsonb, %s) RETURNING id",
            (user_id, name, data, bool(is_public))
        )
        aid = cur.fetchone()[0]
        conn.commit()
        return aid
    except Exception as e:
        print(f"add_animation error: {e}")
        return None
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def update_animation(user_id, anim_id, **fields):
    if not fields:
        return
    if "is_public" in fields:
        fields["is_public"] = bool(fields["is_public"])
    conn = None
    try:
        sets_parts = []
        vals = []
        for k, v in fields.items():
            if k == "data":
                sets_parts.append("data = %s::jsonb")
            else:
                sets_parts.append(f"{k} = %s")
            vals.append(v)
        vals += [anim_id, user_id]
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            f"UPDATE animations SET {', '.join(sets_parts)} WHERE id = %s AND author_id = %s",
            vals
        )
        conn.commit()
    except Exception as e:
        print(f"update_animation error: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def delete_animation(user_id, anim_id):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM animations WHERE id = %s AND author_id = %s", (anim_id, user_id))
        conn.commit()
    except Exception as e:
        print(f"delete_animation error: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def get_animation_tags(anim_id):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT t.id, t.name FROM tags t
            JOIN animation_tags at ON t.id = at.tag_id
            WHERE at.animation_id = %s
        """, (anim_id,))
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1]} for r in rows]
    except Exception as e:
        print(f"get_animation_tags error: {e}")
        return []
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def set_animation_tags(anim_id, tag_ids):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM animation_tags WHERE animation_id = %s", (anim_id,))
        for tid in tag_ids:
            cur.execute("INSERT INTO animation_tags (animation_id, tag_id) VALUES (%s, %s)", (anim_id, tid))
        conn.commit()
    except Exception as e:
        print(f"set_animation_tags error: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def get_sounds(user_id):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, author_id, name, data, is_public, created_at
            FROM sounds WHERE author_id = %s OR is_public = TRUE ORDER BY name
        """, (user_id,))
        cols = ["id", "author_id", "name", "data", "is_public", "created_at"]
        rows = cur.fetchall()
        return [_row_to_dict(r, cols) for r in rows]
    except Exception as e:
        print(f"get_sounds error: {e}")
        return []
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def add_sound(user_id, name, data, is_public=False):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO sounds (author_id, name, data, is_public) VALUES (%s, %s, %s::jsonb, %s) RETURNING id",
            (user_id, name, data, bool(is_public))
        )
        sid = cur.fetchone()[0]
        conn.commit()
        return sid
    except Exception as e:
        print(f"add_sound error: {e}")
        return None
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def update_sound(user_id, sound_id, **fields):
    if not fields:
        return
    if "is_public" in fields:
        fields["is_public"] = bool(fields["is_public"])
    conn = None
    try:
        sets_parts = []
        vals = []
        for k, v in fields.items():
            if k == "data":
                sets_parts.append("data = %s::jsonb")
            else:
                sets_parts.append(f"{k} = %s")
            vals.append(v)
        vals += [sound_id, user_id]
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            f"UPDATE sounds SET {', '.join(sets_parts)} WHERE id = %s AND author_id = %s",
            vals
        )
        conn.commit()
    except Exception as e:
        print(f"update_sound error: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def delete_sound(user_id, sound_id):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM sounds WHERE id = %s AND author_id = %s", (sound_id, user_id))
        conn.commit()
    except Exception as e:
        print(f"delete_sound error: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def get_sound_tags(sound_id):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT t.id, t.name FROM tags t
            JOIN sound_tags st ON t.id = st.tag_id
            WHERE st.sound_id = %s
        """, (sound_id,))
        rows = cur.fetchall()
        return [{"id": r[0], "name": r[1]} for r in rows]
    except Exception as e:
        print(f"get_sound_tags error: {e}")
        return []
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass


def set_sound_tags(sound_id, tag_ids):
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM sound_tags WHERE sound_id = %s", (sound_id,))
        for tid in tag_ids:
            cur.execute("INSERT INTO sound_tags (sound_id, tag_id) VALUES (%s, %s)", (sound_id, tid))
        conn.commit()
    except Exception as e:
        print(f"set_sound_tags error: {e}")
        if conn:
            try:
                conn.rollback()
            except:
                pass
    finally:
        if conn:
            try:
                conn.close()
            except:
                pass