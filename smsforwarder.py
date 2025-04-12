import dbus
import dbus.mainloop.glib
from gi.repository import GLib
import subprocess
import requests
import time
import json
import logging
import traceback
import re
import sys
import jieba
import jieba.analyse
from datetime import datetime
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
jieba.setLogLevel(20)

# ======================
# 配置路径和开关
# ======================
STOPWORDS_PATH = "/home/forward/stopwords.txt"
USERWORDS_PATH = "/home/forward/userwords.txt"
RECIPIENT_CONFIG = "/home/forward/config.json"
LOG_FILE = "/home/forward/sms_log.jsonl"
AUTO_DELETE = False

# ======================
# 日志配置（结构化JSON）
# ======================
class JSONFormatter(logging.Formatter):
    def format(self, record):
        record_dict = {
            "timestamp": self.formatTime(record, "%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "message": record.getMessage()
        }
        return json.dumps(record_dict, ensure_ascii=False)

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# 1. JSONL文件处理器（保持原有配置）
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(JSONFormatter())

# 2. 控制台输出（将被systemd捕获到journal）
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(
    '[%(levelname)s] %(message)s'  # 简化控制台格式
))

logger.addHandler(file_handler)
logger.addHandler(console_handler)

# ======================
# 类：关键词提取
# ======================
class KeywordExtractor:
    def __init__(self, stopwords_path, userdict_path=None):
        self.stopwords = set()
        with open(stopwords_path, encoding="utf-8") as f:
            for line in f:
                self.stopwords.add(line.strip())
        if userdict_path:
            jieba.load_userdict(userdict_path)

    def extract(self, text):
        code_match = re.search(r'(验证码|校验码|动态码)[^\d]{0,10}?(\d{4,6})(?=\D|$)', text, flags=re.IGNORECASE)
        if code_match:
            return f"验证码【{code_match.group(2)}】"

        def is_number(s):
            try:
                float(s)
                return True
            except ValueError:
                return False

        keywords = jieba.analyse.extract_tags(text, topK=10)
        keywords = [
            w for w in keywords
            if len(w) >= 2 and not is_number(w) and w not in self.stopwords
        ]
        return '、'.join(keywords[:4])

# ======================
# 类：短信转发
# ======================
class Forwarder:
    def __init__(self, recipients):
        self.recipients = recipients
        self.session = requests.Session()
        retry_strategy = Retry(total=2, backoff_factor=1, status_forcelist=[500, 502, 504])
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def forward(self, number, text_body, keyword, timestamp):
        results = []
        for recipient in self.recipients:
            name = recipient.get("name", recipient.get("phone_number"))
            push_token = recipient.get("pushplus_token")
            phone_number = recipient.get("phone_number")

            sent = False
            if push_token:
                try:
                    content = f"{keyword}\n\n{number}\n{text_body}\n{timestamp}"
                    res = self.session.post(
                        "https://www.pushplus.plus/send",
                        data={
                            "token": push_token,
                            "title": str(number),
                            "content": content
                        },
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=3
                    )
                    if res.status_code == 200 and res.json().get("code") == 200:
                        logging.info(f"[√] PushPlus成功: {name}")
                        results.append(f"{name} (push)")
                        sent = True
                except Exception as e:
                    logging.warning(f"[!] PushPlus失败: {name} - {e}")

            if not sent and phone_number:
                if self.send_sms(phone_number, text_body):
                    results.append(f"{name} (sms)")
                else:
                    logging.error(f"[!] 短信发送失败: {name}")
        return results

    def send_sms(self, phone_number, text_body):
        try:
            create_cmd = [
                "mmcli", "-m", "0",
                f"--messaging-create-sms=number='{phone_number}',text='{text_body}'"
            ]
            result = subprocess.run(create_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            output = result.stdout.decode(errors="ignore")
            sms_path = next((line.split("/")[-1] for line in output.splitlines() if "/SMS/" in line), None)

            if sms_path:
                send_cmd = ["mmcli", "-s", sms_path, "--send"]
                subprocess.run(send_cmd, check=True)
                logging.info(f"[√] 短信发送成功: {phone_number}")
                return True
            return False
        except Exception as e:
            logging.error(f"[!] 短信发送失败: {phone_number} - {e}")
            return False

# ======================
# 类：短信监听控制器
# ======================
class SMSController:
    def __init__(self, extractor, forwarder, auto_delete=False):
        self.extractor = extractor
        self.forwarder = forwarder
        self.auto_delete = auto_delete
        self.bus = dbus.SystemBus()
        self.loop = GLib.MainLoop()

    def start(self):
        modem = self.bus.get_object("org.freedesktop.ModemManager1", "/org/freedesktop/ModemManager1/Modem/0")
        modem.connect_to_signal("Added", self.handle_sms, dbus_interface="org.freedesktop.ModemManager1.Modem.Messaging")
        logging.info("短信监听服务已启动")
        self.loop.run()  # 确保主循环已经启动

    def handle_sms(self, sms_path, received):
        if not received:
            return
        try:
            msg = self.bus.get_object("org.freedesktop.ModemManager1", sms_path)
            props = dbus.Interface(msg, "org.freedesktop.DBus.Properties")
            data = props.GetAll("org.freedesktop.ModemManager1.Sms")

            for _ in range(3):
                if data.get('State', 99) >= 3:
                    break
                time.sleep(1.5)
                data = props.GetAll("org.freedesktop.ModemManager1.Sms")

            if data.get('State') != 3:
                logging.warning("[!] 无法读取短信内容")
                return

            number = data.get('Number', '未知号码')
            text_body = data.get('Text', '').strip()
            timestamp = data.get('Timestamp', '')
            try:
                formatted_time = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S+08:00").strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if not text_body:
                logging.warning(f"[!] 空短信内容，跳过 path: {sms_path}")
                return

            keyword = self.extractor.extract(text_body)
            results = self.forwarder.forward(number, text_body, keyword, formatted_time)

            logging.info(json.dumps({
                "number": number,
                "text": text_body,
                "timestamp": formatted_time,
                "forwarded_to": results,
                "status": "ok" if results else "failed"
            }, ensure_ascii=False))

            if self.auto_delete:
                self.delete_sms(sms_path)

        except Exception:
            logging.error("处理短信异常\n" + traceback.format_exc())

    def delete_sms(self, sms_path):
        path_str = str(sms_path).split("/")[-1]
        try:
            subprocess.run(["sudo", "mmcli", "-m", "0", f"--messaging-delete-sms={path_str}"],
                           check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            logging.info(f"[√] 已删除短信: {path_str}")
        except Exception as e:
            logging.error(f"[!] 删除短信失败: {path_str} - {e}")

# ======================
# 主启动入口
# ======================
if __name__ == "__main__":
    # 初始化D-Bus主循环（必须在创建连接前调用）
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    
    with open(RECIPIENT_CONFIG, encoding="utf-8") as f:
        recipients = json.load(f)

    extractor = KeywordExtractor(STOPWORDS_PATH, USERWORDS_PATH)
    forwarder = Forwarder(recipients)
    controller = SMSController(extractor, forwarder, auto_delete=AUTO_DELETE)
    controller.start()
