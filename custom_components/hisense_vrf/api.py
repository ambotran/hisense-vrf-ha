"""Hisense VRF API client - with WebSocket push support."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import time
import uuid
from collections.abc import Callable

import aiohttp
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

_LOGGER = logging.getLogger(__name__)

API_AUTH = "https://auth-gateway.hijuconn.com"
API_BASE = "https://clife-eu-gateway.hijuconn.com"
WS_HOST  = "hmt-eu-mpush.hijuconn.com"

JHL_APP_KEY    = "5065088696340"
JHL_APP_SECRET = "2iuyj_X-HJcdLbzpkocZrMFDMCKqQCHGWHxe7bkTFnxJ7qfZ1p28onmFE_RUbCJo"
JHL_CLIENT_ID  = "td0010010000"
SALT           = "D9519A4B756946F081B7BB5B5E8D1197"

RSA_SIGN_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAyyWrNG6q475HIHu7sMVu
vHof6vlgPeixmxa4EL/UsvVvHPz33NnWoQetQqit9TBNzUjMXw0KlY9PXM4iqHUU
U+dSyNDq1jZWIiJ2C2FccppswJtIKL3NRMFvT9PFh6NlP/4FUcQKojgKFbF7Kacc
JPKYHlwaO7qgoIjLxAHlSOXGpucJcOkPzT2EqsSVnW8sn8kenvNmghXDayhgxsh6
AyxK4kehJplEnmX/iYCfNoFXknGcLqFWYccgBz3fybvx30C/0IgU1980L8QsUAv5
esZmN8ugnbRgLRxKRlkQQLxQAiZMZdKTAx665YflT3YMHJvEFE8c2XFgoxHzSMc4
BwIDAQAB
-----END PUBLIC KEY-----"""
RSA_PWD_KEY_B64 = "MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBAL1pyw5RThDowxOMDeV/p5vY3f8o5hgthurwD9Ybby5OVQl3gyHLPie4j6HVmDCMypWbGt94LvpYtVW3ZDVIAc0CAwEAAQ=="


def _rand():
    return hashlib.md5(f"{uuid.uuid4()}{int(time.time()*1000)}".encode()).hexdigest()

