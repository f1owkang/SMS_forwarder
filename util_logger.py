import json

LOG_FILE = "/home/forward/sms_log.jsonl"

def log_sms(number, text, timestamp, results):
    record = {
        "number": number,
        "text": text,
        "timestamp": timestamp,
        "forwarded_to": results,
        "status": "ok" if results else "failed"
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

def log_exception(context, error):
    print(f"[X] {context}: {error}")
