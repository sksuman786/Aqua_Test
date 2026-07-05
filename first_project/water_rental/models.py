from django.db import models
from django.utils import timezone
class Technician(models.Model):
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('on_leave', 'On Leave'),
    ]
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    specialization = models.CharField(max_length=100, blank=True, null=True)
    area_of_operation = models.CharField(max_length=100, blank=True, null=True)
    rating = models.FloatField(default=0)
    completed_jobs = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    is_active = models.BooleanField(default=True)
   

    def __str__(self):
        return f"{self.name} ({self.email})"
from django.db import models
# ========== OTA Firmware Model (from ota_modified) ==========
class Firmware(models.Model):
    BOARD_CHOICE = (
        ('esp8266','ESP8266'),
        ('esp32','ESP32'),
    )

    board = models.CharField(max_length = 20, choices = BOARD_CHOICE)
    version = models.CharField(max_length=20)
    bin_file = models.FileField(upload_to="firmware/")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.board} - {self.version}"
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
import uuid



class WaterQualityReading(models.Model):
    customer = models.ForeignKey(
        'Customer',
        on_delete=models.CASCADE,
        related_name='water_quality_readings',
        null=True,
        blank=True,
    )
    ph = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(14)])
    tds = models.FloatField(null=True, blank=True)  # TDS (Total Dissolved Solids) in ppm
    water_quality = models.CharField(max_length=50, null=True, blank=True)  # e.g., 'Good', 'Fair', 'Poor'
    
    # Metadata
    reading_date = models.DateTimeField(auto_now_add=True)
    
    
    # Future use fields
    future_field1 = models.CharField(max_length=255, null=True, blank=True)
    future_field2 = models.CharField(max_length=255, null=True, blank=True)
    future_field3 = models.TextField(null=True, blank=True)
    future_field4 = models.FloatField(null=True, blank=True)
    future_field5 = models.DateTimeField(null=True, blank=True)
    future_field6 = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-reading_date']
    
    def __str__(self):
        return f"{self.customer.name if self.customer else 'No Customer'} - {self.reading_date}"


# Customer Management Models

# Profile Edit Request Model
class ProfileEditRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    request_message = models.TextField(help_text="Customer's reason for requesting edit")
    requested_changes = models.JSONField(blank=True, null=True, help_text="Fields customer wants updated")
    requested_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True, null=True, help_text="Admin's notes on this request")
    processed_at = models.DateTimeField(blank=True, null=True)
    processed_by = models.CharField(max_length=255, blank=True, null=True)
    customer = models.ForeignKey(
        'Customer',
        on_delete=models.CASCADE,
        related_name='edit_requests',
    )

    class Meta:
        ordering = ['-requested_at']

    def __str__(self):
        return f"EditRequest({self.customer.name}, {self.status}, {self.requested_at})"

