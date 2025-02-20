
# 简介

从东莞气象自动站定时获取气象数据（默认3分钟更新一次数据）

http://120.197.146.91/Mobile/Monitor

# 安装

1 手动安装，放入 /custom_components/ 目录

~~2 hacs安装 CUSTOM REPOSITORIES中填入：https://github.com/buxiny/Dongguan_Auto_Weather~~

# 配置

Example configuration.yaml:

```
sensor:
  - platform: dongguan_auto_weather  # 东莞气象站实时数据（风向、温度等）
```



