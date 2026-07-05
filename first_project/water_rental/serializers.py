"""
Serializers for REST API
Handles data validation and transformation for all models
"""
from rest_framework import serializers
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime
from .models import (
    Customer, SensorData, WaterUsage, Recharge, Payment,
    WaterQualityReading, DismissedAlert,
    UserComplain, SubscriptionPlan
)



# Sensor Data Serializers

class SensorItemSerializer(serializers.Serializer):
    esp_timestamp = serializers.IntegerField()
    total_volume = serializers.CharField()
    current_volume = serializers.CharField()
    water_quality = serializers.CharField()
    tds = serializers.CharField()
    ph = serializers.CharField()
    system_health = serializers.CharField()

    def validate_esp_timestamp(self, value):
        # Convert ESP timestamp → aware datetime
        return timezone.make_aware(datetime.fromtimestamp(value))


class SensorDataSerializer(serializers.ModelSerializer):
    """Serializer for sensor data readings"""
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    
    class Meta:
        model = SensorData
        
        fields = [
            'id', 'customer', 'customer_name', 
            'current_volume', 'total_volume', 'ph',
            'tds', 'water_quality', 'esp_timestamp', 'created_at'
        ]
        
        #fields = '__all__'
        read_only_fields = ['id', 'esp_timestamp', 'created_at']
        
        
class SensorDataSerializerNew(serializers.ModelSerializer):
    """Serializer for sensor data readings"""
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    
    class Meta:
        model = SensorData
        
        fields = [
            'id', 'customer', 'customer_name', 
            'current_volume', 'total_volume', 'ph',
            'tds', 'water_quality', 'esp_timestamp', 'created_at'
        ]
        
        
        #fields = '__all__'
        read_only_fields = ['id', 'esp_timestamp', 'created_at']


class SensorBatchSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=32)
    ts = serializers.IntegerField()  # ESP timestamp
    signature = serializers.CharField(max_length=128)
    data = SensorItemSerializer(many=True)


class SensorDataSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=32)
    ts = serializers.IntegerField()
    signature = serializers.CharField(max_length=128)
    water_consumption = serializers.CharField()
    tds = serializers.CharField()
    ph = serializers.CharField()


class DailyConsumptionSerializer(serializers.Serializer):
    """Serializer for daily consumption query parameters"""
    uid = serializers.UUIDField()
    date = serializers.DateField()


class MonthlyConsumptionSerializer(serializers.Serializer):
    uid = serializers.UUIDField()
    year = serializers.IntegerField()
    month = serializers.IntegerField(min_value=1, max_value=12)


class SensorDataListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for sensor data lists"""
    class Meta:
        model = SensorData
        fields = [
            'id', 'current_volume', 'ph', 'water_quality', 'esp_timestamp'
        ]


# Water Usage Serializers

class WaterUsageSerializer(serializers.ModelSerializer):
    """Serializer for water usage data"""
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    
    class Meta:
        model = WaterUsage
        fields = [
            'id', 'customer', 'customer_name', 'usage_date',
            'last_24hr_usage', 'monthly_usage', 'per_day_average',
            'current_day_usage'
        ]
        read_only_fields = ['id', 'usage_date']


# Recharge & Payment Serializers

class RechargeSerializer(serializers.ModelSerializer):
    """Serializer for recharge records"""
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    is_expired = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    
    class Meta:
        model = Recharge
        fields = [
            'id', 'customer', 'customer_name', 'recharge_date',
            'litres_allocated', 'litres_used', 'litres_remaining',
            'expiry_date', 'status',
            'is_expired', 'days_until_expiry'
        ]
        read_only_fields = ['id', 'recharge_date']


class RechargeCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating recharge records"""
    class Meta:
        model = Recharge
        fields = ['customer', 'litres_allocated', 'expiry_date']


class PaymentSerializer(serializers.ModelSerializer):
    """Serializer for payment records"""
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'customer', 'customer_name', 'amount',
            'recharge_date', 'order_id', 'payment_status',
            'transaction_id'
        ]
        read_only_fields = ['id', 'recharge_date']


