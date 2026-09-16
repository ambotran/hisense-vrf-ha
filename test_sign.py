import hashlib
import base64
import time
import uuid
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA

SALT = "D9519A4B756946F081B7BB5B5E8D1197"
RSA_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAyyWrNG6q475HIHu7sMVu
vHof6vlgPeixmxa4EL/UsvVvHPz33NnWoQetQqit9TBNzUjMXw0KlY9PXM4iqHUU
U+dSyNDq1jZWIiJ2C2FccppswJtIKL3NRMFvT9PFh6NlP/4FUcQKojgKFbF7Kacc
JPKYHlwaO7qgoIjLxAHlSOXGpucJcOkPzT2EqsSVnW8sn8kenvNmghXDayhgxsh6
AyxK4kehJplEnmX/iYCfNoFXknGcLqFWYccgBz3fybvx30C/0IgU1980L8QsUAv5
esZmN8ugnbRgLRxKRlkQQLxQAiZMZdKTAx665YflT3YMHJvEFE8c2XFgoxHzSMc4
BwIDAQAB
-----END PUBLIC KEY-----"""

def sign(params):
    filtered = {k: v for k, v in params.items() if v is not None and v != "[]"}
    sorted_params = dict(sorted(filtered.items()))
    parts = [f"{k}={v}" for k, v in sorted_params.items()]
    query = "&".join(parts) + SALT
    print(f"Signing string: {query}")
    sha256_hash = hashlib.sha256(query.encode('utf-8')).digest()
    print(f"SHA256 bytes (hex): {sha256_hash.hex()}")
    key = RSA.import_key(RSA_PUBLIC_KEY)
    cipher = PKCS1_v1_5.new(key)
    encrypted = cipher.encrypt(sha256_hash)
    result = base64.b64encode(encrypted).decode().replace('\n','').replace('\r','').rstrip('=')
    print(f"Signature: {result}")
    return result

# Test with fixed params (no timestamp/random so we can verify)
params = {
    "accessToken": "",
    "apiVersion": "5.0",
    "timestamp": "1787369133234",
    "languageId": "1",
    "timezone": "-6",
    "randStr": "b281adb184bf11c63acd3ef577b26dad",
    "loginName": "test@test.com",
    "loginPwd": "testpwd",
    "loginType": "0",
}
sign(params)
