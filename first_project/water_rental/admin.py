# ========== OTA Firmware Admin (from ota_modified) ========== 
from django.contrib import admin, messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.template.response import TemplateResponse
from .models import Technician
from .forms import FirmwarePushForm

@admin.register(Technician)
class TechnicianAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'email', 'phone_number', 'specialization',
        'area_of_operation', 'rating', 'completed_jobs', 'status', 'is_active'
    )
    search_fields = ('name', 'email', 'phone_number', 'specialization', 'area_of_operation')
    list_filter = ('is_active', 'status', 'specialization', 'area_of_operation')

# ========== OTA Firmware Admin (merged UserInfo into Customer) ==========
from .models import Firmware

@admin.register(Firmware)
class FirmwareAdmin(admin.ModelAdmin):
    list_display = ('board', 'version', 'uploaded_at', 'is_active')

    def save_model(self, request, obj, form, change):
        """
        When firmware is uploaded,
        update TARGET firmware_version in Customer
        """
        super().save_model(request, obj, form, change)

        from .models import Customer
        Customer.objects.filter(
            board=obj.board
        ).update(firmware_version=obj.version)

from .models import (WaterQualityReading,
                     Customer, SensorData, WaterUsage, Recharge, Payment, DismissedAlert,
                     UserComplain, Coupon, CouponUsage, OTA, CalibrationData, SubscriptionPlan)


@admin.register(WaterQualityReading)
class WaterQualityReadingAdmin(admin.ModelAdmin):
    list_display = ('ph', 'tds', 'water_quality', 'reading_date', 'future_field1', 'future_field2')
    list_filter = ('reading_date', 'water_quality')
    search_fields = ('water_quality',)
    readonly_fields = ('reading_date',)
    fieldsets = (
        ('Physical Properties', {
            'fields': ('ph', 'tds')
        }),
        ('Water Quality', {
            'fields': ('water_quality',)
        }),
        ('Metadata', {
            'fields': ('reading_date',)
        }),
        ('Future Fields', {
            'fields': ('future_field1', 'future_field2', 'future_field3', 'future_field4', 'future_field5', 'future_field6')
        }),
    )


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone_number', 'customer_type', 'subscription_plan', 'device_status', 'block_unblock_display', 'days_remaining', 'recharge_status_color', 'number_of_family_members', 'ota_status', 'paisa_per_litre')
    list_filter = ('device_status', 'block_unblock', 'registration_date', 'ota_status', 'customer_type')
    search_fields = ('name', 'email', 'device_chip_id', 'location', 'customer_address', 'fcm_token')
    readonly_fields = ('name', 'email', 'registration_date', 'days_remaining', 'is_out_of_date', 'recharge_status_color')
    actions = ['schedule_ota_update']
    fieldsets = (
        ('Customer Info', {
            'fields': ('name', 'email', 'phone_number')
        }),
        ('Customer Type & Plan', {
            'fields': ('customer_type', 'subscription_plan'),
            'description': 'Subscription: Uses monthly plans | Paisa-per-litre: Uses consumption-based billing'
        }),
        ('Location Details', {
            'fields': ('location', 'latitude', 'longitude'),
            'description': 'Auto-detected or system-assigned location coordinates'
        }),
        ('Customer Address (Manual Entry)', {
            'fields': ('customer_address',),
            'description': 'Full address manually entered by customer'
        }),
        ('Device Info', {
            'fields': ('device_chip_id', 'device_status', 'ota_status', 'fcm_token')
        }),
        ('System Control', {
            'fields': ('block_unblock',),
            'description': 'Toggle to activate or deactivate the customer system'
        }),
        ('Billing Info', {
            'fields': ('paisa_per_litre',),
            'description': 'Price per litre in paisa (for per-litre billing customers)'
        }),
        ('Recharge Info', {
            'fields': ('last_recharge_date', 'days_remaining', 'is_out_of_date', 'recharge_status_color', 'device_token'),
            'description': 'Recharge and device token info'
        }),
    )

    def regenerate_token(self, obj):
        from django.utils.html import format_html
        return format_html('<a class="button" href="../{}/regenerate_token/">Generate New Token</a>', obj.pk)
    regenerate_token.short_description = 'Regenerate Token'
    regenerate_token.allow_tags = True

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:customer_id>/regenerate_token/', self.admin_site.admin_view(self.regenerate_token_view), name='customer-regenerate-token'),
        ]
        return custom_urls + urls

    def regenerate_token_view(self, request, customer_id):
        from django.shortcuts import redirect, get_object_or_404
        from django.contrib import messages
        customer = get_object_or_404(Customer, pk=customer_id)
        token = customer.generate_device_token()
        messages.success(request, f'A new device token has been generated: {token}')
        return redirect(request.META.get('HTTP_REFERER', '/admin/water_rental/customer/'))
    
    def save_model(self, request, obj, form, change):
        """
        Clear cache when customer data changes to ensure tokens are properly invalidated
        """
        # Clear cache for this device
        from django.core.cache import cache
        cache.delete(f"token:{obj.device_chip_id}")
        cache.delete(f"device_meta:{obj.device_chip_id}")

        # If customer is being deactivated, clear their token
        if not obj.is_active or not obj.block_unblock:
            obj.device_token = None

        super().save_model(request, obj, form, change)
    
    def block_unblock_display(self, obj):
        """Display status as colored indicator"""
        if obj.block_unblock:
            return '🟢 Active'
        return '🔴 Blocked'
    block_unblock_display.short_description = 'System Status'

    def schedule_ota_update(self, request, queryset):
        """Bulk assign a firmware build and mark the OTA rollout as pending."""
        if 'apply' in request.POST:
            form = FirmwarePushForm(request.POST)
            if form.is_valid():
                firmware = form.cleaned_data['firmware']
                matching = queryset.filter(board=firmware.board)
                mismatched = queryset.exclude(board=firmware.board)

                updated = matching.update(
                    firmware_version=firmware.version,
                    ota_status='pending'
                )

                if updated:
                    messages.success(
                        request,
                        f"Scheduled OTA {firmware.version} for {updated} device(s) on {firmware.board.upper()}"
                    )
                else:
                    messages.warning(
                        request,
                        'No matching devices were updated. Ensure the selected firmware matches the device board.'
                    )

                if mismatched.exists():
                    messages.warning(
                        request,
                        f"Skipped {mismatched.count()} device(s) due to board mismatch."
                    )
                return None
        else:
            form = FirmwarePushForm()

        context = {
            'customers': queryset,
            'form': form,
            'action': 'schedule_ota_update',
            'title': 'Schedule OTA Update',
            'opts': self.model._meta,
            'action_checkbox_name': ACTION_CHECKBOX_NAME,
            'select_across': request.POST.get('select_across'),
        }
        return TemplateResponse(request, 'admin/water_rental/customer/schedule_ota.html', context)
    schedule_ota_update.short_description = 'Schedule OTA update for selected devices'