class PaymentCreateSerializer(serializers.ModelSerializer):
    """Serializer for initiating payments"""
    class Meta:
        model = Payment
        fields = ['customer', 'amount', 'order_id']


# Water Quality Serializers





class WaterQualityReadingSerializer(serializers.ModelSerializer):
    """Serializer for water quality readings"""
    class Meta:
        model = WaterQualityReading
        fields = [
            'id', 'customer', 'ph', 'tds', 'water_quality', 'reading_date',
            'future_field1', 'future_field2', 'future_field3', 'future_field4', 'future_field5', 'future_field6'
        ]
        read_only_fields = ['id', 'reading_date']




class DismissedAlertSerializer(serializers.ModelSerializer):
    """Serializer for dismissed alerts"""
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    dismissed_by_username = serializers.CharField(source='dismissed_by.username', read_only=True)
    
    class Meta:
        model = DismissedAlert
        fields = [
            'id', 'customer', 'customer_name', 'alert_type',
            'dismissed_by', 'dismissed_by_username', 'dismissed_at', 'notes'
        ]
        read_only_fields = ['id', 'dismissed_at']


# Statistics Serializers (for dashboard)

class DashboardStatsSerializer(serializers.Serializer):
    """Serializer for dashboard statistics"""
    total_customers = serializers.IntegerField()
    active_customers = serializers.IntegerField()
    blocked_customers = serializers.IntegerField()
    online_devices = serializers.IntegerField()
    offline_devices = serializers.IntegerField()
    total_revenue = serializers.DecimalField(max_digits=10, decimal_places=2)
    pending_payments = serializers.IntegerField()
    critical_alerts = serializers.IntegerField()
    low_balance_customers = serializers.IntegerField()


class CustomerUsageStatsSerializer(serializers.Serializer):
    """Serializer for customer usage statistics"""
    current_day_usage = serializers.FloatField()
    last_24hr_usage = serializers.FloatField()
    monthly_usage = serializers.FloatField()
    per_day_average = serializers.FloatField()
    litres_remaining = serializers.FloatField()
    days_remaining = serializers.IntegerField()


class WaterQualityStatsSerializer(serializers.Serializer):
    """Serializer for water quality statistics"""
    latest_ph = serializers.FloatField()
    latest_tds = serializers.FloatField()
    latest_turbidity = serializers.FloatField()
    latest_temperature = serializers.FloatField()
    water_quality_status = serializers.CharField()
    last_reading_time = serializers.DateTimeField()


# User Complain Serializers

class UserComplainSerializer(serializers.ModelSerializer):
    """Serializer for customer complaints"""
    days_since_complaint = serializers.ReadOnlyField()
    is_overdue = serializers.ReadOnlyField()
    assigned_person_username = serializers.CharField(source='assigned_person.username', read_only=True)
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    class Meta:
        model = UserComplain
        fields = [
            'id', 'customer', 'customer_name', 'phone_no',
            'device_id', 'problem_statement', 'priority', 'complain_date',
            'assigned_person', 'assigned_person_username', 'assigned_person_details',
            'assigned_at', 'status', 'resolution_notes', 'closed_date',
            'days_since_complaint', 'is_overdue',
            'future_field1', 'future_field2', 'future_field3', 'future_field4', 'future_field5', 'future_field6'
        ]
        read_only_fields = ['id', 'complain_date']


class UserComplainCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating complaints"""
    
    class Meta:
        model = UserComplain
        fields = [
            'phone_no', 'device_id',
            'problem_statement', 'priority', 'ticket_number',
            'future_field1', 'future_field2', 'future_field3', 'future_field4', 'future_field5', 'future_field6'
        ]
        # Removed customer from fields since it's set by the view


class UserComplainListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for complaint lists"""
    assigned_person_username = serializers.CharField(source='assigned_person.username', read_only=True)
    days_since_complaint = serializers.ReadOnlyField()
    class Meta:
        model = UserComplain
        fields = [
            'id', 'device_id', 'priority', 'status',
            'complain_date', 'assigned_person_username', 'days_since_complaint',
            'future_field1', 'future_field2', 'future_field3', 'future_field4', 'future_field5', 'future_field6'
        ]