import uuid
class Customer(models.Model):
    CUSTOMER_TYPE_CHOICES = [
        ('subscription', 'Monthly Subscription Plan'),
        ('per_litre', 'Paisa Per Litre'),
    ]

    # UUID as primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    def generate_device_token(self):
        """Generate and persist a unique device token for hardware/App auth."""
        import secrets

        token = secrets.token_urlsafe(32)
        while self.__class__.objects.filter(device_token=token).exists():
            token = secrets.token_urlsafe(32)

        self.device_token = token
        self.save(update_fields=["device_token"])
        return token
    """Model for customer information and device details"""


    name = models.CharField(max_length=255)  # Capitalized
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128, blank=True, default='')  # Stores hashed password when available
    phone_number = models.CharField(max_length=20)
    registration_date = models.DateTimeField(auto_now_add=True)
    device_chip_id = models.CharField(max_length=100, unique=True)  # ESP32 Chip ID
    device_status = models.CharField(max_length=20, choices=[('online', 'Online'), ('offline', 'Offline')], default='offline')
    last_recharge_date = models.DateTimeField(null=True, blank=True)

    # Location Information
    location = models.CharField(max_length=300, null=True, blank=True)  # Auto-detected or system location
    latitude = models.FloatField(null=True, blank=True)  # Geographic latitude
    longitude = models.FloatField(null=True, blank=True)  # Geographic longitude
    customer_address = models.TextField(null=True, blank=True)  # Manual address entered by customer

    block_unblock = models.BooleanField(default=True)  # True=Active/Unblocked, False=Blocked/Inactive

    # Family and Device Information
    number_of_family_members = models.PositiveIntegerField(default=1)  # Number of family members
    ota_status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')], default='pending')  # OTA update status
    fcm_token = models.CharField(max_length=255, null=True, blank=True)  # FCM token for push notifications
   

    # OTA/Firmware fields (merged from UserInfo)
    board = models.CharField(max_length=50, default='esp32', help_text="Board type: esp8266 or esp32")  # esp8266 / esp32
    firmware_version = models.CharField(max_length=20, null=True, blank=True, help_text="Target firmware version")  # TARGET VERSION
    last_seen = models.DateTimeField(auto_now=True, help_text="Last time device was seen online")
    is_active = models.BooleanField(default=True, help_text="Is device active")

    # Customer Type (Subscription plan or Paisa-per-litre billing)
    customer_type = models.CharField(
        max_length=20,
        choices=CUSTOMER_TYPE_CHOICES,
        default='subscription',
        help_text="Select subscription plan billing or paisa-per-litre billing preference"
    )
    
    # Subscription Plan for Normal Users
    subscription_plan = models.ForeignKey('SubscriptionPlan', on_delete=models.SET_NULL, null=True, blank=True, related_name='customers', help_text="Subscription plan for normal users")

    # Paisa per litre rate (set by admin for per-litre billing customers)
    paisa_per_litre = models.FloatField(default=10, help_text="Paisa per litre rate (e.g., 10 = 10 paisa/L = ₹0.10/L = 10L per ₹1)")

    device_health = models.CharField(max_length=50, null=True, blank=True, help_text="Device health status reported by device")
    device_token = models.CharField(max_length=255, null=True, blank=True, help_text="Provisioned device token used for ESP32 auth or push notifications")
    
    # Email Verification field (TOTP-based, no OTP storage needed)
    email_verified = models.BooleanField(default=False, help_text="Has email been verified during signup")
    
    # Future use fields
    future_field1 = models.CharField(max_length=255, null=True, blank=True)
    future_field2 = models.CharField(max_length=255, null=True, blank=True)
    future_field3 = models.TextField(null=True, blank=True)
    future_field4 = models.FloatField(null=True, blank=True)
    future_field5 = models.DateTimeField(null=True, blank=True)
    future_field6 = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-registration_date']

    def __str__(self):
        return f"{self.name} ({self.email})"

    @property
    def days_remaining(self):
        """Calculate days remaining until active recharge expires
        For per_litre customers: returns -1 (N/A - no expiry)
        For subscription customers: returns days until expiry
        """
        from datetime import datetime, timezone
        
        # Per-litre customers don't have expiry - return -1 to indicate N/A
        if self.customer_type == 'per_litre':
            return -1  # -1 means N/A (no expiry for per-litre)
        
        # For subscription customers: check active recharge expiry_date
        active_recharge = self.recharges.filter(status='active').order_by('-recharge_date').first()
        if active_recharge and active_recharge.expiry_date:
            days = (active_recharge.expiry_date - datetime.now(timezone.utc)).days
            return max(0, days)
        # Fallback to last_recharge_date for backward compatibility
        if self.last_recharge_date:
            days = (datetime.now(timezone.utc) - self.last_recharge_date).days
            return max(0, 30 - days)
        return 0

    @property
    def is_out_of_date(self):
        """Check if recharge is overdue
        For per_litre customers: only checks if litres_remaining <= 0
        For subscription customers: checks expiry date
        """
        from datetime import datetime, timezone
        
        active_recharge = self.recharges.filter(status='active').order_by('-recharge_date').first()
        
        # Per-litre customers: only check litres, not expiry
        if self.customer_type == 'per_litre':
            if active_recharge and active_recharge.litres_remaining > 0:
                return False  # Has litres remaining, not out of date
            return True  # No litres remaining
        
        # Subscription customers: check expiry date
        if active_recharge and active_recharge.expiry_date:
            return datetime.now(timezone.utc) > active_recharge.expiry_date
        # Fallback to last_recharge_date
        if self.last_recharge_date:
            days = (datetime.now(timezone.utc) - self.last_recharge_date).days
            return days > 30
        return True  # No recharge at all

    @property
    def recharge_status_color(self):
        """Return color status for recharge"""
        if self.is_out_of_date or self.days_remaining == 0: 
            return 'red'
        elif self.days_remaining <= 7:
            return 'yellow'
        return 'green'



    @property
    def paisa_per_litre_details(self):
        """Return a breakdown for paisa per litre for the active recharge and latest payment."""
        active_recharge = self.recharges.filter(status='active').order_by('-recharge_date').first()
        last_payment = self.payments.filter(payment_status='completed').order_by('-recharge_date').first()
        if active_recharge and last_payment and active_recharge.litres_allocated > 0:
            paisa_per_litre = round((float(last_payment.amount) * 100) / float(active_recharge.litres_allocated), 2)
            return {
                'paisa_per_litre': paisa_per_litre,
                'rupees': last_payment.amount,
                'litres': active_recharge.litres_allocated
            }
        return {}


