#!/bin/bash

# 更新包列表
sudo apt-get update
# 安装依赖
sudo apt-get install -y python3 python3-requests python3-gi python3-dbus python3-jieba

# 创建目录 /home/forward/
mkdir -p /home/forward/
# 进入目录 /home/forward/
cd /home/forward/

# 克隆 GitHub 仓库中的安装脚本和服务文件（下载压缩包）
curl -L https://github.com/f1owkang/SMS_forwarder/archive/refs/heads/main.zip -o smsforwarder.zip
# 解压 ZIP 文件
unzip smsforwarder.zip

# 删除 ZIP 文件
rm smsforwarder.zip
# 将解压的内容移到上一级目录并删除空目录
mv SMS_forwarder-main/* .
rmdir SMS_forwarder-main

# 将服务文件复制到 systemd 服务目录
cp /home/forward/smsforwarder.service /etc/systemd/system/

echo "安装 SMS 转发服务成功！请配置/home/forward/config.json然后启动服务。"