class UserComplainCustomerSerializer(serializers.ModelSerializer):
    """Serializer for customers to retrieve their complaints"""
    customer = serializers.CharField(source='customer.name', read_only=True)
    email = serializers.CharField(source='future_field1', read_only=True)
    assigned_person = serializers.SerializerMethodField()
    
    def get_assigned_person(self, obj):
        return obj.assigned_person.username if obj.assigned_person else None
    
    class Meta:
        model = UserComplain
        fields = [
            'customer', 'phone_no', 'email', 'ticket_number', 'problem_statement', 
            'complain_date', 'priority', 'assigned_person', 'assigned_person_details', 
            'assigned_at', 'resolution_notes', 'closed_date', 'status'
        ]
        read_only_fields = fields


# ===== SUBSCRIPTION PLAN SERIALIZERS =====

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans (list view)"""
    price_per_litre = serializers.ReadOnlyField()
    paisa_per_litre = serializers.ReadOnlyField()
    customer_count = serializers.SerializerMethodField()
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'plan_name', 'description', 'price', 'litres_allocated',
            'duration_days', 'status', 'is_popular', 'price_per_litre', 
            'paisa_per_litre', 'customer_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_customer_count(self, obj):
        """Get number of customers using this plan"""
        return obj.customers.count()


class SubscriptionPlanDetailSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans (detail view)"""
    price_per_litre = serializers.ReadOnlyField()
    paisa_per_litre = serializers.ReadOnlyField()
    customer_count = serializers.SerializerMethodField()
    customers = serializers.SerializerMethodField()
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'plan_name', 'description', 'price', 'litres_allocated',
            'duration_days', 'status', 'is_popular', 'description_features',
            'price_per_litre', 'paisa_per_litre', 'customer_count', 'customers',
            'future_field1', 'future_field2', 'future_field3', 'future_field4',
            'future_field5', 'future_field6', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_customer_count(self, obj):
        """Get number of customers using this plan"""
        return obj.customers.count()
    
    def get_customers(self, obj):
        """Get list of customers using this plan"""
        customers = obj.customers.values('id', 'name', 'email', 'phone_number')
        return list(customers)


# OTA Serializers

class ProvisionDeviceSerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=32)


class CheckOTASerializer(serializers.Serializer):
    device_id = serializers.CharField(max_length=32)
    version = serializers.CharField(max_length=20)
    ts = serializers.IntegerField(min_value=0)
    signature = serializers.CharField(max_length=256)


# Android App Serializers

# Customer Registration & Login Serializers

class CustomerRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for customer registration from Android app"""
    
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'email', 'password', 'phone_number', 'device_chip_id',
            'device_status', 'last_recharge_date', 'location', 'latitude', 'longitude',
            'customer_address', 'block_unblock', 'number_of_family_members', 'ota_status',
            'fcm_token', 'board', 'firmware_version', 'last_seen', 'is_active',
            'customer_type', 'subscription_plan', 'paisa_per_litre', 'device_health',
            'device_token', 'email_verified'
        ]
        read_only_fields = ['id', 'registration_date', 'last_seen']
        extra_kwargs = {
            'password': {'write_only': True},
            'device_token': {'read_only': True},
        }
    
    def create(self, validated_data):
        """Create customer with hashed password"""
        from django.contrib.auth.hashers import make_password
        
        # Hash the password
        validated_data['password'] = make_password(validated_data['password'])
        
        # Generate device token
        # For Android app registrations, do NOT generate a device token here.
        # Device tokens are provisioned by the ESP during device provisioning.
        customer = super().create(validated_data)
        if customer.device_token:
            # Clear any accidental token that might have been set elsewhere
            customer.device_token = None
            customer.save(update_fields=["device_token"])

        return customer
    
    def validate(self, data):
        """Validate registration data based on customer type"""
        customer_type = data.get('customer_type', 'subscription')
        subscription_plan = data.get('subscription_plan')
        
        # subscription_plan is now optional during registration
        # Customers can subscribe to a plan later via a separate endpoint
        
        return data



class CustomerLoginSerializer(serializers.Serializer):
    """Serializer for customer login from Android app"""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class CustomerProfileSerializer(serializers.ModelSerializer):
    """Serializer for customer profile data returned after login"""
    
    class Meta:
        model = Customer
        fields = [
            'id', 'name', 'email', 'phone_number', 'device_chip_id',
            'device_status', 'last_recharge_date', 'location', 'latitude', 'longitude',
            'customer_address', 'block_unblock', 'number_of_family_members', 'ota_status',
            'fcm_token', 'board', 'firmware_version', 'last_seen', 'is_active',
            'customer_type', 'subscription_plan', 'paisa_per_litre', 'device_health',
            'device_token', 'email_verified', 'registration_date'
        ]
        read_only_fields = fields


class CustomerInfoSerializer(serializers.ModelSerializer):
    """Serializer for customer info API response"""
    
    class Meta:
        model = Customer
        fields = [
            'name', 'email', 'phone_number', 'registration_date', 'device_status',
            'last_recharge_date', 'customer_address', 'block_unblock', 
            'number_of_family_members', 'last_seen', 'customer_type', 
            'subscription_plan', 'paisa_per_litre'
        ]
        read_only_fields = fields


class CustomerLocationSerializer(serializers.Serializer):
    """Serializer for customer location update"""
    latitude = serializers.FloatField(required=True)
    longitude = serializers.FloatField(required=True)
    location = serializers.CharField(max_length=300, required=True)


class WaterUsageSerializer(serializers.ModelSerializer):
    """Serializer for water usage data"""
    
    class Meta:
        model = WaterUsage
        fields = [
            'customer', 'usage_date', 'last_24hr_usage', 'monthly_usage', 
            'per_day_average', 'current_day_usage'
        ]
        read_only_fields = fields


class CustomerWaterUsageSerializer(serializers.Serializer):
    """Serializer for customer water usage API response"""
    customer = serializers.CharField(source='customer.name', read_only=True)
    last_24_usage = serializers.FloatField(source='last_24hr_usage', read_only=True)
    monthly_usage = serializers.FloatField(read_only=True)
    per_day_average = serializers.FloatField(read_only=True)
    current_day_usage = serializers.FloatField(read_only=True)


class CustomerRechargeInfoSerializer(serializers.Serializer):
    """Serializer for customer recharge info API response"""
    customer = serializers.CharField(source='customer.name', read_only=True)
    recharge_date = serializers.DateTimeField(read_only=True)
    litres_allocated = serializers.FloatField(read_only=True)
    litres_used = serializers.FloatField(read_only=True)
    litres_remainning = serializers.FloatField(source='litres_remaining', read_only=True)
    expiry_date = serializers.DateTimeField(read_only=True)
    status = serializers.CharField(read_only=True)
    
    amount_paid = serializers.SerializerMethodField()
    order_id = serializers.SerializerMethodField()
    paisa_per_litre = serializers.FloatField(source='paisa_per_litre_at_purchase')
    litres_purchased = serializers.FloatField()

    def get_amount_paid(self, obj):
        if obj.payment:
            return obj.payment.amount
        return None

    def get_order_id(self, obj):
        if obj.payment:
            return obj.payment.order_id
        return None

class CustomerProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating customer profile information
    """

    class Meta:
        model = Customer
        fields = [
            'name',
            'email',
            'phone_number',
            'customer_address',
            'number_of_family_members',
            'customer_type',
            'subscription_plan',
        ]
        read_only_fields = ['email']  # Email is read-only to prevent changes
        extra_kwargs = {
            'name': {'required': False},
            'phone_number': {'required': False},
            'customer_address': {'required': False},
            'number_of_family_members': {'required': False},
            'customer_type': {'required': False},
            'subscription_plan': {'required': False},
        }

    def validate_phone_number(self, value):
        """
        Validate phone number format
        """
        if value:
            # Remove spaces and hyphens
            clean_number = value.replace(' ', '').replace('-', '')

            if not clean_number.isdigit() or len(clean_number) < 10:
                raise serializers.ValidationError("Invalid phone number format")

        return value
    

