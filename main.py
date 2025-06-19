from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()

# نموذج البيانات اللي التطبيق هيبعتها
class UsageData(BaseModel):
    device_id: str
    page: str
    event_type: str
    timestamp: str
    duration: int

# استقبال البيانات عند POST
@app.post("/track")
def track_usage(data: UsageData):
    with open("usage_log.txt", "a") as f:
        log = f"[{datetime.now()}] {data.device_id} | {data.event_type} | {data.page} | {data.duration}s\n"
        f.write(log)
    return {"status": "received"}
