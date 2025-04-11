import dbus
import subprocess
import requests
import json
import time
from datetime import datetime
from util_keyword import extract_keyword
from util_logger import log_sms


def forward_sms(path, logging):
    try:
        bus = dbus.SystemBus()
        msg = bus.get_object("org.freedesktop.ModemManager1", path)
        props = dbus.Interface(msg, "org.freedesktop.DBus.Properties")
        data = props.GetAll("org.freedesktop.ModemManager1.Sms")

        retries = 0
        while data['State'] < 3 and retries < 3:
            time.sleep(1.5)
            data = props.GetAll("org.freedesktop.ModemManager1.Sms")
            retries += 1

        if data['State'] != 3:
            logging.error(f"[!] 短信状态异常")
            return

        number = data['Number']
        text_body = data['Text']
        timestamp = data['Timestamp']
        formatted_time = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S+08:00").strftime("%Y-%m-%d %H:%M:%S")

        keyword, alias_title = extract_keyword(text_body)
        title = alias_title or f"{number}"

        results = []
        recipients = load_recipients()
        for recipient in recipients:
            name = recipient.get("name", recipient["phone_number"])
            push_token = recipient.get("pushplus_token")
            phone_number = recipient.get("phone_number")

            if push_token:
                try:
                    content = f"{keyword}\n\n{phone_number}\n{text_body}\n{formatted_time}"
                    encoded_content = requests.utils.quote(content)
                    pushplus_url = f"http://www.pushplus.plus/send?token={push_token}&title={title}&content={encoded_content}"

                    res = requests.get(pushplus_url, timeout=5)
                    if res.status_code == 200 and res.json().get("code") == 200:
                        logging.info(f"[√] PushPlus成功: {name}")
                        results.append(f"{name} (push)")
                        continue
                except Exception as e:
                    logging.error(f"[!] PushPlus失败: {name} - {e}")

            try:
                # 创建并发送短信，更新为新格式
                sms_create_cmd = f'--messaging-create-sms="text=\'{text_body}\',number=\'{phone_number}\'"'
                result = subprocess.run(
                    ["mmcli", "-m", "0", sms_create_cmd],
                    check=True, stdout=subprocess.PIPE
                )
                sms_path = next((line.split()[-1] for line in result.stdout.decode().splitlines() if "SMS object" in line), None)
                if sms_path:
                    subprocess.run(["mmcli", "-s", sms_path, "--send"], check=True)
                    logging.info(f"[√] 短信发送: {name}")
                    results.append(f"{name} (sms)")
            except Exception as e:
                logging.error(f"[!] 短信发送失败: {name} - {e}")

        # 打印并记录日志
        logging.debug(f"短信转发结果: {number}, {text_body}, {formatted_time}, {results}")
        log_sms(number, text_body, formatted_time, results)
        
    except Exception as e:
        logging.error("处理短信异常", e)


def load_recipients():
    with open("/home/forward/config_recipients.json", "r") as f:
        return json.load(f)
