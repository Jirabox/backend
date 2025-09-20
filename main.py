from fastapi.middleware.cors import CORSMiddleware
from sqlite3.dbapi2 import OperationalError
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import FileResponse
from random import choice
from datetime import datetime
from dateutil import parser
import asyncio
import pathlib
import sqlite3
import os

con = sqlite3.connect("metadata.db")
cur = con.cursor()

background_tasks = set()

if input("Create new Sqlite table? [y/N] ") == "y":
    cur.execute("DROP TABLE IF EXISTS metadata")
    cur.execute("CREATE TABLE metadata(name, time, retention)")
    con.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    retention_checker = asyncio.create_task(check_retention())
    background_tasks.add(retention_checker)
    retention_checker.add_done_callback(background_tasks.discard)
    yield
    con.close()
    retention_checker.cancel()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

chars = list("1234567890-=!£$%^&*()_+QWERTYUIOP{}[]ASDFGHJKL:@~;'#|ZXCVBNM<>,.?`¬")

async def check_retention():
    while True:
        for row in cur.execute("SELECT name, time, retention FROM metadata"):
            time = parser.parse(row[1])
            difference = datetime.now() - time
            if (difference.seconds//60)%60 >= row[2]:
                os.remove(pathlib.Path(row[0]))
                cur.execute("DELETE FROM metadata WHERE name = ?", (row[0],))
                con.commit()
                print(f"Removed {row[0]} from database and storage.")
        await asyncio.sleep(10)
 
def create_database_entry(time, retention, extension):
    res = cur.execute("SELECT name FROM metadata")
    filenames = res.fetchall()
    while True:
        filename = (f"J{choice(chars)}R{choice(chars)}{extension}",)
        if filename not in filenames:
            break
    cur.execute("INSERT INTO metadata VALUES(?, ?, ?)", (filename[0], time, retention))
    con.commit()
    return filename[0]

@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    extension = pathlib.Path(str(file.filename)).suffix
    time = datetime.now()
    min_age = 1440
    max_age = 43200
    max_size = 1000
    file_size = file.size * (10**-6)
    retention = min_age + (min_age - max_age) * pow((file_size / max_size - 1), 3)
    filename = create_database_entry(time, retention, extension)
    with open(filename, "wb") as newfile:
        newfile.write(await file.read())
        return {"file": filename}

@app.get("/download")
async def download(file: str):
    with open(file, "rb") as f:
        return FileResponse(file)

