<p align="center"><img width="100" src="http://120.197.146.91/image/mobile/nav-icon11.png" ></a></p>


# 简介

从东莞气象自动站定时获取气象数据，官网约5分钟左右更新一次。

http://120.197.146.91/Mobile/Monitor

# 安装

1 手动安装，放入 /custom_components/ 目录

2 hacs安装 Custom Repositories 中填入：https://github.com/buxiny/Dongguan_Auto_Weather

# 配置

修改： configuration.yaml:

```
sensor:
  - platform: dongguan_auto_weather  # 东莞气象站实时数据（风向、温度等）
```

修改： /custom_components/dongguan_auto_weather/sensor.py

```
...

DOMAIN = "dongguan_auto_weather"
SCAN_INTERVAL = timedelta(minutes=3)    # 建议3分钟更新一次数据

# 站点名称列表，可直接增减
STATIONS = [
    "麻涌海心沙",
    "南城中心公园",
    "莞城可园"
]

...

```