def _timezone():
    return str(-time.timezone // 3600)

def _rsa_sign(data):
    key = RSA.import_key(RSA_SIGN_KEY)
    return base64.b64encode(PKCS1_v1_5.new(key).encrypt(data)).decode().replace("\n","").rstrip("=")

def _rsa_pwd(data):
    key = RSA.import_key(base64.b64decode(RSA_PWD_KEY_B64))
    return base64.b64encode(PKCS1_v1_5.new(key).encrypt(data)).decode()

def _encode_password(password):
    return _rsa_pwd(hashlib.md5(password.encode()).hexdigest().upper().encode())

def _sign(params):
    filtered = {k: v for k, v in params.items() if v and v != "[]"}
    query = "&".join(f"{k}={v}" for k, v in sorted(filtered.items())) + SALT
    return _rsa_sign(hashlib.sha256(query.encode()).digest())

def _params(token, extra=None):
    p = {"accessToken": token, "version": "5.0",
         "timeStamp": str(int(time.time()*1000)), "languageId": "1",
         "timezone": _timezone(), "randStr": _rand()}
    if extra:
        p.update(extra)
    p["sign"] = _sign(p)
    return p

def _body_with_arrays(token, arrays):
    head = {"accessToken": token, "version": "5.0",
            "timeStamp": str(int(time.time()*1000)), "languageId": "1",
            "timezone": _timezone(), "randStr": _rand()}
    sign_map = dict(head)
    for k, v in arrays.items():
        sign_map[k] = json.dumps(v, separators=(",", ":"))
    sign_map["sign"] = _sign(sign_map)
    body = dict(sign_map)
    for k, v in arrays.items():
        body[k] = v
    return body


class HisenseVRFApi:
    def __init__(self, username, password):
        self._username = username
        self._password = password
        self._access_token = ""
        self._session = None
        self._ws = None
        self._ws_task = None
        self._push_channel = ""
        self._ssl_port = "443"
        self._hb_interval = 40
        self._state_callbacks = {}

    async def _get_session(self):
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._ws_task:
            self._ws_task.cancel()
        if self._ws and not self._ws.closed:
            await self._ws.close()
        if self._session and not self._session.closed:
            await self._session.close()

    async def login(self):
        session = await self._get_session()
        lp = {"accessToken": "", "version": "5.0",
              "timeStamp": str(int(time.time()*1000)), "languageId": "1",
              "timezone": _timezone(), "randStr": _rand(),
              "loginName": self._username,
              "password": _encode_password(self._password),
              "appId": JHL_APP_KEY, "appSecret": JHL_APP_SECRET,
              "sourceId": JHL_CLIENT_ID}
        lp["sign"] = _sign(lp)
        try:
            async with session.post(f"{API_AUTH}/account/acc/login_pwd",
                    json=lp, headers={"Content-Type": "application/json"}) as r:
                data = await r.json(content_type=None)
                resp = data.get("response", {})
                if resp.get("resultCode") == 0:
                    self._access_token = resp["accessToken"]
                    return True
                _LOGGER.error("Login failed: %s", resp.get("errorDesc"))
        except Exception as e:
            _LOGGER.error("Login error: %s", e)
        return False

    async def get_homes(self):
        session = await self._get_session()
        try:
            async with session.get(f"{API_BASE}/himit-lgs/get_home_list",
                    params=_params(self._access_token)) as r:
                data = await r.json(content_type=None)
                return data.get("response", {}).get("homeList", [])
        except Exception as e:
            _LOGGER.error("get_homes error: %s", e)
        return []

    async def get_devices(self, home_id):
        session = await self._get_session()
        try:
            async with session.get(f"{API_BASE}/himit-dms/get_customer_device_list_info",
                    params=_params(self._access_token, {"homeId": home_id, "deviceType": "2"})) as r:
                data = await r.json(content_type=None)
                return data.get("response", {}).get("airconInfoList", [])
        except Exception as e:
            _LOGGER.error("get_devices error: %s", e)
        return []

    async def get_device_properties(self, devices):
        session = await self._get_session()
        device_list = [{"deviceId": d["deviceId"], "wifiId": d["wifiId"]} for d in devices]
        body = _body_with_arrays(self._access_token, {"deviceList": device_list})
        try:
            async with session.post(f"{API_BASE}/himit-dshd/getDeviceProperty",
                    json=body, headers={"Content-Type": "application/json"}) as r:
                data = await r.json(content_type=None)
                return data.get("response", {}).get("devicesProperties", []) or []
        except Exception as e:
            _LOGGER.error("get_device_properties error: %s", e)
        return []

    async def set_device_property(self, wifi_id, device_id, properties):
        session = await self._get_session()
        cmds = [{"cmdType": p["name"], "cmdValue": str(p["value"]),
                 "deviceId": device_id, "wifiId": wifi_id,
                 "haveValue": 2, "valueIds": ""} for p in properties]
        
        # String params signed as plain strings
        # Array params signed as compact JSON string
        head = {"accessToken": self._access_token, "version": "5.0",
                "timeStamp": str(int(time.time()*1000)), "languageId": "1",
                "timezone": _timezone(), "randStr": _rand()}
        
        # Build sign map: head + string params + array as JSON string
        sign_map = dict(head)
        sign_map["wifiId"] = wifi_id
        sign_map["deviceId"] = device_id
        sign_map["controlRecord"] = "1"
        sign_map["properties"] = json.dumps(cmds, separators=(",", ":"))
        sign_map["sign"] = _sign(sign_map)
        
        # Build body: head + string params + sign + actual array
        body = dict(sign_map)
        body["properties"] = cmds  # actual array not string
        
        try:
            async with session.post(f"{API_BASE}/himit-dshd/setDeviceProperty",
                    json=body, headers={"Content-Type": "application/json"}) as r:
                data = await r.json(content_type=None)
                return data.get("response", {}).get("resultCode", -1) == 0
        except Exception as e:
            _LOGGER.error("set_device_property error: %s", e)
        return False

    def register_state_callback(self, device_id, callback):
        if device_id not in self._state_callbacks:
            self._state_callbacks[device_id] = []
        self._state_callbacks[device_id].append(callback)

    async def start_websocket(self):
        session = await self._get_session()
        try:
            async with session.get(f"{API_BASE}/msg/get_msg_and_channels",
                    params=_params(self._access_token)) as r:
                data = await r.json(content_type=None)
                resp = data.get("response", {})
                if resp.get("resultCode") != 0:
                    return False
                self._push_channel = resp["pushChannels"][0]["pushChannel"]
                self._ssl_port = resp.get("pushServerSslPort", "443")
                self._hb_interval = int(resp.get("hbInterval", 40))
        except Exception as e:
            _LOGGER.error("start_websocket fetch error: %s", e)
            return False

        ws_url = (f"wss://{WS_HOST}:{self._ssl_port}/ws/{self._push_channel}"
                  f"?token={self._access_token}")
        _LOGGER.info("Connecting WebSocket: %s", ws_url[:80])
        self._ws_task = asyncio.create_task(self._ws_listen(ws_url))
        return True

    async def _ws_listen(self, url):
        session = await self._get_session()
        while True:
            try:
                async with session.ws_connect(url, heartbeat=self._hb_interval,
                        ssl=False) as ws:
                    self._ws = ws
                    _LOGGER.info("WebSocket connected")
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            await self._handle_ws_message(msg.data)
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
            except asyncio.CancelledError:
                return
            except Exception as e:
                _LOGGER.warning("WebSocket error, reconnecting in 30s: %s", e)
                await asyncio.sleep(30)

    async def _handle_ws_message(self, raw):
        try:
            try:
                decoded = base64.b64decode(raw).decode("utf-8")
            except Exception:
                decoded = raw
            msg = json.loads(decoded)
            format_id = msg.get("formatId")
    
            if format_id == 2:
                # DEVICE_STATUS - has wifiid/deviceid
                content = json.loads(msg.get("content", "{}"))
                device_id = content.get("deviceid", "")
                status_str = content.get("status", "{}")
                status = json.loads(status_str)
                if "allStatus" in status:
                    functions = json.loads(status["allStatus"])
                else:
                    functions = json.loads(status.get("status", "{}"))
                for cb in self._state_callbacks.get(device_id, []):
                    try:
                        cb(functions)
                    except Exception as e:
                        _LOGGER.error("State callback error: %s", e)
    
            elif format_id == 3:
                # SELF - no device id, apply to all registered devices
                content = json.loads(msg.get("content", "{}"))
                status_str = content.get("status", "{}")
                status = json.loads(status_str)
                if "allStatus" in status:
                    functions = json.loads(status["allStatus"])
                else:
                    functions = json.loads(status.get("status", "{}"))
                if functions:
                    for device_id, callbacks in self._state_callbacks.items():
                        for cb in callbacks:
                            try:
                                cb(functions)
                            except Exception as e:
                                _LOGGER.error("State callback error: %s", e)
    
        except Exception as e:
            _LOGGER.warning("WS parse error: %s", e)

    @property
    def access_token(self):
        return self._access_token
