from datetime import date
from .models import RequestLog

class SourceTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        agent = request.META.get("HTTP_USER_AGENT", "").lower()
        ip = request.META.get("REMOTE_ADDR", "")
        today = date.today()

        # detect device type
        if "android" in agent:
            source = "Android"
        elif "esp32" in agent:
            source = "ESP32"
        elif "iphone" in agent or "ios" in agent:
            source = "iOS"
        elif "mozilla" in agent or "chrome" in agent or "safari" in agent:
            source = "Browser"
        else:
            source = "Other"

        # check if already counted today
        exists = RequestLog.objects.filter(
            ip=ip,
            source=source,
            date=today
        ).exists()

        # only log once per day per device
        if not exists:
            RequestLog.objects.create(
                source=source,
                ip=ip,
                user_agent=agent,
                date=today
            )

        return self.get_response(request)
