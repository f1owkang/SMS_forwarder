#!/bin/bash
# 更新包列表
sudo apt-get update
# 安装依赖
sudo apt-get install -y python3 python3-requests python3-gi python3-dbus python3-jieba
# 将服务文件复制到 systemd 服务目录
cp smsforwarder.service /etc/systemd/system/

# 等待 1 秒
sleep 1

# 启动服务
systemctl start smsforwarder
# 设置服务开机自启
systemctl enable smsforwarder