@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = (
        "customer",
        "esp_timestamp",
        "total_volume",
        "current_volume",
        "water_quality",
        "tds",
        "ph",
        "device_health",
        "created_at",
    )
    list_filter = (
        "water_quality",
        "device_health",
        "created_at",
        "customer",
    )
    search_fields = (
        "customer__name",
        "customer__email",
        "customer__device_chip_id",
    )
    readonly_fields = ("esp_timestamp", "created_at")
    date_hierarchy = "esp_timestamp"

@admin.register(WaterUsage)
class WaterUsageAdmin(admin.ModelAdmin):
    list_display = (
        'customer', 'usage_date', 'last_24hr_usage', 'monthly_usage',
        'per_day_average', 'current_day_usage', 'future_field1', 'future_field2'
    )
    list_filter = ('usage_date', 'customer')
    search_fields = ('customer__name', 'customer__email')
    readonly_fields = ('usage_date',)
    fieldsets = (
        ('Usage Info', {
            'fields': (
                'customer', 'usage_date', 'last_24hr_usage',
                'monthly_usage', 'per_day_average', 'current_day_usage'
            )
        }),
        ('Future Fields', {
            'fields': ('future_field1', 'future_field2', 'future_field3', 'future_field4', 'future_field5', 'future_field6')
        }),
    )

