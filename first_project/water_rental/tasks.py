from celery import shared_task
from .models import SensorData, Customer, WaterUsage, Recharge, Payment
from django.utils import timezone
from django.utils.timezone import make_aware
from datetime import datetime, date, timedelta
import logging
import random
#xyz
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


def update_water_usage_for_customer(customer, sensor_data_objects):
    """
    Manually update WaterUsage records for a customer after bulk sensor data insertion.
    This replicates the logic from the post_save signal.
    """
    from django.utils import timezone
    from django.db.models import Sum
    from datetime import date

    # Process each sensor data object
    for sensor_data in sensor_data_objects:
        # Normalize to local timezone so "today" matches dashboards
        local_timestamp = timezone.localtime(sensor_data.esp_timestamp)
        today = local_timestamp.date()
        start_of_day = local_timestamp.replace(hour=0, minute=0, second=0, microsecond=0)

        # Get or create usage record for today
        usage, was_created = WaterUsage.objects.get_or_create(
            customer=customer,
            usage_date=today,
            defaults={
                'current_day_usage': 0,
                'last_24hr_usage': 0,
                'monthly_usage': 0,
                'per_day_average': 0
            }
        )

        # Determine litres represented by this reading
        previous_reading = SensorData.objects.filter(
            customer=customer,
            esp_timestamp__lt=sensor_data.esp_timestamp
        ).order_by('-esp_timestamp').first()
        delta_usage = _flow_delta(sensor_data, previous_reading)

        # Deduct only the delta from recharge
        if delta_usage > 0:
            try:
                from water_rental.utils import deduct_from_recharge
                deduct_from_recharge(customer, delta_usage)
            except Exception as exc:
                logger.warning("Failed to deduct recharge usage: %s", exc)

        usage.current_day_usage = (usage.current_day_usage or 0) + delta_usage

        # Recompute last 24 hours usage by summing deltas in the window
        window_start = sensor_data.esp_timestamp - timezone.timedelta(hours=24)
        prev_before_window = SensorData.objects.filter(
            customer=customer,
            esp_timestamp__lt=window_start
        ).order_by('-esp_timestamp').first()
        last_24h_total = 0
        previous_window_reading = prev_before_window
        for reading in SensorData.objects.filter(
            customer=customer,
            esp_timestamp__gte=window_start
        ).order_by('esp_timestamp'):
            last_24h_total += _flow_delta(reading, previous_window_reading)
            previous_window_reading = reading
        usage.last_24hr_usage = last_24h_total

        # Calculate monthly usage and per-day average
        month_start = today.replace(day=1)
        monthly_total = WaterUsage.objects.filter(
            customer=customer,
            usage_date__gte=month_start,
            usage_date__lte=today
        ).exclude(pk=usage.pk).aggregate(total=Sum('current_day_usage'))['total'] or 0
        usage.monthly_usage = monthly_total + usage.current_day_usage
        days_in_month = (today - month_start).days + 1
        usage.per_day_average = usage.monthly_usage / days_in_month if days_in_month > 0 else usage.monthly_usage

        usage.save()


def safe_float(val):
    try:
        return float(val)
    except Exception:
        return 0.0


def parse_esp_ts(ts):
    """
    Accepts:
    - unix timestamp (int / str)
    - datetime object
    Returns timezone-aware datetime
    """
    from django.utils.timezone import make_aware, is_aware

    # Case 1: already datetime
    if isinstance(ts, datetime):
        return ts if is_aware(ts) else make_aware(ts)

    # Case 2: unix timestamp (ESP)
    return make_aware(datetime.fromtimestamp(int(ts)))


@shared_task(bind=True)
def save_sensor_batch(self, uid, sensor_list):
    print("[CELERY] save_sensor_batch called")
    print("[CELERY] UID =", uid)

    try:
        customer = Customer.objects.get(id=uid, is_active=True, block_unblock=True)
    except Customer.DoesNotExist:
        print("[CELERY] Customer not found for UID")
        return

    objs = []
    latest_health = "Good"  # Default value
    for item in sensor_list:
        latest_health = item.get("system_health", "Good")  # Capture latest health
        objs.append(
            SensorData(
                customer=customer,
                esp_timestamp=parse_esp_ts(item["esp_timestamp"]),
                total_volume=float(item["total_volume"]),
                current_volume=float(item["current_volume"]),
                water_quality=item["water_quality"],
                tds=float(item["tds"]),
                ph=float(item["ph"]),
                device_health=item["system_health"],
            )
        )

    # Bulk create the sensor data
    created_objects = SensorData.objects.bulk_create(objs)
    print(f"[CELERY] Inserted {len(objs)} rows")

    from django.utils import timezone as django_tz
    Customer.objects.filter(id=uid).update(
        device_status='online',
        device_health=latest_health,
        last_seen=django_tz.now()
    )
    print(f"[CELERY] Updated customer device_status=online, device_health={latest_health}")

    # Manually trigger WaterUsage updates since bulk_create doesn't trigger post_save signals
    if created_objects:
        print("[CELERY] Updating WaterUsage records...")
        update_water_usage_for_customer(customer, created_objects)
        print("[CELERY] WaterUsage updates completed")


