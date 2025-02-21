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

DOMAIN = "dongguan_auto_weather"
SCAN_INTERVAL = timedelta(minutes=3)    # 默认3分钟更新一次数据

STATIONS = ["麻涌海心沙", "南城中心公园", "莞城可园"]   # 站点名称列表，可直接增减
URL = "http://120.197.146.91/Mobile/Monitor"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({})

def setup_platform(hass, config, add_entities, discovery_info=None):
    """设置传感器平台"""
    sensors = []
    for station_name in STATIONS:
        sensors.append(DGFXSensor(station_name, "wd2dd"))
        sensors.append(DGFXSensor(station_name, "t"))
        sensors.append(DGFXSensor(station_name, "wd2df"))  # 新增风速传感器
        sensors.append(DGFXSensor(station_name, "hourr"))  # 新增时降雨量传感器
    add_entities(sensors, True)

class DGFXSensor(SensorEntity):
    """自定义传感器实体"""

    def __init__(self, chinese_name, sensor_type):
        self._chinese_name = chinese_name
        self._sensor_type = sensor_type
        
        # 配置传感器属性
        sensor_config = {
            "wd2dd": ("风向角度", "mdi:compass", "°"),
            "t": ("气温", "mdi:thermometer", "°C"),
            "wd2df": ("风速", "mdi:weather-windy", "m/s"),
            "hourr": ("时降雨量", "mdi:weather-pouring", "mm")
        }
        
        name_part, icon, unit = sensor_config.get(sensor_type, ("未知", "mdi:alert", ""))
        
        self._attr_name = f"{chinese_name} {name_part}"
        self._attr_unique_id = f"{chinese_name}_{sensor_type}"
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit
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
            
            # 动态获取数据键名
            key_mapping = {
                "wd2dd": '"Wd2dd":',
                "t": '"T":',
                "wd2df": '"Wd2df":',
                "hourr": '"HourR":'
            }
            data_key = key_mapping.get(self._sensor_type)
            
            if not data_key:
                _LOGGER.error(f"不支持的传感器类型: {self._sensor_type}")
                return

            # 查找数据位置
            key_start = script_content.find(data_key, start_index)
            if key_start == -1:
                _LOGGER.error(f"未找到{data_key}字段")
                return
                
            value_start = key_start + len(data_key)
            value_end = script_content.find(',', value_start)
            
            # 处理最后一个字段的情况
            if value_end == -1:
                value_end = script_content.find('}', value_start)
                if value_end == -1:
                    _LOGGER.error("无法确定数据结束位置")
                    return

            # 提取并处理数值
            value = script_content[value_start:value_end].strip()
            
            # 去除可能存在的引号
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            
            # 处理整数格式
            if ".0" in value and value.split(".0")[0].isdigit():
                value = value.split(".0")[0]
            
            self._attr_native_value = value

        except Exception as e:
            _LOGGER.error(f"更新传感器时出错: {str(e)}")
            self._attr_native_value = None
