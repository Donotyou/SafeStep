import sqlite3

db = r"D:\SavaStep-main\data\safepath.db"
conn = sqlite3.connect(db)
c = conn.cursor()

for t in c.execute('SELECT name FROM sqlite_master WHERE type="table";'):
    c.execute('DELETE FROM ' + t[0])

conn.commit()
conn.close()
print("Database emptied, tables preserved!")
