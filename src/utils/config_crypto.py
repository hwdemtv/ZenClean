import base64

# 混淆密钥（仅用于防止记事本直视，非军事级加密）
_CONF_KEY = b"ZEN-MAGIC-2026"

def encrypt_config(content: str) -> bytes:
    """将明文配置加密为字节流"""
    data = content.encode('utf-8')
    # 简单的 XOR 混淆
    xor_data = bytes([data[i] ^ _CONF_KEY[i % len(_CONF_KEY)] for i in range(len(data))])
    return base64.b64encode(xor_data)

def decrypt_config(encrypted_data: bytes) -> str:
    """从字节流解密回明文配置"""
    try:
        xor_data = base64.b64decode(encrypted_data)
        data = bytes([xor_data[i] ^ _CONF_KEY[i % len(_CONF_KEY)] for i in range(len(xor_data))])
        return data.decode('utf-8')
    except Exception:
        return ""