class ForgotPasswordRequestSerializer(serializers.Serializer):
    """
    Serializer for forgot password - request OTP
    """
    email = serializers.EmailField()


class ForgotPasswordVerifySerializer(serializers.Serializer):
    """
    Serializer for forgot password - verify OTP
    """
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6, min_length=6)


class ForgotPasswordResetSerializer(serializers.Serializer):
    """
    Serializer for forgot password - reset password
    """
    email = serializers.EmailField()
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match"
            })
        return data


class PaymentCreateSerializer(serializers.Serializer):
    """Serializer for creating payment records"""
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    recharge_date = serializers.DateTimeField(required=False)  # Optional, will use current time if not provided
    order_id = serializers.CharField(max_length=100, required=True)
    payment_status = serializers.ChoiceField(choices=[('completed', 'Completed'), ('pending', 'Pending'), ('failed', 'Failed')], default='completed')
    transaction_id = serializers.CharField(max_length=100, required=False, allow_blank=True)


class SubscriptionInfoSerializer(serializers.ModelSerializer):
    """Serializer for subscription plan information (public API)"""
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'plan_name', 'description', 'price', 'litres_allocated', 
            'duration_days', 'status', 'is_popular'
        ]
        read_only_fields = fields


class UserComplainCreateSerializer(serializers.Serializer):
    """Serializer for creating customer complaints"""
    phone_no = serializers.CharField(max_length=20, required=True)
    problem_statement = serializers.CharField(required=True)
    priority = serializers.ChoiceField(choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], default='medium', required=False)


# ========== ESP DEVICE SERIALIZERS ==========

class ESPBlockUnblockStatusSerializer(serializers.Serializer):
    """Serializer for ESP device block/unblock status request"""
    device_id = serializers.CharField(max_length=32, required=True)
    ts = serializers.IntegerField(required=True)  # ESP timestamp
    signature = serializers.CharField(max_length=128, required=True)
    token = serializers.CharField(max_length=255, required=True)

class ESPOTAStatusCheckSerializer(serializers.Serializer):
    """Serializer for ESP device OTA status check request"""
    device_id = serializers.CharField(max_length=32, required=True)
    ts = serializers.IntegerField(required=True)  # ESP timestamp
    signature = serializers.CharField(max_length=128, required=True)
    token = serializers.CharField(max_length=255, required=True)


class ESPSensorDataSerializer(serializers.Serializer):
    """Serializer for ESP device sensor data submission"""
    device_id = serializers.CharField(max_length=32, required=True)
    ts = serializers.IntegerField(required=True)  # ESP timestamp
    signature = serializers.CharField(max_length=128, required=True)
    token = serializers.CharField(max_length=255, required=True)
    data = SensorItemSerializer(many=True, required=True)  # Sensor data array


class ESPDeviceHealthSerializer(serializers.Serializer):
    """Serializer for ESP device health status update"""
    device_id = serializers.CharField(max_length=32, required=True)
    ts = serializers.IntegerField(required=True)  # ESP timestamp
    signature = serializers.CharField(max_length=128, required=True)
    token = serializers.CharField(max_length=255, required=True)
    health_status = serializers.CharField(max_length=50, required=True)  # Device health status


class ESPCalibrationFactorSerializer(serializers.Serializer):
    """Serializer for ESP device calibration factor request"""
    device_id = serializers.CharField(max_length=32, required=True)
    ts = serializers.IntegerField(required=True)  # ESP timestamp
    signature = serializers.CharField(max_length=128, required=True)
    token = serializers.CharField(max_length=255, required=True)


class FCMTokenSerializer(serializers.Serializer):
    """Serializer for FCM token registration/update"""
    customer_id = serializers.UUIDField(required=True)  # Customer UUID
    fcm_token = serializers.CharField(max_length=255, required=True)  # FCM registration token