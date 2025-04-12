#!/bin/bash

# 停止并禁用服务
sudo systemctl stop smsforwarder
sudo systemctl disable smsforwarder

# 删除 systemd 服务文件
sudo rm -f /etc/systemd/system/smsforwarder.service

# 重新加载 systemd 配置
sudo systemctl daemon-reload

# 提示用户是否删除依赖包
read -p "是否删除安装的依赖（python3, python3-requests, python3-gi, python3-dbus, python3-jieba）？(y/n): " choice
if [ "$choice" = "y" ]; then
    # 删除已安装的依赖
    sudo apt-get remove -y python3 python3-requests python3-gi python3-dbus python3-jieba

    # 清理无用的依赖包
    sudo apt-get autoremove -y

    # 清理下载的缓存
    sudo apt-get clean

    echo "依赖包已删除！"
else
    echo "保留依赖包。"
fi
echo "卸载完成！请自行删除/home/forward/文件夹！！！"
