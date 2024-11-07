"""Support for Tibber sensors."""
from __future__ import annotations

from datetime import timedelta
import logging
from random import randrange
from typing import Any

import aiohttp

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_COUNT, CONF_NAME, CONF_SENSORS, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import PlatformNotReady
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import Throttle, dt as dt_util

from .const import DOMAIN as TIBBER_DOMAIN, MANUFACTURER
from .price_logic import PriceLogic

_LOGGER = logging.getLogger(__name__)

TIME_HOURS = str(UnitOfTime.HOURS)
ICON_CURRENCY = "mdi:currency-usd"
ICON_CHARGING = "mdi:battery-charging-outline"
SCAN_INTERVAL = timedelta(minutes=1)
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)
PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the Tibber sensor."""

    tibber_connection = hass.data[TIBBER_DOMAIN]["tibber_connection"]

    entities: list[TibberSensor] = []
    for home in tibber_connection.get_homes(only_active=False):
        try:
            await home.update_info()
        except TimeoutError as err:
            _LOGGER.error("Timeout connecting to Tibber home: %s ", err)
            raise PlatformNotReady() from err
        except aiohttp.ClientError as err:
            _LOGGER.error("Error connecting to Tibber home: %s ", err)
            raise PlatformNotReady() from err

        if home.has_active_subscription:
            entities.append(TibberSensorElPrice(home))
            if CONF_SENSORS in entry.options:
                smart_charge_sensors = [
                    SmartChargeSensor(home, data)
                    for data in entry.options[CONF_SENSORS]
                ]
                for sensor in smart_charge_sensors:
                    entities.append(sensor)

    async_add_entities(entities, True)


class TibberSensor(SensorEntity):
    """Representation of a generic Tibber sensor."""

    def __init__(self, *args, tibber_home, **kwargs):
        """Initialize the sensor."""
        super().__init__(*args, **kwargs)
        self._tibber_home = tibber_home
        self._home_name = tibber_home.info["viewer"]["home"]["appNickname"]
        if self._home_name is None:
            self._home_name = tibber_home.info["viewer"]["home"]["address"].get(
                "address1", ""
            )
        self._device_name = None
        self._model = None

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device_info of the device."""
        device_info = DeviceInfo(
            identifiers={(TIBBER_DOMAIN, self._tibber_home.home_id)},
            name=self._device_name,
            manufacturer=MANUFACTURER,
        )
        if self._model is not None:
            device_info["model"] = self._model
        return device_info


class TibberSensorElPrice(TibberSensor):
    """Representation of a Tibber sensor for el price."""

    def __init__(self, tibber_home):
        """Initialize the sensor."""
        super().__init__(tibber_home=tibber_home)
        self._last_updated = None
        self._spread_load_constant = randrange(5000)

        self._attr_available = False
        self._attr_extra_state_attributes = {
            "app_nickname": None,
            "grid_company": None,
        }
        self._attr_icon = ICON_CURRENCY
        self._attr_name = f"Electricity price {self._home_name}"
        self._attr_unique_id = self._tibber_home.home_id
        self._model = "Price Sensor"

        self._device_name = self._home_name

    async def async_update(self) -> None:
        """Get the latest data and updates the states."""
        now = dt_util.now()
        if (
            not self._tibber_home.last_data_timestamp
            or (self._tibber_home.last_data_timestamp - now).total_seconds()
            < 5 * 3600 + self._spread_load_constant
            or not self.available
        ):
            _LOGGER.debug("Asking for new data")
            await self._fetch_data()

        elif (
            self._tibber_home.current_price_total
            and self._last_updated
            and self._last_updated.hour == now.hour
            and self._tibber_home.last_data_timestamp
        ):
            return

        res = self._tibber_home.current_price_data()
        self._attr_native_value, price_level, self._last_updated, *_ = res

        self._attr_available = self._attr_native_value is not None
        self._attr_native_unit_of_measurement = self._tibber_home.price_unit

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def _fetch_data(self):
        _LOGGER.debug("Fetching data")
        try:
            await self._tibber_home.update_info_and_price_info()
        except (TimeoutError, aiohttp.ClientError):
            return
        data = self._tibber_home.info["viewer"]["home"]
        self._attr_extra_state_attributes["app_nickname"] = data["appNickname"]
        self._attr_extra_state_attributes["grid_company"] = data["meteringPointData"][
            "gridCompany"
        ]


class SmartChargeSensor(BinarySensorEntity):
    """Representation of a smart charge entity."""

    def __init__(self, tibber_home, data: dict[str, str]):
        super().__init__()
        self._tibber_home = tibber_home
        self.attrs: dict[str, Any] = {
            CONF_COUNT: data[CONF_COUNT],
            "next_hour": None,
            "next_hour_price": None,
            "done_before_hour": data[TIME_HOURS] if data[TIME_HOURS] else None,
        }

        for idx in range(int(data[CONF_COUNT])):
            if idx > 0:
                self.attrs[f"other_hour_{idx}"] = None
                self.attrs[f"other_hour_{idx}_price"] = None

        self._name = data[CONF_NAME]
        self._available = True
        self._attr_device_class = BinarySensorDeviceClass.BATTERY_CHARGING
        self._attr_is_on = False
        self._attr_icon = ICON_CHARGING
        self._price_logic = None
        self._device_name = tibber_home.info["viewer"]["home"]["appNickname"]
        self._model = "Smart Charge Sensor"

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device_info of the device."""
        device_info = DeviceInfo(
            identifiers={(TIBBER_DOMAIN, self._tibber_home.home_id)},
            name=self._device_name,
            manufacturer=MANUFACTURER,
        )
        if self._model is not None:
            device_info["model"] = self._model
        return device_info

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor."""
        return self._name

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the extra state attributes."""
        return self.attrs

    @property
    def hours(self) -> int:
        """Return number of charging hours."""
        return self.attrs[CONF_COUNT]

    async def async_update(self) -> None:
        """Update Electricity Prices, set cheapest hours, set sensor is_on attribute."""

        price_logic = PriceLogic(self._tibber_home.price_total)
        time_from = dt_util.now().replace(minute=0, second=0, microsecond=0)
        cheap_hours = price_logic.find_cheapest_hours(
            self.hours, time_from, self.attrs["done_before_hour"]
        )
        idx = 0
        for dt, price in cheap_hours:
            if idx == 0:
                self.attrs["next_hour"] = dt
                self.attrs["next_hour_price"] = price
            else:
                self.attrs[f"other_hour_{idx}"] = dt
                self.attrs[f"other_hour_{idx}_price"] = price
            idx += 1

        if self.attrs["next_hour"]:
            self._attr_is_on = self.attrs["next_hour"].hour == time_from.hour
        else:
            self._attr_is_on = False
