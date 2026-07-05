"""
Business Alert System for AquaGuard Rental Management
Generates alerts for admin to monitor business operations
"""
from datetime import datetime, timedelta, timezone
from django.utils import timezone as django_timezone
from django.db import connection
from .models import Customer, Recharge, Payment


class BusinessAlert:
    """Class to represent a business alert"""
    
    SEVERITY_CRITICAL = 'critical'
    SEVERITY_HIGH = 'high'
    SEVERITY_MEDIUM = 'medium'
    SEVERITY_LOW = 'low'
    
    TYPE_RECHARGE_EXPIRED = 'recharge_expired'
    TYPE_RECHARGE_EXPIRING = 'recharge_expiring'
    TYPE_WATER_LOW = 'water_low'
    TYPE_WATER_DEPLETED = 'water_depleted'
    TYPE_DEVICE_OFFLINE = 'device_offline'
    TYPE_PAYMENT_FAILED = 'payment_failed'
    TYPE_HIGH_USAGE = 'high_usage'
    TYPE_SYSTEM_BLOCKED = 'system_blocked'
    
    def __init__(self, alert_type, severity, customer, message, details=None):
        self.alert_type = alert_type
        self.severity = severity
        self.customer = customer
        self.message = message
        self.details = details or {}
        self.created_at = django_timezone.now()


def get_all_business_alerts():
    """
    Generate all current business alerts for the admin dashboard
    Returns list of BusinessAlert objects (excluding dismissed alerts)
    """
    alerts = []
    customers = Customer.objects.all()
    
    # Get all dismissed alerts - handle case where table doesn't exist yet
    dismissed_set = set()
    try:
        from .models import DismissedAlert
        dismissed = DismissedAlert.objects.values_list('customer_id', 'alert_type')
        dismissed_set = set(dismissed)
    except Exception:
        # Table doesn't exist yet (migration not run), continue without filtering
        pass
    
    for customer in customers:
        # Check recharge status
        for alert in check_recharge_alerts(customer):
            # Only add if not dismissed
            if (customer.email, alert.alert_type) not in dismissed_set:
                alerts.append(alert)
        
        # Check water remaining
        for alert in check_water_alerts(customer):
            if (customer.email, alert.alert_type) not in dismissed_set:
                alerts.append(alert)
        
        # Check device status
        for alert in check_device_alerts(customer):
            if (customer.email, alert.alert_type) not in dismissed_set:
                alerts.append(alert)
        
        # Check payment status
        for alert in check_payment_alerts(customer):
            if (customer.email, alert.alert_type) not in dismissed_set:
                alerts.append(alert)
    
    # Sort by severity (critical first)
    severity_order = {
        BusinessAlert.SEVERITY_CRITICAL: 0,
        BusinessAlert.SEVERITY_HIGH: 1,
        BusinessAlert.SEVERITY_MEDIUM: 2,
        BusinessAlert.SEVERITY_LOW: 3,
    }
    alerts.sort(key=lambda x: severity_order.get(x.severity, 4))
    
    return alerts


def check_recharge_alerts(customer):
    """Check for recharge-related alerts"""
    alerts = []
    
    # Check if recharge expired
    if customer.is_out_of_date:
        alerts.append(BusinessAlert(
            alert_type=BusinessAlert.TYPE_RECHARGE_EXPIRED,
            severity=BusinessAlert.SEVERITY_CRITICAL,
            customer=customer,
            message=f"⚠️ URGENT: {customer.name}'s recharge has EXPIRED!",
            details={
                'last_recharge': customer.last_recharge_date,
                'days_overdue': abs(customer.days_remaining) if customer.last_recharge_date else 0,
            }
        ))
    # Check if recharge expiring soon (7 days or less)
    elif customer.days_remaining <= 7 and customer.days_remaining > 0:
        alerts.append(BusinessAlert(
            alert_type=BusinessAlert.TYPE_RECHARGE_EXPIRING,
            severity=BusinessAlert.SEVERITY_HIGH,
            customer=customer,
            message=f"⏰ {customer.name}'s recharge expires in {customer.days_remaining} days",
            details={
                'days_remaining': customer.days_remaining,
                'last_recharge': customer.last_recharge_date,
            }
        ))
    
    return alerts