class SensorData(models.Model):
    """Model for storing real-time sensor data from ESP devices"""
    customer = models.ForeignKey(
        'Customer',
        on_delete=models.CASCADE,
        related_name='sensor_readings',
        db_index=True
    )

    # ESP-provided timestamp (CRITICAL)
    esp_timestamp = models.DateTimeField(db_index=True, help_text="Timestamp sent by ESP (NTP synced)")

    # Volume data
    total_volume = models.FloatField(help_text="Total volume consumed")
    current_volume = models.FloatField(help_text="Current volume in this reading")

    # Water quality metrics
    water_quality = models.CharField(max_length=20, help_text="Water quality status")
    tds = models.FloatField(help_text="Total Dissolved Solids in ppm")
    ph = models.FloatField(help_text="pH level")

    # Device health
    device_health = models.CharField(max_length=20, help_text="Device health status")

    # Server timestamp
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-esp_timestamp']
        indexes = [
            models.Index(fields=['customer', 'esp_timestamp']),
            models.Index(fields=['esp_timestamp']),
        ]

    def __str__(self):
        return f"{self.customer.name} @ {self.esp_timestamp}"


class WaterUsage(models.Model):
    """Model for tracking daily aggregated water consumption"""
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='water_usages',
    )
    usage_date = models.DateField()  # Removed auto_now_add to allow manual date setting
    last_24hr_usage = models.FloatField(default=0)  # Liters
    per_day_average = models.FloatField(default=0)  # Liters per day
    current_day_usage = models.FloatField(default=0)  # Liters
    monthly_usage = models.FloatField(default=0)  # Liters
    
    
    # Future use fields
    future_field1 = models.CharField(max_length=255, null=True, blank=True)
    future_field2 = models.CharField(max_length=255, null=True, blank=True)
    future_field3 = models.TextField(null=True, blank=True)
    future_field4 = models.FloatField(null=True, blank=True)
    future_field5 = models.DateTimeField(null=True, blank=True)
    future_field6 = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-usage_date']
        unique_together = ('customer', 'usage_date')
    
    def __str__(self):
        return f"{self.customer.name} - {self.usage_date}"


