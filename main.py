#!/usr/bin/python3
from gi.repository import GLib
import dbus
import dbus.mainloop.glib
import signal
import sys
import logging
import multiprocessing.pool
from util_forwarder import forward_sms

loop = GLib.MainLoop()
pool = multiprocessing.pool.ThreadPool()
# 设置日志格式和级别
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # 将日志输出到标准输出
    ]
)

def sms_received_handler(sms_path, received):
    if not received:
        return
    pool.apply_async(forward_sms, args=(sms_path, logging,)) 

def sigint_handler(sig, frame):
    logging.info("🛑 正在退出...")
    pool.close()
    pool.join()
    loop.quit()

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    signal.signal(signal.SIGINT, sigint_handler)

    try:
        bus = dbus.SystemBus()
        modem = bus.get_object("org.freedesktop.ModemManager1", "/org/freedesktop/ModemManager1/Modem/0")
        modem.connect_to_signal("Added", sms_received_handler,
                                dbus_interface="org.freedesktop.ModemManager1.Modem.Messaging")
    except Exception as e:
        logging.error("初始化失败", e)
        sys.exit(1)

    logging.info("📨 短信监听启动...")
    loop.run()
