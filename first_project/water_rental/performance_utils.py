"""
Performance utilities for handling high-volume sensor data
Optimizations for 100+ devices with thousands of data points
"""
from django.db import connection
from django.core.cache import cache
from datetime import datetime, timedelta, date
from .models import SensorData, WaterUsage, Customer
import logging

logger = logging.getLogger(__name__)


def get_database_stats():
    """
    Get database statistics for monitoring performance
    Returns table sizes and row counts
    """
    with connection.cursor() as cursor:
        # Get table sizes
        cursor.execute("""
            SELECT 
                relname as table_name,
                pg_size_pretty(pg_total_relation_size(relid)) as total_size,
                pg_size_pretty(pg_relation_size(relid)) as table_size,
                pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) as index_size
            FROM pg_catalog.pg_statio_user_tables
            WHERE relname IN ('water_rental_sensordata', 'water_rental_waterusage', 'water_rental_customer')
            ORDER BY pg_total_relation_size(relid) DESC;
        """)
        
        stats = {
            'tables': cursor.fetchall(),
            'timestamp': datetime.now()
        }
        
        # Get row counts efficiently
        stats['sensor_data_count'] = SensorData.objects.count()
        stats['customers_count'] = Customer.objects.count()
        stats['water_usage_count'] = WaterUsage.objects.count()
        
        return stats


def archive_old_sensor_data(days_to_keep=90):
    """
    Archive sensor data older than specified days
    Keeps WaterUsage summaries but removes raw sensor readings
    
    Args:
        days_to_keep: Number of days to retain (default 90)
    
    Returns:
        Number of records archived/deleted
    """
    cutoff_date = date.today() - timedelta(days=days_to_keep)
    
    # Count records to archive
    old_records = SensorData.objects.filter(date__lt=cutoff_date)
    count = old_records.count()
    
    if count > 0:
        logger.info(f"Archiving {count} sensor records older than {cutoff_date}")
        
        # Option 1: Delete (WaterUsage summaries are already saved)
        old_records.delete()
        
        # Option 2: Export to CSV before deleting (uncomment if needed)
        # export_to_csv(old_records, f'archive_{cutoff_date}.csv')
        # old_records.delete()
        
        logger.info(f"Archived {count} records")
        return count
    
    return 0


def optimize_database_indexes():
    """
    Run database maintenance commands for optimal performance
    Should be run periodically (weekly)
    """
    with connection.cursor() as cursor:
        # Analyze tables for better query planning
        cursor.execute("ANALYZE water_rental_sensordata;")
        cursor.execute("ANALYZE water_rental_waterusage;")
        cursor.execute("ANALYZE water_rental_customer;")
        
        # Vacuum to reclaim storage
        # Note: VACUUM cannot run inside a transaction block
        # Run this manually: python manage.py dbshell
        # Then: VACUUM ANALYZE water_rental_sensordata;
        
        logger.info("Database optimization completed")


def get_cached_customer_stats(customer_id, date=None):
    """
    Get customer statistics with caching for better performance
    
    Args:
        customer_id: Customer ID
        date: Date for stats (default: today)
    
    Returns:
        Dictionary with customer stats
    """
    if date is None:
        date = datetime.now().date()
    
    cache_key = f'customer_stats_{customer_id}_{date}'
    
    # Try to get from cache
    stats = cache.get(cache_key)
    
    if stats is None:
        # Calculate stats (not in cache)
        try:
            customer = Customer.objects.get(id=customer_id)
            usage = WaterUsage.objects.filter(
                customer=customer,
                usage_date=date
            ).first()
            
            stats = {
                'customer_name': customer.name,
                'device_status': customer.device_status,
                'current_day_usage': usage.current_day_usage if usage else 0,
                'last_24hr_usage': usage.last_24hr_usage if usage else 0,
                'monthly_usage': usage.monthly_usage if usage else 0,
                'days_remaining': customer.days_remaining,
            }
            
            # Cache for 5 minutes
            cache.set(cache_key, stats, 300)
            
        except Customer.DoesNotExist:
            return None
    
    return stats


def bulk_insert_sensor_data(sensor_readings):
    """
    Efficiently insert multiple sensor readings at once
    Use this for ESP32 batch uploads
    
    Args:
        sensor_readings: List of dictionaries with sensor data
        
    Example:
        readings = [
            {
                'customer_id': 1,
                'sensor_id': 'ESP32_001',
                'flow_rate': 1.5,
                'temperature': 25.0,
                'ph': 7.2,
                ...
            },
            ...
        ]
    """
    sensor_objects = []
    
    for reading in sensor_readings:
        customer_identifier = reading.get('customer_id')
        if not customer_identifier:
            logger.warning('Skipping sensor reading with missing customer identifier: %s', reading)
            continue
        customer_key = customer_identifier
        try:
            if isinstance(customer_identifier, int) or (isinstance(customer_identifier, str) and customer_identifier.isdigit()):
                customer = Customer.objects.filter(id=int(customer_identifier)).only('email').first()
                if not customer:
                    logger.warning('Skipping sensor reading; customer id %s not found', customer_identifier)
                    continue
                customer_key = customer.email
        except (ValueError, TypeError):
            pass
        sensor_objects.append(SensorData(
            customer_id=customer_key,
            sensor_id=reading['sensor_id'],
            flow_rate=reading.get('flow_rate', 0),
            total_flow=reading.get('total_flow', 0),
            temperature=reading.get('temperature'),
            ph=reading.get('ph'),
            tds=reading.get('tds'),
            turbidity=reading.get('turbidity'),
            water_quality=reading.get('water_quality'),
        ))
    
    # Bulk create - much faster than individual inserts
    SensorData.objects.bulk_create(sensor_objects, batch_size=1000)
    
    logger.info(f"Bulk inserted {len(sensor_objects)} sensor readings")
    return len(sensor_objects)


def get_query_performance_tips():
    """
    Return performance tips for database queries
    """
    return {
        'tips': [
            "Always filter by 'date' field when querying SensorData",
            "Use select_related() for foreign key relationships",
            "Use prefetch_related() for reverse relationships",
            "Aggregate at database level using Django ORM aggregation",
            "Cache frequently accessed data for 5-10 minutes",
            "Use bulk_create() for inserting multiple records",
            "Run VACUUM ANALYZE weekly on large tables",
            "Archive data older than 90 days",
            "Monitor slow queries using DEBUG logging",
        ],
        'indexed_fields': [
            'SensorData: (customer, date), (sensor_id, date), (timestamp)',
            'WaterUsage: (customer, usage_date)',
            'Customer: device_chip_id, email',
        ]
    }


def monitor_system_load():
    """
    Get system load statistics for monitoring
    """
    stats = {
        'database': get_database_stats(),
        'cache_stats': {
            'backend': cache.__class__.__name__,
        },
        'active_devices': Customer.objects.filter(device_status='online').count(),
        'total_devices': Customer.objects.count(),
        'today_readings': SensorData.objects.filter(date=date.today()).count(),
    }
    
    return stats


# Performance monitoring decorator
def track_query_time(func):
    """
    Decorator to track function execution time
    Usage: @track_query_time
    """
    def wrapper(*args, **kwargs):
        start_time = datetime.now()
        result = func(*args, **kwargs)
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        logger.info(f"{func.__name__} executed in {execution_time:.3f} seconds")
        
        if execution_time > 5:
            logger.warning(f"Slow query detected: {func.__name__} took {execution_time:.3f}s")
        
        return result
    return wrapper
