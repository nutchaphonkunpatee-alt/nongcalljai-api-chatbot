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
        "elders": db["elderprofiles"].count_documents({}),
        "calls": db["callsummaries"].count_documents({}),
        "answers": db["callanswers"].count_documents({})
    }

# ─── ดึงข้อมูลคนไข้ตาม phone ────────────────────────────────
@app.get("/api/elder")
def get_elder(phone: str = Query(None)):
    if not phone:
        return {"error": "กรุณาส่ง phone"}
    elder = db["elderprofiles"].find_one({"phone": phone})
    if not elder:
        return {"error": "ไม่พบผู้สูงอายุเบอร์: " + phone}
    e = fix_doc(elder)
    return {
        "name": e.get("name", ""),
        "nickname": e.get("nickname", ""),
        "phone": e.get("phone", ""),
        "regCode": e.get("regCode", ""),
        "careNote": e.get("careNote", ""),
    }

# ─── helper: หา elder จาก lineUserId ────────────────────────
def get_elder_by_line(line_user_id: str):
    # lineconnections → userId
    lc = db["lineconnections"].find_one({"lineUserId": line_user_id})
    if not lc:
        return None, "ไม่พบ LINE User: " + line_user_id
    # users → familyAccountId
    user = db["users"].find_one({"_id": lc["userId"]})
    if not user:
        return None, "ไม่พบ user"
    # elderprofiles → familyAccountId
    elder = db["elderprofiles"].find_one({"familyAccountId": user["familyAccountId"]})
    if not elder:
        return None, "ไม่พบผู้สูงอายุ"
    return elder, None

# ─── ดึงรายงานสุขภาพ ─────────────────────────────────────────
@app.get("/api/report")
def get_report(
    phone: str = Query(None),
    elder_id: str = Query(None),
    line_user_id: str = Query(None)
):
    elder = None

    # กรณีส่ง line_user_id มา
    if line_user_id:
        elder, err = get_elder_by_line(line_user_id)
        if err:
            return {"error": err}

    # กรณีส่ง phone มา
    elif phone:
        elder = db["elderprofiles"].find_one({"phone": phone})
        if not elder:
            return {"error": "ไม่พบผู้สูงอายุเบอร์: " + phone}

    # กรณีส่ง elder_id มา
    elif elder_id:
        try:
            elder = db["elderprofiles"].find_one({"_id": ObjectId(elder_id)})
        except:
            return {"error": "elder_id ไม่ถูกต้อง"}
        if not elder:
            return {"error": "ไม่พบผู้สูงอายุ"}

    else:
        return {"error": "กรุณาส่ง phone, elder_id หรือ line_user_id"}

    # หา session ล่าสุด
    session = db["voicecallsessions"].find_one(
        {"elderId": elder["_id"]},
        sort=[("startedAt", -1)]
    )
    if not session:
        return {"error": "ยังไม่มีข้อมูลการโทร"}

    session_id = session["_id"]
    summary = db["callsummaries"].find_one({"callSessionId": session_id})
    answers = list(db["callanswers"].find({"callSessionId": session_id}))
    questions = {str(q["_id"]): q.get("questionKey", "") for q in db["carequestions"].find({})}

    answer_map = {}
    for a in answers:
        qid = str(a.get("questionId", ""))
        key = questions.get(qid, qid)
        val = a.get("valueText") or a.get("valueNumber") or a.get("valueBool")
        answer_map[key] = val

    return {
        "patient_name": elder.get("name", ""),
        "food_detail": answer_map.get("meal_detail", ""),
        "medicine_detail": answer_map.get("medication_detail", ""),
        "routine_detail": answer_map.get("today_activity", ""),
        "message_back": fix_doc(summary).get("caringMessage", "") if summary else "",
        "summary_status": fix_doc(summary).get("summaryText", "") if summary else "",
        "safe_note": fix_doc(summary).get("safeNote", "") if summary else "",
        "ate_food": 1 if answer_map.get("appetite") == True else 0,
        "took_medicine": 1 if answer_map.get("medication_taken") == True else 0,
        "pain_level": answer_map.get("pain_level", 0),
    }

@app.get("/api/users")
def get_users():
    return [fix_doc(u) for u in db["users"].find({}).limit(10)]

@app.get("/api/calls")
def get_calls():
    return [fix_doc(c) for c in db["callsummaries"].find({}).limit(10)]

@app.get("/api/elders")
def get_elders():
    return [fix_doc(e) for e in db["elderprofiles"].find({}).limit(10)]

@app.post("/api/saveLog")
def save_log(body: dict):
    body["createdAt"] = datetime.now().isoformat()
    result = db["callsummaries"].insert_one(body)
    return {"success": True, "id": str(result.inserted_id)}

@app.post("/api/saveMessage")
def save_message(body: dict):
    session_id = body.get("session_id")
    message = body.get("message")
    if not session_id or not message:
        return {"error": "กรุณาส่ง session_id และ message"}
    db["callsummaries"].update_one(
        {"callSessionId": session_id},
        {"$set": {"caringMessage": message}}
    )
    return {"success": True}