class Payment(models.Model):
    """Model for payment history"""
    PAYMENT_STATUS = [
        ('completed', 'Completed'),
        ('pending', 'Pending'),
        ('failed', 'Failed'),
    ]
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    recharge_date = models.DateTimeField(auto_now_add=True)
    order_id = models.CharField(max_length=100, unique=True)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='completed')
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    
    # Future use fields
    future_field1 = models.CharField(max_length=255, null=True, blank=True)
    future_field2 = models.CharField(max_length=255, null=True, blank=True)
    future_field3 = models.TextField(null=True, blank=True)
    future_field4 = models.FloatField(null=True, blank=True)
    future_field5 = models.DateTimeField(null=True, blank=True)
    future_field6 = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-recharge_date']
    
    def __str__(self):
        return f"{self.customer.name} - ₹{self.amount}"




class Recharge(models.Model):
    """Model for filter recharge subscriptions"""
    RECHARGE_STATUS = [
        ('active', 'Active'),
        ('pending', 'Pending'),
        ('expired', 'Expired'),
    ]
    
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='recharges',
    )
    
    payment = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='recharges'
    )
    
    recharge_date = models.DateTimeField(auto_now_add=True)
    litres_allocated = models.FloatField(default=500)  # Default 500L per recharge
    litres_used = models.FloatField(default=0)
    litres_remaining = models.FloatField(default=500)
    expiry_date = models.DateTimeField()  # 30 days from recharge
    status = models.CharField(max_length=20, choices=RECHARGE_STATUS, default='active')
    paisa_per_litre_at_purchase = models.FloatField(null=True, blank=True)
    litres_purchased = models.FloatField(null=True, blank=True)
  
    
    # Future use fields
    future_field1 = models.CharField(max_length=255, null=True, blank=True)
    future_field2 = models.CharField(max_length=255, null=True, blank=True)
    future_field3 = models.TextField(null=True, blank=True)
    future_field4 = models.FloatField(null=True, blank=True)
    future_field5 = models.DateTimeField(null=True, blank=True)
    future_field6 = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-recharge_date']
    
    def __str__(self):
        return f"{self.customer.name} - {self.recharge_date}"
    
    def save(self, *args, **kwargs):
        """Override save to calculate and update customer's paisa_per_litre when recharge created with subscription plan"""
        super().save(*args, **kwargs)
        
        # Calculate paisa_per_litre if customer has a subscription plan
        if self.customer and self.customer.subscription_plan:
            subscription_plan = self.customer.subscription_plan
            if subscription_plan.litres_allocated > 0:
                # Calculate: paisa_per_litre = (plan price / plan litres) * 100 to convert to paisa
                paisa_per_litre = (subscription_plan.price / subscription_plan.litres_allocated) * 100
                
                # Update customer's paisa_per_litre
                self.customer.paisa_per_litre = paisa_per_litre
                self.customer.save(update_fields=['paisa_per_litre'])
    
    @property
    def is_expired(self):
        from datetime import datetime, timezone
        if self.expiry_date is None:
            return False
        return datetime.now(timezone.utc) > self.expiry_date
    
    @property
    def days_until_expiry(self):
        from datetime import datetime, timezone
        if self.expiry_date is None:
            return None
        days = (self.expiry_date - datetime.now(timezone.utc)).days
        return max(0, days)


class DismissedAlert(models.Model):
    """Model to track dismissed business alerts"""
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='dismissed_alerts',
    )
    alert_type = models.CharField(max_length=50)  # Type of alert dismissed
    dismissed_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    dismissed_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(null=True, blank=True)  # Optional notes about why dismissed
    
    # Future use fields
    future_field1 = models.CharField(max_length=255, null=True, blank=True)
    future_field2 = models.CharField(max_length=255, null=True, blank=True)
    future_field3 = models.TextField(null=True, blank=True)
    future_field4 = models.FloatField(null=True, blank=True)
    future_field5 = models.DateTimeField(null=True, blank=True)
    future_field6 = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-dismissed_at']
        unique_together = ('customer', 'alert_type')  # One dismissal per customer per alert type
    
    def __str__(self):
        return f"{self.customer.name} - {self.alert_type} dismissed"