@shared_task(bind=True)
def save_sensor_data(self, uid, water_consumption, tds, ph):
    print("[CELERY] save_sensor_data called")
    print("[CELERY] UID =", uid)

    try:
        customer = Customer.objects.get(id=uid, is_active=True, block_unblock=True)
    except Customer.DoesNotExist:
        print("[CELERY] Customer not found for UID")
        return

    # Create sensor data object
    sensor_data = SensorData.objects.create(
        customer=customer,
        esp_timestamp=timezone.now(),
        total_volume=float(water_consumption),
        current_volume=float(water_consumption),
        water_quality='Good',  # Default value
        tds=float(tds),
        ph=float(ph),
        device_health='Good',  # Default value
    )

    print(f"[CELERY] Inserted 1 sensor data row")

    # Update WaterUsage records
    print("[CELERY] Updating WaterUsage records...")
    update_water_usage_for_customer(customer, [sensor_data])
    print("[CELERY] WaterUsage updates completed")


@shared_task(bind=True)
def process_sensor_data_task(self, target_date=None, customer_id=None):
    """
    Celery task to process real-time sensor data and calculate daily usage.
    Equivalent to the process_sensor_data management command.
    """
    from water_rental.utils import calculate_daily_usage
    from datetime import date
    import logging

    logger = logging.getLogger(__name__)

    if target_date is None:
        target_date = date.today()
    elif isinstance(target_date, str):
        from datetime import datetime
        target_date = datetime.strptime(target_date, '%Y-%m-%d').date()

    logger.info(f'Processing sensor data for date: {target_date}')

    # Get customers to process
    if customer_id:
        customers = Customer.objects.filter(id=customer_id)
        if not customers.exists():
            logger.error(f'Customer with ID {customer_id} not found')
            return {'status': 'error', 'message': f'Customer {customer_id} not found'}
    else:
        # Get all customers with sensor readings for the target date
        customer_ids = SensorData.objects.filter(
            date=target_date
        ).values_list('customer_id', flat=True).distinct()
        customers = Customer.objects.filter(id__in=customer_ids)

    if not customers.exists():
        logger.warning(f'No sensor data found for {target_date}')
        return {'status': 'success', 'message': f'No data to process for {target_date}'}

    processed_count = 0
    error_count = 0

    for customer in customers:
        try:
            usage = calculate_daily_usage(customer, target_date)
            if usage:
                processed_count += 1
                logger.info(f'Processed {customer.name}: {usage.current_day_usage:.2f}L')
            else:
                logger.warning(f'No data to process for {customer.name}')
        except Exception as e:
            error_count += 1
            logger.error(f'Error processing {customer.name}: {str(e)}')

    result = {
        'status': 'success',
        'processed': processed_count,
        'errors': error_count,
        'date': str(target_date)
    }
    logger.info(f'Processing complete: {processed_count} customers processed, {error_count} errors')
    return result


@shared_task(bind=True)
def process_recharges_task(self):
    """
    Celery task to process expired recharges and create new ones.
    Equivalent to the process_recharges management command.
    """
    import random
    from datetime import timedelta
    import logging

    logger = logging.getLogger(__name__)

    now = timezone.now()

    # Find expired recharges
    expired_recharges = Recharge.objects.filter(status='expired')
    logger.info(f"Processing {expired_recharges.count()} expired recharges...")

    processed_count = 0

    for recharge in expired_recharges:
        customer = recharge.customer

        # Check if customer already has an active recharge
        active_recharge = Recharge.objects.filter(
            customer=customer,
            status='active'
        ).first()

        if not active_recharge:
            # Create new recharge
            plan_price = random.choice([2999.00, 5999.00, 12999.00])

            new_recharge = Recharge.objects.create(
                customer=customer,
                recharge_date=now,
                litres_allocated=500.0,
                litres_used=0.0,
                litres_remaining=500.0,
                expiry_date=now + timedelta(days=30),
                status='active',
                needs_filtration=False
            )

            # Create payment record
            Payment.objects.create(
                customer=customer,
                amount=plan_price,
                recharge_date=now,
                order_id=f"ORD-{now.strftime('%Y%m%d%H%M%S')}-{customer.id:04d}",
                payment_status='completed',
                transaction_id=f"TXN{random.randint(100000000, 999999999)}"
            )

            # Update customer's last recharge date
            customer.last_recharge_date = now
            customer.save()

            logger.info(f'Renewed recharge for {customer.name} - ₹{plan_price}')
            processed_count += 1

    result = {'status': 'success', 'processed_recharges': processed_count}
    logger.info(f'Processed {processed_count} recharges!')
    return result