@admin.register(Recharge)
class RechargeAdmin(admin.ModelAdmin):
    list_display = ('customer', 'recharge_date', 'litres_allocated', 'litres_used', 'litres_remaining', 'expiry_date', 'status', 'days_until_expiry', 'future_field1', 'future_field2')
    list_filter = ('status', 'recharge_date')
    search_fields = ('customer__name', 'customer__email')
    readonly_fields = ('recharge_date', 'days_until_expiry', 'is_expired')
    fieldsets = (
        ('Recharge Info', {
            'fields': ('customer', 'recharge_date', 'litres_allocated', 'litres_used', 'litres_remaining', 'expiry_date', 'status', 'days_until_expiry', 'is_expired')
        }),
        ('Future Fields', {
            'fields': ('future_field1', 'future_field2', 'future_field3', 'future_field4', 'future_field5', 'future_field6')
        }),
    )

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('customer', 'amount', 'recharge_date', 'order_id', 'payment_status', 'transaction_id', 'future_field1', 'future_field2')
    list_filter = ('payment_status', 'recharge_date')
    search_fields = ('customer__name', 'customer__email', 'order_id', 'transaction_id')
    readonly_fields = ('recharge_date', 'order_id')
    fieldsets = (
        ('Payment Info', {
            'fields': ('customer', 'amount', 'recharge_date', 'order_id', 'payment_status', 'transaction_id')
        }),
        ('Future Fields', {
            'fields': ('future_field1', 'future_field2', 'future_field3', 'future_field4', 'future_field5', 'future_field6')
        }),
    )

