from rest_framework.throttling import SimpleRateThrottle

class DeviceRateThrottle(SimpleRateThrottle):
    scope = "device"

    def get_cache_key(self, request, view):
        try:
            device_id = request.data.get("device_id")
        except Exception:
            device_id = None

        if not device_id:
            return None  # no throttling if device_id missing

        return f"throttle_device_{device_id}"