from fastapi import FastAPI
from pymongo import MongoClient
from bson import ObjectId
import json

app = FastAPI()

client = MongoClient("mongodb+srv://nongcalljai-admin:NongCall2026!@nongcalljai.kbb0yds.mongodb.net/nongcalljai")
db = client["nongcalljai"]

def fix_doc(doc):
    return json.loads(json.dumps(doc, default=str))

@app.get("/")
def root():
    return {"status": "NongCallJai API is running!"}

@app.get("/api/stats")
def get_stats():
    return {
        "users": db["users"].count_documents({}),
        "calls": db["callsummaries"].count_documents({}),
        "answers": db["callanswers"].count_documents({})
    }

@app.get("/api/users")
def get_users():
    return [fix_doc(u) for u in db["users"].find({}).limit(10)]

@app.get("/api/calls")
def get_calls():
    return [fix_doc(c) for c in db["callsummaries"].find({}).limit(10)]
