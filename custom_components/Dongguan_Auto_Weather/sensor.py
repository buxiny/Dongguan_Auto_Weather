import logging
import voluptuous as vol
from datetime import timedelta
from bs4 import BeautifulSoup
import requests

from homeassistant.components.sensor import SensorEntity, PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

DOMAIN = "dongguan_weather"
SCAN_INTERVAL = timedelta(minutes=3)    # 每3分钟更新

STATION_MAPPING = {
    "麻涌海心沙": "mayong_haixinsha",
    "麻涌镇大步村委": "mayong_dabu",
    "望牛墩官洲水闸": "wangniudun_gzshuizha"
}

URL = "http://120.197.146.91/Mobile/Monitor"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.6943.98'
}

# 平台模式需要PLATFORM_SCHEMA
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({})

def setup_platform(hass, config, add_entities, discovery_info=None):
    """设置传感器平台"""
    sensors = []
    for chinese_name, english_name in STATION_MAPPING.items():
        sensors.append(DGFXSensor(chinese_name, english_name, "wd2dd"))
        sensors.append(DGFXSensor(chinese_name, english_name, "t"))
    add_entities(sensors, True)

class DGFXSensor(SensorEntity):
    """自定义传感器实体"""
    def __init__(self, chinese_name, english_name, sensor_type):
        self._chinese_name = chinese_name
        self._english_name = english_name
        self._sensor_type = sensor_type
        self._attr_name = f"{chinese_name} {'风向角度' if sensor_type == 'wd2dd' else '气温'}"
        self._attr_unique_id = f"{english_name}_{sensor_type}"
        self._attr_icon = "mdi:compass" if sensor_type == "wd2dd" else "mdi:thermometer"
        self._attr_native_unit_of_measurement = "°" if sensor_type == "wd2dd" else "°C"
        self._state = None

    def update(self):
        """从目标网站抓取数据"""
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
        
            # 提取数据
            if self._sensor_type == "wd2dd":
                value_start = script_content.find('"Wd2dd":', start_index) + len('"Wd2dd":')
            else:
                value_start = script_content.find('"T":', start_index) + len('"T":')
        
            value_end = script_content.find(',', value_start)
            value = script_content[value_start:value_end].strip()
            if ".0" in value:
                value = value.split(".0")[0]

            self._attr_native_value = value

        except Exception as e:
            _LOGGER.error(f"更新传感器时出错: {str(e)}")
            self._attr_native_value = None
