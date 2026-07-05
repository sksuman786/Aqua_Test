from django.db.models.signals import post_save, post_migrate
from django.dispatch import receiver
from django.utils import timezone
from django.core.cache import cache
import logging
from django.db.models import Sum
from water_rental.models import SensorData, WaterQualityReading, WaterUsage, Customer, Firmware
from .tasks import update_water_usage_task, mark_devices_offline_task

logger = logging.getLogger(__name__)


def _flow_delta(current_reading, previous_reading):
    """Return the positive litres between two readings (handles counter resets)."""
    current_total = current_reading.total_volume or 0
    previous_total = (previous_reading.total_volume or 0) if previous_reading else 0
    raw_delta = current_total - previous_total
    if raw_delta < 0:
        # Counter reset or reading represents per-interval litres
        raw_delta = current_total
    return max(0, raw_delta)

@receiver(post_save, sender=SensorData)
def create_water_quality_reading_from_sensor(sender, instance, created, **kwargs):
    # Only WaterQualityReading should store pH, TDS, and water_quality.
    # SensorData should not duplicate these fields.
    if created:
        # If you ever need to migrate old data, do it via a management command, not here.
        pass  # No action needed; ingestion logic should create WaterQualityReading directly.


@receiver(post_save, sender=SensorData)
def update_water_usage(sender, instance, created, **kwargs):
    """
    Automatically update WaterUsage table when new sensor data arrives
    This now triggers a Celery task to keep the operation async
    """
    if created:
        # Trigger Celery task instead of doing work synchronously
        update_water_usage_task.delay(instance.customer.id, instance.id)


@receiver(post_migrate)
def mark_stale_devices_offline(sender, **kwargs):
    """Ensure devices with old last_seen are marked offline on startup"""
    try:
        # Trigger Celery task instead of doing work synchronously
        mark_devices_offline_task.delay()
    except Exception as exc:
        logger.warning("Failed to trigger offline device marking task: %s", exc)


@receiver(post_save, sender=Firmware)
def update_customer_firmware_and_clear_cache(sender, instance, created, **kwargs):
    """
    Triggered whenever a Firmware object is saved.
    """
    # Only push update if the firmware is marked as active
    if instance.is_active:
        # 1. Bulk update the database
        # We filter by board to target only relevant devices
        affected_customers = Customer.objects.filter(board=instance.board)
        affected_customers.update(firmware_version=instance.version)

        # 2. Clear the Cache Gap
        # Since get_device_meta uses 'device_meta:{device_id}',
        # we must clear the specific key for each affected device.
        for customer in affected_customers.only("device_chip_id"):
            cache.delete(f"device_meta:{customer.device_chip_id}")


@receiver(post_save, sender=Customer)
def clear_token_cache_on_deactivate(sender, instance, **kwargs):
    if instance.is_active is False:
        cache.delete(f"token:{instance.device_chip_id}")
        cache.delete(f"device_meta:{instance.device_chip_id}")

        Customer.objects.filter(pk=instance.pk).update(device_token=None)
