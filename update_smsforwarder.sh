#!/bin/bash

# 设置安装路径
INSTALL_DIR="/home/forward"
TMP_DIR="/tmp/smsforwarder_update_tmp"

# 检查目录是否存在
if [ ! -d "$INSTALL_DIR" ]; then
    echo "目录 $INSTALL_DIR 不存在，请先安装后再执行升级。"
    exit 1
fi

# 清理临时目录
rm -rf "$TMP_DIR"
mkdir -p "$TMP_DIR"

# 下载最新代码压缩包
echo "正在下载最新版本..."
curl -L https://github.com/f1owkang/SMS_forwarder/archive/refs/heads/master.zip -o "$TMP_DIR/master.zip"

# 解压
unzip -q "$TMP_DIR/master.zip" -d "$TMP_DIR"

# 删除配置文件，防止覆盖
rm -f "$TMP_DIR/SMS_forwarder-master/config_recipients.json"

# 拷贝文件覆盖旧文件
cp -r "$TMP_DIR/SMS_forwarder-master/"* "$INSTALL_DIR/"

# 清理临时文件
rm -rf "$TMP_DIR"

echo "升级完成 ✅，原配置已保留。"