class SubscriptionPlan(models.Model):
    """Model for subscription plans available to normal users (e.g., Rs 200 for 500L)"""
    
    plan_name = models.CharField(max_length=100)  # e.g., 'Basic', 'Standard', 'Premium'
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price in rupees (e.g., 200)
    litres_allocated = models.IntegerField()  # Water litres allocated (e.g., 500)
    duration_days = models.IntegerField(default=30)  # Duration in days
    status = models.BooleanField(default=True)
    is_popular = models.BooleanField(default=False)  # Mark as popular plan
    description_features = models.JSONField(default=list, blank=True, help_text="List of features")  # e.g., ["24/7 Support", "Water Quality Monitoring"]
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    
    # Future use fields
    future_field1 = models.CharField(max_length=255, null=True, blank=True)
    future_field2 = models.CharField(max_length=255, null=True, blank=True)
    future_field3 = models.TextField(null=True, blank=True)
    future_field4 = models.FloatField(null=True, blank=True)
    future_field5 = models.DateTimeField(null=True, blank=True)
    future_field6 = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['price']
    
    def __str__(self):
        return f"{self.plan_name} - ₹{self.price} for {self.litres_allocated}L"
    
    @property
    def price_per_litre(self):
        """Calculate price per litre"""
        if self.litres_allocated and self.price and self.litres_allocated > 0:
            return round(float(self.price) / float(self.litres_allocated), 2)
        return 0
    
    @property
    def paisa_per_litre(self):
        """Calculate paisa per litre"""
        if self.price_per_litre:
            return round(self.price_per_litre * 100, 2)
        return 0



