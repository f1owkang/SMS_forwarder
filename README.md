# SMS Forwarder ~~智慧的~~短信转发脚本

转发随身WIFI一类的设备中ModemManager的短信到PushPlus平台。

在我的随身WIFI(帝旭410,debian 11系统中完成了测试)。

Python3脚本，比起Openstick WIKI里的那个脚本来说，这个监听dbus信号，无需设置cron，比cron接收的更快，消息延迟会低一些。

在源代码的基础上，加入了jieba进行提取关键词，验证码提取效果，推送到PushPlus中效果更好。

逻辑是优先PushPlus，失败就发送短信，注意短信消耗！目前大幅度结构化了代码。

# 使用方法

```
curl -sSL https://raw.githubusercontent.com/f1owkang/SMS_forwarder/main/script_install_online.sh | bash
```
记得安装后自行配置`config.json`文件，支持一对多转发。
修改好配置之后启动服务，让你的转发配置生效！！！
```
# 加载服务
systemctl daemon-reload
# 启动服务
systemctl start smsforwarder
# 设置服务开机自启
systemctl enable smsforwarder
```
后续要进行升级本程序的话，手动覆盖文件或者使用`script_update.sh`。

# 卸载方法

```
cd /home/forward/
sudo chmod +x ./script_uninstall.sh
sudo ./script_uninstall.sh
```

# 参考项目

- https://github.com/TeddyNight/sms_forwarder_mmcli
- https://github.com/lkiuyu/DbusSmsForward
- https://github.com/cyfrit/sms_forwarder