def check_water_alerts(customer):
    """Check for water usage/remaining alerts"""
    alerts = []
    
    # Get active recharge
    active_recharge = Recharge.objects.filter(
        customer=customer,
        status='active'
    ).first()
    
    if active_recharge:
        litres_remaining = active_recharge.litres_remaining
        
        # Water depleted (0 liters)
        if litres_remaining <= 0:
            alerts.append(BusinessAlert(
                alert_type=BusinessAlert.TYPE_WATER_DEPLETED,
                severity=BusinessAlert.SEVERITY_CRITICAL,
                customer=customer,
                message=f"💧 {customer.name} has NO WATER remaining!",
                details={
                    'litres_used': active_recharge.litres_used,
                    'litres_allocated': active_recharge.litres_allocated,
                }
            ))
        # Water running low (less than 25 liters)
        elif litres_remaining < 25:
            alerts.append(BusinessAlert(
                alert_type=BusinessAlert.TYPE_WATER_LOW,
                severity=BusinessAlert.SEVERITY_HIGH,
                customer=customer,
                message=f"💧 {customer.name} has only {litres_remaining:.1f}L water remaining",
                details={
                    'litres_remaining': litres_remaining,
                    'litres_used': active_recharge.litres_used,
                }
            ))
        # High usage check (used more than 400L out of 500L)
        elif active_recharge.litres_used > 400:
            alerts.append(BusinessAlert(
                alert_type=BusinessAlert.TYPE_HIGH_USAGE,
                severity=BusinessAlert.SEVERITY_MEDIUM,
                customer=customer,
                message=f"📊 {customer.name} has high water usage: {active_recharge.litres_used:.1f}L used",
                details={
                    'litres_used': active_recharge.litres_used,
                    'litres_remaining': litres_remaining,
                }
            ))
    
    return alerts


def check_device_alerts(customer):
    """Check for device-related alerts"""
    alerts = []
    
    # Device offline
    if customer.device_status == 'offline':
        alerts.append(BusinessAlert(
            alert_type=BusinessAlert.TYPE_DEVICE_OFFLINE,
            severity=BusinessAlert.SEVERITY_MEDIUM,
            customer=customer,
            message=f"📡 {customer.name}'s device is OFFLINE",
            details={
                'device_chip_id': customer.device_chip_id,
            }
        ))
    
    # System blocked
    if not customer.block_unblock:
        alerts.append(BusinessAlert(
            alert_type=BusinessAlert.TYPE_SYSTEM_BLOCKED,
            severity=BusinessAlert.SEVERITY_LOW,
            customer=customer,
            message=f"🔴 {customer.name}'s system is currently BLOCKED",
            details={
                'status': 'blocked',
            }
        ))
    
    return alerts


def check_payment_alerts(customer):
    """Check for payment-related alerts"""
    alerts = []
    
    # Check for failed payments in last 30 days
    failed_payments = Payment.objects.filter(
        customer=customer,
        payment_status='failed',
        recharge_date__gte=django_timezone.now() - timedelta(days=30)
    )
    
    if failed_payments.exists():
        alerts.append(BusinessAlert(
            alert_type=BusinessAlert.TYPE_PAYMENT_FAILED,
            severity=BusinessAlert.SEVERITY_HIGH,
            customer=customer,
            message=f"💳 {customer.name} has {failed_payments.count()} failed payment(s)",
            details={
                'failed_count': failed_payments.count(),
                'latest_failure': failed_payments.first().recharge_date,
            }
        ))
    
    return alerts


def get_alert_summary():
    """Get summary statistics of alerts"""
    alerts = get_all_business_alerts()
    
    return {
        'total': len(alerts),
        'critical': len([a for a in alerts if a.severity == BusinessAlert.SEVERITY_CRITICAL]),
        'high': len([a for a in alerts if a.severity == BusinessAlert.SEVERITY_HIGH]),
        'medium': len([a for a in alerts if a.severity == BusinessAlert.SEVERITY_MEDIUM]),
        'low': len([a for a in alerts if a.severity == BusinessAlert.SEVERITY_LOW]),
        'recharge_expired': len([a for a in alerts if a.alert_type == BusinessAlert.TYPE_RECHARGE_EXPIRED]),
        'water_depleted': len([a for a in alerts if a.alert_type == BusinessAlert.TYPE_WATER_DEPLETED]),
        'device_offline': len([a for a in alerts if a.alert_type == BusinessAlert.TYPE_DEVICE_OFFLINE]),
    }