class UserComplain(models.Model):
    """Model for customer complaints/support tickets"""
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
        ('pending', 'Pending'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    # User Information
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='complains',
    )
    # User name is obtained from customer.name, email moved to future_field1
    phone_no = models.CharField(max_length=20)
    device_id = models.CharField(max_length=100, null=True, blank=True)  # ESP32 device ID
    
    # Ticket System
    ticket_number = models.CharField(max_length=20, unique=True, blank=True, null=True)  # Auto-generated ticket number
    
    # Complaint Details
    problem_statement = models.TextField()  # Description of the problem
    complain_date = models.DateTimeField(auto_now_add=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    # Resolution 
    assigned_person = models.ForeignKey('Technician', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_complains')
    assigned_person_details = models.TextField(null=True, blank=True)  # Notes about assignment
    assigned_at = models.DateTimeField(null=True, blank=True)
    
    resolution_notes = models.TextField(null=True, blank=True)  # How the issue was resolved
    closed_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    
    # Future use fields
    # future_field1: email, future_field2: closing date (string)
    future_field1 = models.CharField("Email", max_length=255, null=True, blank=True)
    future_field2 = models.CharField("Closing Date", max_length=255, null=True, blank=True)
    future_field3 = models.TextField(null=True, blank=True)
    future_field4 = models.FloatField(null=True, blank=True)
    future_field5 = models.DateTimeField(null=True, blank=True)
    future_field6 = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-complain_date']
        verbose_name = 'User Complain'
        verbose_name_plural = 'User Complains'
    
    def save(self, *args, **kwargs):
        # Auto-generate ticket number if not set
        if not self.ticket_number:
            # Generate ticket number: TKT + YYYYMMDD + sequential number
            from django.utils import timezone
            today = timezone.now().date()
            date_str = today.strftime('%Y%m%d')
            
            # Find the next sequential number for today
            existing_tickets = UserComplain.objects.filter(
                ticket_number__startswith=f'TKT{date_str}'
            ).order_by('-ticket_number')
            
            if existing_tickets.exists():
                last_ticket = existing_tickets.first().ticket_number
                # Extract the sequential number (last 4 digits)
                try:
                    seq_num = int(last_ticket[-4:]) + 1
                except (ValueError, IndexError):
                    seq_num = 1
            else:
                seq_num = 1
            
            self.ticket_number = f'TKT{date_str}{seq_num:04d}'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.ticket_number} - {self.customer.name} - {self.status}"
    
    @property
    def days_since_complaint(self):
        """Calculate days since complaint was filed"""
        from datetime import datetime, timezone
        if not self.complain_date:
            return 0
        days = (datetime.now(timezone.utc) - self.complain_date).days
        return max(0, days)
    
    @property
    def is_overdue(self):
        """Check if complaint is overdue (open for more than 7 days)"""
        return self.days_since_complaint > 7 and self.status != 'closed'


class Coupon(models.Model):
    """Model for discount coupons/vouchers"""
    COUPON_TYPE_CHOICES = [
        ('percentage', 'Percentage Discount'),
        ('fixed', 'Fixed Amount'),
        ('free_litres', 'Free Litres'),
    ]
    
    COUPON_STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('expired', 'Expired'),
    ]
    
    coupon_code = models.CharField(max_length=50, unique=True)  # e.g., 'SUMMER20', 'WELCOME10'
    description = models.TextField(blank=True, null=True)
    coupon_type = models.CharField(max_length=20, choices=COUPON_TYPE_CHOICES, default='percentage')
    
    # Discount value depends on type:
    # - percentage: 5 means 5% discount
    # - fixed: 50 means ₹50 discount
    # - free_litres: 100 means 100 free litres
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Coupon validity
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    status = models.BooleanField(default=True)  # True=active, False=inactive
    
    # Usage limits
    max_usage = models.IntegerField(null=True, blank=True)  # None = unlimited
    current_usage = models.IntegerField(default=0)
    max_usage_per_customer = models.IntegerField(default=1)  # How many times a customer can use
    
    # Applicability
    min_order_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Minimum amount to apply
    applicable_plans = models.ManyToManyField(SubscriptionPlan, blank=True, related_name='coupons')  # Leave blank for all plans
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Future use fields
    future_field1 = models.CharField(max_length=255, null=True, blank=True)
    future_field2 = models.CharField(max_length=255, null=True, blank=True)
    future_field3 = models.TextField(null=True, blank=True)
    future_field4 = models.FloatField(null=True, blank=True)
    future_field5 = models.DateTimeField(null=True, blank=True)
    future_field6 = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-id']
    
    def __str__(self):
        return f"{self.coupon_code} - {self.get_coupon_type_display()}"
    
    @property
    def is_valid(self):
        """Check if coupon is currently valid"""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        return (self.status == 'active' and 
                self.valid_from <= now <= self.valid_until and
                (self.max_usage is None or self.current_usage < self.max_usage))
    
    @property
    def can_use(self):
        """Simple check if coupon can be used"""
        return self.is_valid
    
    def get_discount_amount(self, original_amount):
        """Calculate actual discount amount based on type"""
        from decimal import Decimal
        original = Decimal(str(original_amount))
        
        if self.coupon_type == 'percentage':
            return (original * Decimal(self.discount_value)) / Decimal(100)
        elif self.coupon_type == 'fixed':
            return min(self.discount_value, original)  # Discount can't exceed original amount
        else:  # free_litres
            return Decimal(0)  # Free litres are handled differently
    
    def apply_coupon(self, customer):
        """Apply coupon and increment usage"""
        from datetime import datetime, timezone
        
        if not self.is_valid:
            return False, "Coupon is not valid"
        
        # Check usage per customer
        usage_count = CouponUsage.objects.filter(coupon=self, customer=customer).count()
        if usage_count >= self.max_usage_per_customer:
            return False, f"You have already used this coupon {self.max_usage_per_customer} time(s)"
        
        # Check max usage
        if self.max_usage and self.current_usage >= self.max_usage:
            return False, "Coupon usage limit reached"
        
        return True, "Coupon applied successfully"


