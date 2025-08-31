from sqlite3.dbapi2 import OperationalError
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from random import choice
import pathlib
import sqlite3

app = FastAPI()
chars = list("1234567890-=!£$%^&*()_+QWERTYUIOP{}[]ASDFGHJKL:@~;'#|ZXCVBNM<>,.?`¬")

con = sqlite3.connect("metadata.db")
cur = con.cursor()

if input("Create new Sqlite table? [y/N] ") == "y":
    try:
        cur.execute("CREATE TABLE metadata(name)")
    except OperationalError:
        cur.execute("DROP TABLE metadata")
        cur.execute("CREATE TABLE metadata(name)")

def pick_filename():
    res = cur.execute("SELECT name FROM metadata")
    filenames = res.fetchall()
    while True:
        filename = (f"J{choice(chars)}R{choice(chars)}",)
        if filename not in filenames:
            break
    cur.execute("INSERT INTO metadata VALUES(?)", filename)
    con.commit()
    return filename[0]

@app.post("/upload")
async def upload(file: UploadFile):
    extension = pathlib.Path(str(file.filename)).suffix
    filename = f"{pick_filename()}{extension}"
    with open(filename, "wb") as newfile:
        newfile.write(await file.read())
        return {"file": filename}

@app.get("/download")
async def download(file: str):
    with open(file, "rb") as f:
        return FileResponse(file)

