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
curl -L https://github.com/f1owkang/SMS_forwarder/archive/refs/heads/master.zip -o smsforwarder.zip
# 解压 ZIP 文件
unzip smsforwarder.zip

# 删除 ZIP 文件
rm smsforwarder.zip
# 将解压的内容移到上一级目录并删除空目录
mv SMS_forwarder-main/* .
rmdir SMS_forwarder-main

# 给安装脚本添加执行权限
chmod +x ./install_smsforwarder.sh

# 运行安装脚本
./install_smsforwarder.sh

# 将服务文件复制到 systemd 服务目录
cp /home/forward/smsforwarder.service /etc/systemd/system/
# 等待 1 秒
sleep 1
# 启动服务
sudo systemctl start smsforwarder
# 设置服务开机自启
sudo systemctl enable smsforwarder

echo "安装并启动 SMS 转发服务成功！"