class CouponUsage(models.Model):
    """Model to track coupon usage per customer"""
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name='usages')
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='coupon_usages',
    )
    payment = models.ForeignKey(Payment, on_delete=models.SET_NULL, null=True, blank=True, related_name='coupon_usages')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2)
    used_at = models.DateTimeField(auto_now_add=True)
    
    # Future use fields
    future_field1 = models.CharField(max_length=255, null=True, blank=True)
    future_field2 = models.CharField(max_length=255, null=True, blank=True)
    future_field3 = models.TextField(null=True, blank=True)
    future_field4 = models.FloatField(null=True, blank=True)
    future_field5 = models.DateTimeField(null=True, blank=True)
    future_field6 = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-used_at']
        unique_together = ('coupon', 'customer', 'used_at')
    
    def __str__(self):
        return f"{self.coupon.coupon_code} - {self.customer.name}"


class OTA(models.Model):
    """Model for Over-The-Air (OTA) firmware updates"""
    version_name = models.CharField(max_length=100, unique=True)  # Version name (e.g., v1.0.0)
    bin_file = models.FileField(upload_to='ota_firmware/')  # Binary firmware file
    release_date = models.DateTimeField(auto_now_add=True)  # When the version was created
    is_active = models.BooleanField(default=False)  # Whether this version is currently active
    description = models.TextField(null=True, blank=True)  # Release notes/description
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ota_versions')  # Admin who uploaded
    
    # Future use fields
    future_field1 = models.CharField(max_length=255, null=True, blank=True)
    future_field2 = models.CharField(max_length=255, null=True, blank=True)
    future_field3 = models.TextField(null=True, blank=True)
    future_field4 = models.FloatField(null=True, blank=True)
    future_field5 = models.DateTimeField(null=True, blank=True)
    future_field6 = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-release_date']
    
    def __str__(self):
        return f"OTA Version {self.version_name}"


class CalibrationData(models.Model):
    """Model for storing calibration factor and water volume data records"""
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name='calibration_records',
    )
    
    # Calibration data
    calibration_factor = models.FloatField()  # Calibration factor value
    water_volume = models.FloatField()  # Water volume measurement
    
    # Metadata
    recorded_at = models.DateTimeField(auto_now_add=True)  # When this record was created
    
    # Future use fields
    future_field1 = models.CharField(max_length=255, null=True, blank=True)
    future_field2 = models.CharField(max_length=255, null=True, blank=True)
    future_field3 = models.TextField(null=True, blank=True)
    future_field4 = models.FloatField(null=True, blank=True)
    future_field5 = models.DateTimeField(null=True, blank=True)
    future_field6 = models.JSONField(null=True, blank=True)
    
    class Meta:
        ordering = ['-recorded_at']
    
    def __str__(self):
        return f"Calibration Record - {self.customer.name} ({self.recorded_at.strftime('%Y-%m-%d %H:%M')})"


#user traffic model
class RequestLog(models.Model):
    source = models.CharField(max_length=50)
    #ip = models.GenericIPAddressField()
    ip = models.CharField(max_length=50, null=True, blank=True)
    user_agent = models.TextField()
    date = models.DateField()  # NEW

    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('ip', 'source', 'date')  # PREVENT DUPLICATES



# Motivational Quote Model for Android/Streamlit API
class MotivationalQuote(models.Model):
    quote = models.TextField(null=True, blank=True, help_text="Optional motivational quote text")
    author = models.CharField(max_length=200, default="Unknown", help_text="Author of the quote")
    image = models.ImageField(upload_to='quotes/', help_text="Image for the quote (required)")
    is_active = models.BooleanField(default=True, help_text="Whether this quote is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.quote:
            return f"{self.quote[:50]}... - {self.author}"
        return f"Image Quote - {self.author}"
    
    
# For Email Verification
class EmailVerification(models.Model):
    email = models.EmailField(unique=True)
    secret = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=100, blank=True)
    
#For ForgotPassword verification
class PasswordReset(models.Model):
    email = models.EmailField(unique=True)
    secret = models.CharField(max_length=100)
    customer = models.ForeignKey("Customer", on_delete=models.CASCADE)
    
    verified = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    def is_expired(self):
        return (timezone.now() - self.created_at).total_seconds() > 300    