@admin.register(DismissedAlert)
class DismissedAlertAdmin(admin.ModelAdmin):
    list_display = ('customer', 'alert_type', 'dismissed_by', 'dismissed_at', 'future_field1', 'future_field2')
    list_filter = ('alert_type', 'dismissed_at')
    search_fields = ('customer__name', 'customer__email', 'dismissed_by__username')
    readonly_fields = ('dismissed_at',)
    fieldsets = (
        ('Alert Information', {
            'fields': ('customer', 'alert_type')
        }),
        ('Dismissal Details', {
            'fields': ('dismissed_by', 'dismissed_at', 'notes')
        }),
        ('Future Fields', {
            'fields': ('future_field1', 'future_field2', 'future_field3', 'future_field4', 'future_field5', 'future_field6')
        }),
    )


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    """Admin interface for subscription plan management"""
    list_display = ('plan_name', 'price', 'litres_allocated', 'duration_days', 'is_popular', 'status')
    list_filter = ('status', 'is_popular', 'duration_days')
    search_fields = ('plan_name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fields = ('plan_name', 'description', 'price', 'litres_allocated', 'duration_days', 'is_popular', 'status', 'description_features', 'created_at', 'updated_at')
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        """Ensure litres_allocated field has no default value"""
        if db_field.name == 'litres_allocated':
            kwargs['initial'] = None
            kwargs['required'] = True
        return super().formfield_for_dbfield(db_field, request, **kwargs)
    
    def get_customer_count(self, obj):
        """Display count of customers using this plan"""
        if not obj or not obj.pk:
            return "0 customers"
        count = obj.customers.count()
        return f"{count} customer{'s' if count != 1 else ''}"
    get_customer_count.short_description = 'Customers Using This Plan'
    
    def save_model(self, request, obj, form, change):
        """Save the subscription plan"""
        super().save_model(request, obj, form, change)


@admin.register(UserComplain)
class UserComplainAdmin(admin.ModelAdmin):
    list_display = ('customer', 'phone_no', 'device_id', 'priority', 'status', 'complain_date', 'days_since_complaint', 'assigned_person', 'future_field1', 'future_field2')
    list_filter = ('status', 'priority', 'complain_date', 'assigned_person')
    search_fields = ('customer__name', 'phone_no', 'device_id', 'problem_statement', 'future_field1')
    readonly_fields = ('complain_date', 'days_since_complaint', 'is_overdue')
    date_hierarchy = 'complain_date'
    fieldsets = (
        ('Customer Information', {
            'fields': ('customer', 'phone_no', 'device_id')
        }),
        ('Complaint Details', {
            'fields': ('problem_statement', 'priority', 'complain_date', 'days_since_complaint', 'is_overdue')
        }),
        ('Assignment & Resolution', {
            'fields': ('assigned_person', 'assigned_person_details', 'assigned_at', 'status', 'resolution_notes', 'closed_date')
        }),
        ('Future Fields', {
            'fields': ('future_field1', 'future_field2', 'future_field3', 'future_field4', 'future_field5', 'future_field6')
        }),
    )



    def save_model(self, request, obj, form, change):
        # Move email to future_field1, closed_date to future_field2
        obj.future_field1 = obj.email if hasattr(obj, 'email') else ''
        obj.future_field2 = obj.closed_date.strftime('%Y-%m-%d %H:%M') if obj.closed_date else ''
        super().save_model(request, obj, form, change)
    
    actions = ['mark_in_progress', 'mark_resolved', 'mark_closed']
    
    def mark_in_progress(self, request, queryset):
        """Admin action to mark complaints as in progress"""
        from django.utils import timezone
        queryset.update(status='in_progress', assigned_person=request.user, assigned_at=timezone.now())
    mark_in_progress.short_description = "Mark selected as In Progress"
    
    def mark_resolved(self, request, queryset):
        """Admin action to mark complaints as resolved"""
        queryset.update(status='resolved')
    mark_resolved.short_description = "Mark selected as Resolved"
    
    def mark_closed(self, request, queryset):
        """Admin action to mark complaints as closed"""
        from django.utils import timezone
        queryset.update(status='closed', closed_date=timezone.now())
    mark_closed.short_description = "Mark selected as Closed"


@admin.register(OTA)
class OTAAdmin(admin.ModelAdmin):
    list_display = ('version_name', 'is_active', 'release_date', 'created_by', 'future_field1', 'future_field2')
    list_filter = ('is_active', 'release_date')
    search_fields = ('version_name', 'description')
    readonly_fields = ('release_date',)
    fieldsets = (
        ('Version Information', {
            'fields': ('version_name', 'is_active')
        }),
        ('Firmware', {
            'fields': ('bin_file', 'description')
        }),
        ('Metadata', {
            'fields': ('release_date', 'created_by')
        }),
        ('Future Fields', {
            'fields': ('future_field1', 'future_field2', 'future_field3', 'future_field4', 'future_field5', 'future_field6')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Set created_by when saving"""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    """Admin interface for coupon usage tracking"""
    list_display = ('coupon', 'customer', 'discount_amount', 'used_at', 'payment')
    list_filter = ('used_at', 'coupon__coupon_type', 'coupon__status')
    search_fields = ('coupon__coupon_code', 'customer__name', 'customer__email')
    readonly_fields = ('used_at',)
    raw_id_fields = ('coupon', 'customer', 'payment')


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('coupon_code', 'coupon_type', 'discount_value', 'status', 'valid_from', 'valid_until', 'current_usage', 'max_usage', 'created_at', 'future_field1', 'future_field2')
    list_filter = ('status', 'coupon_type', 'valid_from', 'valid_until', 'created_at')
    search_fields = ('coupon_code', 'description')
    readonly_fields = ('current_usage', 'created_at', 'updated_at')
    actions = ['recalculate_usage_counts']
    fieldsets = (
        ('Coupon Information', {
            'fields': ('coupon_code', 'description')
        }),
        ('Discount Details', {
            'fields': ('coupon_type', 'discount_value')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_until', 'status')
        }),
        ('Usage Limits', {
            'fields': ('max_usage', 'current_usage', 'max_usage_per_customer')
        }),
        ('Applicability', {
            'fields': ('min_order_amount', 'applicable_plans')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
        ('Future Fields', {
            'fields': ('future_field1', 'future_field2', 'future_field3', 'future_field4', 'future_field5', 'future_field6')
        }),
    )

    def recalculate_usage_counts(self, request, queryset):
        """Recalculate current_usage for selected coupons based on CouponUsage records"""
        updated = 0
        for coupon in queryset:
            actual_usage = coupon.usages.count()
            if coupon.current_usage != actual_usage:
                coupon.current_usage = actual_usage
                coupon.save(update_fields=['current_usage'])
                updated += 1
        self.message_user(request, f"Recalculated usage counts for {updated} coupon(s).")
    recalculate_usage_counts.short_description = "Recalculate usage counts for selected coupons"


@admin.register(CalibrationData)
class CalibrationDataAdmin(admin.ModelAdmin):
    list_display = ('customer', 'calibration_factor', 'water_volume', 'recorded_at', 'future_field1', 'future_field2')
    list_filter = ('recorded_at', 'customer')
    search_fields = ('customer__name', 'customer__email')
    readonly_fields = ('recorded_at',)
    fieldsets = (
        ('Customer Information', {
            'fields': ('customer',)
        }),
        ('Calibration Data', {
            'fields': ('calibration_factor', 'water_volume')
        }),
        ('Metadata', {
            'fields': ('recorded_at',)
        }),
        ('Future Fields', {
            'fields': ('future_field1', 'future_field2', 'future_field3', 'future_field4', 'future_field5', 'future_field6')
        }),
    )


#User Traffic Log
from .models import RequestLog

class RequestLogAdmin(admin.ModelAdmin):
    list_display = ('source', 'ip', 'timestamp')
    list_filter = ('source', 'timestamp')
    search_fields = ('user_agent', 'ip')