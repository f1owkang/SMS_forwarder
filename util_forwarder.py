import dbus
import json
import time
import subprocess
import requests
import traceback
from datetime import datetime
from util_keyword import extract_keyword
from util_logger import log_sms

AUTO_DELETE = False


def forward_sms(sms_path, logging):
    try:
        bus = dbus.SystemBus()
        msg = bus.get_object("org.freedesktop.ModemManager1", sms_path)
        props = dbus.Interface(msg, "org.freedesktop.DBus.Properties")
        data = props.GetAll("org.freedesktop.ModemManager1.Sms")

        retries = 0
        while data.get('State', 99) < 3 and retries < 3:
            time.sleep(1.5)
            data = props.GetAll("org.freedesktop.ModemManager1.Sms")
            retries += 1

        if data.get('State') != 3:
            logging.error("[!] 短信状态异常")
            return

        number = data.get('Number', '未知号码')
        text_body = data.get('Text', '').strip()
        timestamp = data.get('Timestamp')

        try:
            formatted_time = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S+08:00").strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            formatted_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not text_body:
            logging.warning(f"[!] 空短信内容，跳过 path: {str(sms_path)}")
            return

        keyword, alias_title = extract_keyword(text_body)
        title = alias_title or f"{number}"

        results = []
        recipients = load_recipients()
        for recipient in recipients:
            name = recipient.get("name", recipient.get("phone_number"))
            push_token = recipient.get("pushplus_token")
            phone_number = recipient.get("phone_number")

            sent = False

            # PushPlus 尝试
            if push_token:
                try:
                    content = f"{keyword}\n\n{number}\n{text_body}\n{formatted_time}"
                    pushplus_url = "https://www.pushplus.plus/send"
                    headers = {"Content-Type": "application/x-www-form-urlencoded"}
                    payload = {
                        "token": push_token,
                        "title": title,
                        "content": content
                    }

                    res = requests.post(pushplus_url, data=payload, headers=headers, timeout=5)
                    if res.status_code == 200 and res.json().get("code") == 200:
                        logging.info(f"[√] PushPlus成功: {name}")
                        results.append(f"{name} (push)")
                        sent = True
                except Exception as e:
                    logging.warning(f"[!] PushPlus失败: {name} - {e}")

            # 如果PushPlus失败则发送短信
            if not sent:
                if send_sms(phone_number, f"{text_body}", logging):
                    results.append(f"{name} (sms)")
                else:
                    logging.error(f"[!] 短信发送失败: {name}")

        logging.debug(f"短信转发结果: {number}, {text_body}, {formatted_time}, {results}")
        log_sms(number, text_body, formatted_time, results)

        if AUTO_DELETE:
            time.sleep(1)
            delete_sms(sms_path, logging)

    except Exception as e:
        logging.error("处理短信异常\n" + traceback.format_exc())


def send_sms(phone_number, text_body, logging):
    try:
        # 创建短信命令
        create_cmd = [
            "mmcli", "-m", "0",
            f"--messaging-create-sms=number='{phone_number}',text='{text_body}'"
        ]
        result = subprocess.run(create_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        output = result.stdout.decode(errors="ignore")
        lines = output.splitlines()

        # 提取 sms_path（只提取路径部分）
        sms_path = None
        for line in lines:
            if "/org/freedesktop/ModemManager1/SMS/" in line:
                sms_path = line.strip().split("/")[-1]
                break

        if sms_path:
            # 发送短信
            send_cmd = ["mmcli", "-s", sms_path, "--send"]
            subprocess.run(send_cmd, check=True)
            logging.info(f"[√] 短信发送成功: {phone_number}")
            return True
        else:
            logging.error(f"[!] 未能提取短信路径: {phone_number}")
            return False

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors='ignore') if e.stderr else "无stderr信息"
        logging.error(f"[!] ModemManager调用失败: {phone_number} - {stderr}")
        return False
    except Exception as e:
        logging.error(f"[!] 短信发送异常: {phone_number} - {e}\n{traceback.format_exc()}")
        return False


def delete_sms(sms_path, logging):
    # 确保 path 是字符串
    path_str = str(sms_path).strip().strip('"\'')
    path_str = path_str.split("/")[-1]
    try:
        subprocess.run(
            ["sudo", "mmcli", "-m", "0", f"--messaging-delete-sms={path_str}"],
            check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        logging.info(f"[√] 已删除短信: {path_str}")
    except subprocess.CalledProcessError as e:
        logging.error(f"[!] 删除失败: {path_str} - {e.stderr.decode(errors='ignore')}")
    except Exception as e:
        logging.error(f"[!] 删除短信异常: {path_str} - {e}\n{traceback.format_exc()}")


def load_recipients():
    try:
        with open("/home/forward/config_recipients.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("[!] 加载配置失败:", e)
        return []
