import base64


def encode_image_to_base64(image_bytes: bytes) -> str:
    """將圖片的原始 bytes 轉成 base64 字串

    Args:
        image_bytes: 圖片的原始 bytes

    Return:
        str: base64 編碼後的字串
    """
    return base64.b64encode(image_bytes).decode("utf-8")
