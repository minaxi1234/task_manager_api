# set_admin.py
import sqlite3
conn = sqlite3.connect("task_manager.db")
cur = conn.cursor()
cur.execute("UPDATE users SET is_admin = 1 WHERE id = 1")
conn.commit()
conn.close()
print("Done: user id 1 set to is_admin = 1")

