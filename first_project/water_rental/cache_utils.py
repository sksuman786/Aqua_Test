from django.core.cache import cache
from .models import Customer

CACHE_TTL = 3600  # 1 hour

def get_device_token(device_id):
    cache_key = f"token:{device_id}"

    try:
        token = cache.get(cache_key)
    except Exception:
        token = None

    if token:
        return token

    try:
        token = Customer.objects.values_list(
            "device_token", flat=True
        ).get(device_chip_id=device_id, is_active=True, block_unblock=True)
    except Customer.DoesNotExist:
        return None

    try:
        cache.set(cache_key, token, timeout=CACHE_TTL)
    except Exception:
        pass

    return token


def clear_device_cache(device_id):
    cache.delete(f"token:{device_id}")
    cache.delete(f"device_meta:{device_id}")


def get_device_meta(device_id):
    try:
        customer = Customer.objects.filter(
            device_chip_id=device_id,
            is_active=True
        ).only("device_chip_id", "board", "firmware_version").first()
    except Exception:
        return None

    if not customer:
        return None

    cache_key = f"device_meta:{device_id}"

    try:
        meta = cache.get(cache_key)
    except Exception:
        meta = None

    if meta:
        return meta

    meta = {
        "board": customer.board,
        "firmware_version": customer.firmware_version,
    }

    try:
        cache.set(cache_key, meta, timeout=CACHE_TTL)
    except Exception:
        pass

    return meta