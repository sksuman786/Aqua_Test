# ========== OTA Utility Functions (from ota_modified) ==========
import hmac, hashlib, time
import secrets
import json
from django.utils import timezone

def generate_token():
    return secrets.token_hex(32)

def verify_signature(device_id, version, ts, signature, token):
    ts_str = str(int(ts))
    msg = f"{device_id}|{version}|{ts_str}".encode()
    expected = hmac.new(
        token.encode(),
        msg,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, signature)
"""
Utility functions for aggregating sensor data and calculating usage metrics
"""
from django.db.models import Sum, Avg, Count, Max, Min
from datetime import datetime, timedelta, date
from .models import SensorData, WaterUsage, Customer


def get_customer_by_identifier(identifier):
    """Resolve customer by numeric id or email string."""
    if not identifier:
        return None
    if isinstance(identifier, Customer):
        return identifier
    lookup = str(identifier).strip()
    if not lookup:
        return None
    customer = None
    try:
        if lookup.isdigit():
            customer = Customer.objects.filter(id=int(lookup)).first()
    except (ValueError, TypeError):
        customer = None
    if customer:
        return customer
    try:
        return Customer.objects.get(email__iexact=lookup)
    except Customer.DoesNotExist:
        return None

# OTA utility functions (from otamodified, renamed)
import hmac, hashlib, secrets

def generate_ota_token():
    return secrets.token_hex(32)


def get_device_token(device_id):
    """Get device token for a given device_id"""
    try:
        customer = Customer.objects.get(device_chip_id=device_id, is_active=True, block_unblock=True)
        return customer.device_token
    except Customer.DoesNotExist:
        return None


def verify_sensor_signature(device_id, ts, signature, token, payload):
    """
    Verify signature for sensor data using the ORIGINAL payload string from request,
    not the re-serialized version after deserialization.
    """
    # This payload is already deserialized by DRF serializer
    # We need to use the raw JSON string from the request instead
    payload_json = json.dumps(
        payload,
        separators=(",", ":"),
        sort_keys=False,  # Don't sort keys
        ensure_ascii=False
    )
    msg = f"{device_id}{ts}{payload_json}"
    expected = hmac.new(
        token.encode(),
        msg.encode(),
        hashlib.sha256
    ).hexdigest()
    print("SERVER_MSG =", msg)
    print("SERVER_SIG =", expected)
    print("CLIENT_SIG =", signature)
    return hmac.compare_digest(expected, signature)


