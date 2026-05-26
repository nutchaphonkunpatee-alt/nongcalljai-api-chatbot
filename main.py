from fastapi import FastAPI, Query
from pymongo import MongoClient
from bson import ObjectId
import json
from datetime import datetime

app = FastAPI()

client = MongoClient(
    "mongodb+srv://nongcalljai-admin:NongCall2026!@nongcalljai.kbb0yds.mongodb.net/nongcalljai",
    tlsAllowInvalidCertificates=True
)
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

# ดึงรายงานล่าสุดของผู้สูงอายุ
@app.get("/api/report")
def get_report(elder_id: str = Query(None), phone: str = Query(None)):
    if not elder_id and not phone:
        return {"error": "กรุณาส่ง elder_id หรือ phone"}

    # หา elder จาก phone
    if phone and not elder_id:
        elder = db["elders"].find_one({"phone": phone})
        if not elder:
            return {"error": "ไม่พบผู้สูงอายุเบอร์: " + phone}
        elder_id = str(elder["_id"])

    # หา callSession ล่าสุด
    session = db["callsessions"].find_one(
        {"elderId": elder_id},
        sort=[("createdAt", -1)]
    )
    if not session:
        return {"error": "ยังไม่มีข้อมูลการโทรของ: " + elder_id}

    session_id = str(session["_id"])

    # หา summary
    summary = db["callsummaries"].find_one({"callSessionId": session_id})

    # หา answers
    answers = list(db["callanswers"].find({"callSessionId": session_id}))

    return {
        "elder_id": elder_id,
        "session_id": session_id,
        "summary": fix_doc(summary) if summary else {},
        "answers": [fix_doc(a) for a in answers]
    }

# ดึงข้อมูล caregiver จาก phone
@app.get("/api/caregiver")
def get_caregiver(phone: str = Query(None)):
    if not phone:
        return {"error": "กรุณาส่ง phone"}
    user = db["users"].find_one({"phone": phone})
    if not user:
        return {"error": "ไม่พบ caregiver เบอร์: " + phone}
    return fix_doc(user)

# ดึงรายชื่อ caregiver ทั้งหมด
@app.get("/api/users")
def get_users():
    return [fix_doc(u) for u in db["users"].find({}).limit(10)]

# ดึง callsummaries ทั้งหมด
@app.get("/api/calls")
def get_calls():
    return [fix_doc(c) for c in db["callsummaries"].find({}).limit(10)]

# ดึง callanswers ทั้งหมด
@app.get("/api/answers")
def get_answers():
    return [fix_doc(a) for a in db["callanswers"].find({}).limit(10)]

# บันทึก log จาก Voicebot
@app.post("/api/saveLog")
def save_log(body: dict):
    body["createdAt"] = datetime.now().isoformat()
    result = db["callsummaries"].insert_one(body)
    return {"success": True, "id": str(result.inserted_id)}

# บันทึกข้อความจากลูกหลาน
@app.post("/api/saveMessage")
def save_message(body: dict):
    session_id = body.get("session_id")
    message = body.get("message")
    if not session_id or not message:
        return {"error": "กรุณาส่ง session_id และ message"}
    db["callsummaries"].update_one(
        {"callSessionId": session_id},
        {"\": {"caringMessage": message}}
    )
    return {"success": True}