'''
@shared_task(bind=True)
def auto_block_expired_recharges(self):
    """
    Celery periodic task to automatically block devices when recharges expire or are exhausted.
    This task should be scheduled to run every hour (or as needed) via Celery Beat.
    
    It performs two operations:
    1. Marks recharges as 'expired' if their expiry_date has passed
    2. Blocks customers (block_unblock=False) if they have no valid recharge
    """
    now = timezone.now()
    
    # Step 1: Mark expired recharges as 'expired'
    expired_count = Recharge.objects.filter(
        status='active',
        expiry_date__lt=now
    ).update(status='expired')
    
    logger.info(f"Marked {expired_count} recharges as expired")
    
    # Step 2: Find customers with no valid recharge and block them
    # A valid recharge is: status='active', litres_remaining > 0, expiry_date > now
    customers_with_valid_recharge = Recharge.objects.filter(
        status='active',
        litres_remaining__gt=0,
        expiry_date__gt=now
    ).values_list('customer_id', flat=True)
    
    # Block customers who don't have a valid recharge and are currently unblocked
    blocked_count = Customer.objects.filter(
        is_active=True,
        block_unblock=True  # Currently unblocked
    ).exclude(
        id__in=customers_with_valid_recharge
    ).update(block_unblock=False)
    
    logger.info(f"Auto-blocked {blocked_count} customers due to expired/exhausted recharges")
    
    return {
        'status': 'success',
        'expired_recharges': expired_count,
        'blocked_customers': blocked_count,
        'timestamp': str(now)
    }
'''
import logging
from celery import shared_task
from django.utils import timezone

# Make sure to import your Recharge model here
# from .models import Recharge

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def auto_block_expired_recharges(self): 
    """
    Celery periodic task to mark expired recharges.
    This task should be scheduled to run every hour (or as needed) via Celery Beat.

    NOTE: This task only marks recharges as 'expired'. It does NOT block customer accounts.
    When a recharge expires, only the ESP device should stop working (checked via has_valid_recharge).
    Customer can still access their account to view usage, history, and make new recharges.
    Admin manual blocking (block_unblock=False) is the only way to fully block customer + ESP.
    """
    now = timezone.now()

    # Mark expired recharges as 'expired' 
    expired_count = Recharge.objects.filter(
        status='active', 
        expiry_date__lt=now  # Fixed: changed 'lt=now' to 'expiry_date__lt=now'
    ).update(status='expired')
    
    logger.info(f"Marked {expired_count} recharges as expired") 
    
    # NOTE: We intentionally DO NOT block customers here.
    # ESP devices check has_valid_recharge to decide whether to allow water flow. 
    # Customers should still be able to access their account to recharge.

    return {
        'status': 'success', 
        'expired_recharges': expired_count, 
        'timestamp': str(now)
    }

@shared_task(bind=True)
def archive_sensor_data_task(self, days_to_keep=90):
    """
    Celery task to archive old sensor data.
    Equivalent to the archive_sensor_data management command.
    """
    from datetime import date, timedelta
    from water_rental.performance_utils import archive_old_sensor_data
    import logging

    logger = logging.getLogger(__name__)

    cutoff_date = date.today() - timedelta(days=days_to_keep)
    logger.info(f'Archiving sensor data older than {cutoff_date} (keeping {days_to_keep} days)')

    # Count records to be archived
    old_records = SensorData.objects.filter(date__lt=cutoff_date)
    count = old_records.count()

    if count == 0:
        logger.info('No old records to archive. Database is clean!')
        return {'status': 'success', 'archived': 0, 'message': 'No records to archive'}

    # Perform archiving
    logger.info(f'Archiving {count:,} records...')
    archived_count = archive_old_sensor_data(days_to_keep)

    result = {
        'status': 'success',
        'archived': archived_count,
        'cutoff_date': str(cutoff_date)
    }
    logger.info(f'Successfully archived {archived_count:,} records')
    return result


