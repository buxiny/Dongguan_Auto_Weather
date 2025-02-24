import logging
import voluptuous as vol
from datetime import timedelta
from bs4 import BeautifulSoup
import requests
import math
from collections import deque, defaultdict

from homeassistant.components.sensor import SensorEntity, PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

DOMAIN = "dongguan_auto_weather2"
SCAN_INTERVAL = timedelta(minutes=3)  # 默认3分钟更新一次数据

STATIONS = ["麻涌海心沙", "南城中心公园", "莞城可园"]   # 站点名称列表，可直接增减
URL = "http://120.197.146.91/Mobile/Monitor"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({})


def setup_platform(hass, config, add_entities, discovery_info=None):
    """设置传感器平台"""
    sensors = []
    for station_name in STATIONS:
        # 按顺序添加传感器，确保wd2dd先于wd2dd_wma
        sensors.append(DGFXSensor(station_name, "wd2dd"))
        sensors.append(DGFXSensor(station_name, "t"))
        sensors.append(DGFXSensor(station_name, "wd2df"))
        sensors.append(DGFXSensor(station_name, "hourr"))
        sensors.append(DGFXSensor(station_name, "wd2dd_wma"))
    add_entities(sensors, True)


class DGFXSensor(SensorEntity):
    """自定义传感器实体"""

    # 类变量，保存各站点的wd2dd历史数据（窗口大小4）
    wd2dd_history = defaultdict(lambda: deque(maxlen=4))

    def __init__(self, chinese_name, sensor_type):
        self._chinese_name = chinese_name
        self._sensor_type = sensor_type

        # 传感器属性配置
        sensor_config = {
            "wd2dd": ("风向角度", "mdi:compass", "°"),
            "wd2dd_wma": ("风向角度加权平均", "mdi:compass", "°"),
            "t": ("气温", "mdi:thermometer", "°C"),
            "wd2df": ("风速", "mdi:weather-windy", "m/s"),
            "hourr": ("时降雨量", "mdi:weather-pouring", "mm"),
        }

        name_part, icon, unit = sensor_config.get(
            self._sensor_type, ("未知", "mdi:alert", "")
        )

        self._attr_name = f"{chinese_name} {name_part}"
        self._attr_unique_id = f"{chinese_name}_{sensor_type}"
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
        self._attr_native_value = None

    def update(self):
        """更新传感器数据"""
        if self._sensor_type == "wd2dd_wma":
            self._calculate_wma()
            return

        # 原始数据抓取逻辑
        try:
            response = requests.get(URL, headers=HEADERS, timeout=10)
            soup = BeautifulSoup(response.text, "html.parser")
            script_tag = soup.find("script", text=lambda x: x and "WeatherData" in x)

            if not script_tag:
                _LOGGER.error("未找到气象数据脚本标签")
                return

            script_content = script_tag.string
            start_index = script_content.find(f'"StationName":"{self._chinese_name}"')

            if start_index == -1:
                _LOGGER.error(f"未找到站点 {self._chinese_name} 的数据")
                return

            # 动态获取数据键名
            key_mapping = {
                "wd2dd": '"Wd2dd":',
                "t": '"T":',
                "wd2df": '"Wd2df":',
                "hourr": '"HourR":',
            }
            data_key = key_mapping.get(self._sensor_type)

            if not data_key:
                _LOGGER.error(f"不支持的传感器类型: {self._sensor_type}")
                return

            # 提取数据值
            key_start = script_content.find(data_key, start_index)
            if key_start == -1:
                _LOGGER.error(f"未找到{data_key}字段")
                return

            value_start = key_start + len(data_key)
            value_end = script_content.find(",", value_start)
            if value_end == -1:
                value_end = script_content.find("}", value_start)
                if value_end == -1:
                    _LOGGER.error("无法确定数据结束位置")
                    return

            value = script_content[value_start:value_end].strip(' "')

            # 处理数值格式
            if ".0" in value and value.split(".0")[0].isdigit():
                value = value.split(".0")[0]

            self._attr_native_value = value

            # 特殊处理wd2dd数据：保存到历史队列
            if self._sensor_type == "wd2dd":
                try:
                    angle = float(value)
                    normalized_angle = angle % 360
                    self.wd2dd_history[self._chinese_name].append(normalized_angle)
                except (ValueError, TypeError) as e:
                    _LOGGER.error(f"角度数据格式错误: {value}, 错误: {e}")

        except Exception as e:
            _LOGGER.error(f"更新传感器时出错: {str(e)}")
            self._attr_native_value = None

    def _calculate_wma(self):
        """计算加权移动平均（考虑0°=360°）"""
        history = self.wd2dd_history[self._chinese_name]
        angles = list(history)
        if not angles:
            self._attr_native_value = None
            return

        # 计算加权矢量平均
        total_x, total_y, total_weight = 0.0, 0.0, 0.0
        for idx, angle in enumerate(angles, start=1):
            rad = math.radians(angle)
            total_x += math.cos(rad) * idx  # 权重1到n
            total_y += math.sin(rad) * idx
            total_weight += idx

        if total_weight == 0:
            self._attr_native_value = None
            return

        avg_x = total_x / total_weight
        avg_y = total_y / total_weight
        avg_rad = math.atan2(avg_y, avg_x)
        avg_angle = math.degrees(avg_rad) % 360

        self._attr_native_value = round(avg_angle, 0)  # 保留一位小数
