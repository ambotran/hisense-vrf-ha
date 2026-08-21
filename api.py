"""Hisense VRF API client."""
from __future__ import annotations

import base64
import hashlib
import logging
import time
import uuid
from typing import Any

import aiohttp
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

from .const import (
    API_BASE_AUTH,
    API_BASE_SHADOW,
    API_BASE_DEVICE,
    API_BASE_HOME,
    APP_KEY,
    API_VERSION,
    LANGUAGE_ID,
    SALT,
    RSA_PUBLIC_KEY,
)

_LOGGER = logging.getLogger(__name__)


def _get_rand_str() -> str:
    """Generate a random string (MD5 of UUID + timestamp)."""
    raw = f"{uuid.uuid4()}{int(time.time() * 1000)}"
    return hashlib.md5(raw.encode()).hexdigest()


def _get_timezone() -> str:
    """Get timezone offset string."""
    offset = -time.timezone // 3600
    return str(offset)


def _sign(params: dict[str, str]) -> str:
    """Generate RSA signature for request parameters."""
    # Filter empty values
    filtered = {k: v for k, v in params.items() if v and v != "[]"}
    # Sort alphabetically
    sorted_params = dict(sorted(filtered.items()))
    # Build query string
    parts = [f"{k}={v}" for k, v in sorted_params.items()]
    query = "&".join(parts) + SALT
    # SHA256 hash
    sha256_hash = hashlib.sha256(query.encode()).digest()
    # RSA encrypt
    key = RSA.import_key(RSA_PUBLIC_KEY)
    cipher = PKCS1_v1_5.new(key)
    encrypted = cipher.encrypt(sha256_hash)
    # Base64 encode (no padding)
    return base64.b64encode(encrypted).decode().rstrip("=")


def _build_params(access_token: str, extra: dict[str, str] | None = None) -> dict[str, str]:
    """Build common request parameters."""
    params = {
        "accessToken": access_token,
        "apiVersion": API_VERSION,
        "timestamp": str(int(time.time() * 1000)),
        "languageId": LANGUAGE_ID,
        "timezone": _get_timezone(),
        "randStr": _get_rand_str(),
    }
    if extra:
        params.update(extra)
    params["sign"] = _sign(params)
    return params


class HisenseVRFApi:
    """Hisense VRF API client."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize the API client."""
        self._username = username
        self._password = password
        self._access_token: str = ""
        self._refresh_token: str = ""
        self._home_id: str = ""
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def login(self) -> bool:
        """Login and obtain access token."""
        session = await self._get_session()
        # RSA encrypt password using account public key
        from .const import RSA_PUBLIC_KEY
        import base64
        key = RSA.import_key(RSA_PUBLIC_KEY)
        cipher = PKCS1_v1_5.new(key)
        encrypted_pwd = base64.b64encode(
            cipher.encrypt(self._password.encode())
        ).decode()

        params = _build_params("", {
            "loginName": self._username,
            "loginPwd": encrypted_pwd,
            "loginType": "0",
        })

        try:
            async with session.post(
                f"{API_BASE_AUTH}auth/login",
                json=params,
                headers={"Content-Type": "application/json"},
            ) as resp:
                data = await resp.json(content_type=None)
                _LOGGER.debug("Login response: %s", data)

                response = data.get("response", {})
                if data.get("resultCode") == 0 or (response and response.get("resultCode") == 0):
                    token_data = response.get("data", response)
                    self._access_token = token_data.get("accessToken", "")
                    self._refresh_token = token_data.get("refreshToken", "")
                    return bool(self._access_token)
        except Exception as e:
            _LOGGER.error("Login failed: %s", e)
        return False

    async def get_homes(self) -> list[dict]:
        """Get list of homes."""
        session = await self._get_session()
        params = _build_params(self._access_token)
        try:
            async with session.get(
                f"{API_BASE_HOME}home/list",
                params=params,
            ) as resp:
                data = await resp.json(content_type=None)
                _LOGGER.debug("Homes response: %s", data)
                return data.get("response", {}).get("homeList", [])
        except Exception as e:
            _LOGGER.error("Get homes failed: %s", e)
        return []

    async def get_devices(self, home_id: str) -> list[dict]:
        """Get list of devices for a home."""
        session = await self._get_session()
        params = _build_params(self._access_token, {"homeId": home_id})
        try:
            async with session.get(
                f"{API_BASE_DEVICE}device/list",
                params=params,
            ) as resp:
                data = await resp.json(content_type=None)
                _LOGGER.debug("Devices response: %s", data)
                response = data.get("response", {})
                return response.get("deviceList", response.get("bindDeviceList", []))
        except Exception as e:
            _LOGGER.error("Get devices failed: %s", e)
        return []

    async def get_device_status(self, wifi_id: str, device_id: str) -> dict[str, str]:
        """Get current device status/properties."""
        session = await self._get_session()
        params = _build_params(self._access_token, {
            "wifiId": wifi_id,
            "deviceId": device_id,
        })
        try:
            async with session.post(
                f"{API_BASE_SHADOW}shadow/getDeviceProperty",
                json=params,
                headers={"Content-Type": "application/json"},
            ) as resp:
                data = await resp.json(content_type=None)
                _LOGGER.debug("Device status response: %s", data)
                response = data.get("response", {})
                return response.get("statusList", response.get("properties", {}))
        except Exception as e:
            _LOGGER.error("Get device status failed: %s", e)
        return {}

    async def send_command(
        self,
        wifi_id: str,
        device_id: str,
        properties: list[dict],
    ) -> bool:
        """Send control command to device."""
        session = await self._get_session()

        # Build the properties as Cmd objects
        cmds = [
            {
                "cmdType": p["name"],
                "cmdValue": str(p["value"]),
                "deviceId": device_id,
                "wifiId": wifi_id,
                "haveValue": 2,
                "valueIds": "",
            }
            for p in properties
        ]

        import json
        params = _build_params(self._access_token, {
            "wifiId": wifi_id,
            "deviceId": device_id,
            "controlRecord": "1",
            "properties": json.dumps(cmds),
        })

        try:
            async with session.post(
                f"{API_BASE_SHADOW}shadow/sendCommand",
                json=params,
                headers={"Content-Type": "application/json"},
            ) as resp:
                data = await resp.json(content_type=None)
                _LOGGER.debug("Send command response: %s", data)
                response = data.get("response", {})
                return response.get("resultCode", -1) == 0
        except Exception as e:
            _LOGGER.error("Send command failed: %s", e)
        return False

    @property
    def access_token(self) -> str:
        """Return current access token."""
        return self._access_token