@shared_task(bind=True)
def mark_devices_offline_task(self):
    """
    Celery task to mark devices offline if they haven't sent data in 24 hours.
    Equivalent to the mark_devices_offline management command.
    """
    import logging

    logger = logging.getLogger(__name__)

    cutoff = timezone.now() - timezone.timedelta(hours=24)
    updated = Customer.objects.filter(last_seen__lt=cutoff).update(device_status='offline')

    result = {'status': 'success', 'devices_marked_offline': updated}
    logger.info(f"Marked {updated} devices offline (no data in >24h)")
    return result


@shared_task(bind=True)
def update_water_usage_task(self, customer_id, sensor_data_id):
    """
    Celery task to update WaterUsage records when new sensor data arrives.
    Triggered by post_save signal on SensorData.
    """
    try:
        customer = Customer.objects.get(id=customer_id)
        sensor_data = SensorData.objects.get(id=sensor_data_id)
    except (Customer.DoesNotExist, SensorData.DoesNotExist):
        logger.error(f"Customer {customer_id} or SensorData {sensor_data_id} not found")
        return

    # Use the UTC date from the sensor timestamp to determine the usage date
    usage_date = sensor_data.esp_timestamp.date()

    # Get or create usage record for the date of the sensor reading
    usage, was_created = WaterUsage.objects.get_or_create(
        customer=customer,
        usage_date=usage_date,
        defaults={
            'current_day_usage': 0,
            'last_24hr_usage': 0,
            'monthly_usage': 0,
            'per_day_average': 0
        }
    )

    # Determine litres represented by this reading
    previous_reading = SensorData.objects.filter(
        customer=customer,
        esp_timestamp__lt=sensor_data.esp_timestamp
    ).order_by('-esp_timestamp').first()
    delta_usage = _flow_delta(sensor_data, previous_reading)

    # Deduct only the delta from recharge
    if delta_usage > 0:
        try:
            from water_rental.utils import deduct_from_recharge
            deduct_from_recharge(customer, delta_usage)
        except Exception as exc:
            logger.warning("Failed to deduct recharge usage: %s", exc)

    usage.current_day_usage = (usage.current_day_usage or 0) + delta_usage

    # Recompute last 24 hours usage by summing deltas in the window
    window_start = sensor_data.esp_timestamp - timezone.timedelta(hours=24)
    prev_before_window = SensorData.objects.filter(
        customer=customer,
        esp_timestamp__lt=window_start
    ).order_by('-esp_timestamp').first()
    last_24h_total = 0
    previous_window_reading = prev_before_window
    for reading in SensorData.objects.filter(
        customer=customer,
        esp_timestamp__gte=window_start
    ).order_by('esp_timestamp'):
        last_24h_total += _flow_delta(reading, previous_window_reading)
        previous_window_reading = reading
    usage.last_24hr_usage = last_24h_total

    # Calculate monthly usage and per-day average
    month_start = usage_date.replace(day=1)
    monthly_total = WaterUsage.objects.filter(
        customer=customer,
        usage_date__gte=month_start,
        usage_date__lte=usage_date
    ).exclude(pk=usage.pk).aggregate(total=Sum('current_day_usage'))['total'] or 0
    usage.monthly_usage = monthly_total + usage.current_day_usage
    days_in_month = (usage_date - month_start).days + 1
    usage.per_day_average = usage.monthly_usage / days_in_month if days_in_month > 0 else usage.monthly_usage

    usage.save()
    logger.info(f"Updated water usage for customer {customer.name}: {delta_usage:.2f}L added")
    
    
# ---- For ESP -----    
import requests
from celery import shared_task
from django.conf import settings

# Periodic task to ping all devices
@shared_task
def ping_all_devices():
    """Ping all ESP devices to check online/offline status.""" 
    
    # Imported locally to prevent circular import issues when Celery loads tasks
    from .models import Customer
    
    base_url = getattr(settings, 'DEVICE_PING_URL', None) 
    
    if not base_url:
        # Fallback: try to build from settings
        base_url = getattr(settings, 'BASE_API_URL', 'https://nubiwatersolutions.store') + '/api/esp/ping/'
        
    devices = Customer.objects.filter(is_active=True, block_unblock=True) 
    
    for device in devices:
        try:
            requests.post(
                base_url, 
                json={"device_chip_id": device.device_chip_id},
                timeout=5
            )
        except Exception as e:
            print(f"Failed to ping device {device.device_chip_id}: {e}")