def verify_ota_signature(device_id, version, ts, signature, token):
    ts_str = str(int(ts))
    msg = f"{device_id}|{version}|{ts_str}".encode()
    expected = hmac.new(
        token.encode(),
        msg,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def aggregate_sensor_data_by_day(customer, target_date=None):
    """
    Aggregate per-second sensor data for a specific day into daily summary.
    
    Args:
        customer: Customer object
        target_date: Date object (defaults to today)
    
    Returns:
        Dictionary with aggregated data
    """
    if target_date is None:
        target_date = date.today()
    
    # Get all sensor readings for the specified date
    daily_readings = SensorData.objects.filter(
        customer=customer,
        date=target_date
    )
    
    if not daily_readings.exists():
        return None
    
    # Aggregate the data
    aggregated = daily_readings.aggregate(
        total_readings=Count('id'),
        total_flow=Sum('total_flow'),
        avg_flow_rate=Avg('flow_rate'),
        max_flow_rate=Max('flow_rate'),
        min_flow_rate=Min('flow_rate'),
        avg_temperature=Avg('temperature'),
        avg_ph=Avg('ph'),
        avg_tds=Avg('tds'),
        first_reading=Min('timestamp'),
        last_reading=Max('timestamp'),
    )
    
    return aggregated


def calculate_daily_usage(customer, target_date=None):
    """
    Calculate and store daily water usage from sensor data.
    
    Args:
        customer: Customer object
        target_date: Date object (defaults to today)
    """
    if target_date is None:
        target_date = date.today()
    
    # Get aggregated sensor data for the day
    daily_data = aggregate_sensor_data_by_day(customer, target_date)
    
    if not daily_data:
        return None
    
    # Calculate usage metrics
    current_day_usage = daily_data['total_flow'] or 0
    
    # Calculate last 24 hours usage
    last_24hr = SensorData.objects.filter(
        customer=customer,
        timestamp__gte=datetime.now() - timedelta(hours=24)
    ).aggregate(total=Sum('total_flow'))['total'] or 0
    
    # Calculate monthly usage (current month)
    first_day_of_month = target_date.replace(day=1)
    monthly = SensorData.objects.filter(
        customer=customer,
        date__gte=first_day_of_month,
        date__lte=target_date
    ).aggregate(total=Sum('total_flow'))['total'] or 0
    
    # Calculate per day average using month-to-date data
    days_in_month = (target_date - first_day_of_month).days + 1
    per_day_avg = monthly / days_in_month if days_in_month > 0 else monthly
    
    # Create or update WaterUsage record
    usage, created = WaterUsage.objects.update_or_create(
        customer=customer,
        usage_date=target_date,
        defaults={
            'current_day_usage': current_day_usage,
            'last_24hr_usage': last_24hr,
            'monthly_usage': monthly,
            'per_day_average': per_day_avg,
        }
    )
    
    return usage


def get_sensor_data_for_date_range(customer, start_date, end_date):
    """
    Get sensor data grouped by date for a date range.
    
    Args:
        customer: Customer object
        start_date: Starting date
        end_date: Ending date
    
    Returns:
        QuerySet of sensor readings
    """
    return SensorData.objects.filter(
        customer=customer,
        esp_timestamp__date__gte=start_date,
        esp_timestamp__date__lte=end_date
    ).order_by('esp_timestamp')


def get_hourly_usage_for_day(customer, target_date=None):
    """
    Get hourly breakdown of water usage for a specific day.
    
    Args:
        customer: Customer object
        target_date: Date object (defaults to today)
    
    Returns:
        List of dictionaries with hourly data
    """
    if target_date is None:
        target_date = date.today()
    
    from django.db.models.functions import TruncHour
    
    hourly_data = SensorData.objects.filter(
        customer=customer,
        date=target_date
    ).annotate(
        hour=TruncHour('timestamp')
    ).values('hour').annotate(
        total_flow=Sum('total_flow'),
        avg_flow_rate=Avg('flow_rate'),
        reading_count=Count('id')
    ).order_by('hour')
    
    return list(hourly_data)


def simulate_sensor_reading(customer, flow_rate=0.5, temperature=25.0, ph=7.0, tds=150.0):
    """
    Create a simulated sensor reading (useful for testing).
    
    Args:
        customer: Customer object
        flow_rate: Flow rate in liters per second
        temperature: Water temperature in Celsius
        ph: pH level
        tds: Total Dissolved Solids in ppm
    
    Returns:
        Created SensorData object
    """
    # Get the last reading to calculate cumulative flow
    last_reading = SensorData.objects.filter(
        customer=customer,
        esp_timestamp__date=date.today()
    ).order_by('-esp_timestamp').first()
    import random
    # Always increment by a random value if flow_rate is not provided
    increment = flow_rate if flow_rate else random.uniform(0.5, 2.0)
    total_volume = (last_reading.total_volume if last_reading else 0) + increment
    
    # Determine water quality based on TDS
    if tds < 300:
        water_quality = "Excellent"
    elif tds < 600:
        water_quality = "Good"
    elif tds < 900:
        water_quality = "Fair"
    else:
        water_quality = "Poor"
    
    reading = SensorData.objects.create(
        customer=customer,
        esp_timestamp=timezone.now(),
        total_volume=total_volume,
        current_volume=flow_rate,
        ph=ph,
        tds=tds,
        water_quality=water_quality,
        device_health='Healthy'
    )
    
    return reading

'''
def deduct_from_recharge(customer, usage_litres):
    """
    Deduct water usage from customer's recharges using FIFO (First In First Out).
    Auto-blocks the machine when all recharges are exhausted or expired.
    
    For per_litre customers: Only checks litres_remaining (no expiry date check)
    For subscription customers: Checks both litres_remaining AND expiry_date
    """
    if usage_litres <= 0:
        return True
    
    from .models import Recharge
    from django.utils import timezone
    
    is_per_litre_customer = customer.customer_type == 'per_litre'
    
    if not is_per_litre_customer:
        # For subscription customers only: mark date-expired recharges as 'expired'
        Recharge.objects.filter(
            customer=customer,
            status='active',
            expiry_date__lt=timezone.now()
        ).update(status='expired')
    
    # Get active recharges with remaining litres
    if is_per_litre_customer:
        # Per-litre: ONLY check litres, ignore expiry date
        active_recharges = Recharge.objects.filter(
            customer=customer,
            status='active',
            litres_remaining__gt=0
        ).order_by('recharge_date')
    else:
        # Subscription: check both litres AND expiry date
        active_recharges = Recharge.objects.filter(
            customer=customer,
            status='active',
            litres_remaining__gt=0,
            expiry_date__gt=timezone.now()
        ).order_by('recharge_date')
    
    if not active_recharges.exists():
    # NOTE: We do NOT block customer account here.
    # Customer can still access their account to view usage and make new recharges. 
    # ESP will check has_valid_recharge to decide if water should flow.
        return False

    remaining_usage = usage_litres 

    for recharge in active_recharges:
        if remaining_usage <= 0: 
            break
            
        deductible = min(remaining_usage, recharge.litres_remaining) 
        recharge.litres_used += deductible
        recharge.litres_remaining = max(0, recharge.litres_allocated - recharge.litres_used)
        
        if recharge.litres_remaining <= 0: 
            recharge.status = 'expired'
            
        recharge.save() 
        remaining_usage -= deductible

    # Check if all recharges exhausted
    # NOTE: We do NOT block customer account here. ESP checks has_valid_recharge. 
    if is_per_litre_customer:
        remaining_active = Recharge.objects.filter(
            customer=customer, 
            status='active', 
            litres_remaining__gt=0  # Fixed: changed 'gt' to '__gt'
        ).exists()
    else:
        remaining_active = Recharge.objects.filter(
            customer=customer, 
            status='active', 
            litres_remaining__gt=0,         # Fixed: changed 'gt' to '__gt'
            expiry_date__gt=timezone.now()  # Fixed: changed 'gt' to '__gt'
        ).exists()

    return remaining_active
'''
def deduct_from_recharge(customer, usage_litres):
    """
    Deduct water usage from customer's recharges using FIFO (First In First Out).
    Auto-blocks the machine when all recharges are exhausted or expired.
    
    For per_litre customers: Only checks litres_remaining (no expiry date check)
    For subscription customers: Checks both litres_remaining AND expiry_date
    """
    if usage_litres <= 0:
        return True
    
    # Imported locally to prevent circular imports
    from django.utils import timezone
    from .models import Recharge
    
    is_per_litre_customer = customer.customer_type == 'per_litre'
    
    if not is_per_litre_customer:
        # For subscription customers only: mark date-expired recharges as 'expired'
        Recharge.objects.filter(
            customer=customer,
            status='active',
            expiry_date__lt=timezone.now()
        ).update(status='expired')
    
    # Get active recharges with remaining litres
    if is_per_litre_customer:
        # Per-litre: ONLY check litres, ignore expiry date
        active_recharges = Recharge.objects.filter(
            customer=customer,
            status='active',
            litres_remaining__gt=0
        ).order_by('recharge_date')
    else:
        # Subscription: check both litres AND expiry date
        active_recharges = Recharge.objects.filter(
            customer=customer,
            status='active',
            litres_remaining__gt=0,
            expiry_date__gt=timezone.now()
        ).order_by('recharge_date')
    
    if not active_recharges.exists():
        # NOTE: We do NOT block customer account here.
        # Customer can still access their account to view usage and make new recharges. 
        # ESP will check has_valid_recharge to decide if water should flow.
        return False

    remaining_usage = usage_litres 

    for recharge in active_recharges:
        if remaining_usage <= 0: 
            break
            
        deductible = min(remaining_usage, recharge.litres_remaining) 
        recharge.litres_used += deductible
        recharge.litres_remaining = max(0, recharge.litres_allocated - recharge.litres_used)
        
        if recharge.litres_remaining <= 0: 
            recharge.status = 'expired'
            
        recharge.save() 
        remaining_usage -= deductible

    # Check if all recharges exhausted
    # NOTE: We do NOT block customer account here. ESP checks has_valid_recharge. 
    if is_per_litre_customer:
        remaining_active = Recharge.objects.filter(
            customer=customer, 
            status='active', 
            litres_remaining__gt=0
        ).exists()
    else:
        remaining_active = Recharge.objects.filter(
            customer=customer, 
            status='active', 
            litres_remaining__gt=0,
            expiry_date__gt=timezone.now()
        ).exists()

    return remaining_active