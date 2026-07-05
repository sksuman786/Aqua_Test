from django.urls import path, reverse_lazy
from django.views.generic.base import RedirectView
from django.contrib.auth import views as auth_views
from . import views

from django.conf import settings
from django.conf.urls.static import static





app_name = 'aquaguard'

urlpatterns = [
    # Public Pages

    path('', views.homepage),
    path('landing/', views.landing_page, name='landing'),
    path("api/device-count/", views.device_count_api, name="device_count_api"),
    path("device-chart/", views.device_graph, name="device_chart"),
    
 # ========== DJANGO ADMIN & WEB UI VIEWS ==========
    # Authentication URLs
    path('admin-login/', views.admin_login, name='admin-login'),
    path('admin-signup/', views.admin_signup, name='admin-signup'),
    path('admin-logout/', views.admin_logout, name='admin-logout'),
    
    # Password Reset URLs
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='aquaguard/password_reset.html',
             email_template_name='aquaguard/password_reset_email.html',
             subject_template_name='aquaguard/password_reset_subject.txt',
             success_url=reverse_lazy('aquaguard:password_reset_done')
         ), 
         name='password-reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='aquaguard/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='aquaguard/password_reset_confirm.html',
             success_url=reverse_lazy('aquaguard:password_reset_complete')
         ), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='aquaguard/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    
    # Water Quality Monitoring
    path('business-alerts/', views.business_alerts_view, name='business-alerts'),
    path('business-alerts/api/', views.get_alerts_json, name='alerts-api'),
    path('alert/dismiss/<int:customer_id>/<str:alert_type>/', views.dismiss_alert, name='dismiss-alert'),
    path('alert/restore/<int:customer_id>/<str:alert_type>/', views.restore_alert, name='restore-alert'),
    
    # Admin Dashboard (Separate from Django Admin)
    path('admin-dashboard/', views.admin_dashboard, name='admin-dashboard'),
    path('customers/', views.CustomerListView.as_view(), name='customer-list'),
    path('customer/<uuid:customer_id>/', views.customer_details, name='customer-details'),
    path('customer/<uuid:customer_id>/toggle-block/', views.toggle_block_unblock, name='toggle-block'),
    path('customer-search/', views.customer_search, name='customer-search'),
    path('sensor-data/', views.sensor_data_dashboard, name='sensor-data'),
    path('payments/', views.payment_history, name='payment-history'),
    
    # ========== MOTIVATIONAL QUOTES MANAGEMENT ==========
    path('admin/uploadmotivationquote/', views.admin_quotes_management, name='admin-quotes-management'),
    
    # ========== EXPORT DATA ==========
    path('export/customers/excel/', views.export_customers_excel, name='export-customers-excel'),
    path('export/sensor-data/', views.export_sensor_data_csv, name='export-sensor-data-csv'),
    path('export/water-usage/excel/', views.export_water_usage_excel, name='export-water-usage-excel'),
    
    # ========== COUPON MANAGEMENT ==========
    path('admin/coupons/', views.admin_coupons_list, name='admin-coupons'),
    path('admin/coupons/create/', views.admin_create_coupon, name='admin-create-coupon'),
    path('admin/coupons/<int:coupon_id>/', views.admin_coupon_detail, name='admin-coupon-detail'),
    path('admin/coupons/<int:coupon_id>/update/', views.admin_update_coupon, name='admin-update-coupon'),
    path('admin/coupons/<int:coupon_id>/delete/', views.admin_delete_coupon, name='admin-delete-coupon'),
    
    # ========== SUBSCRIPTION PLAN MANAGEMENT ==========
    path('admin/subscription-plans/', views.admin_subscription_plans, name='subscription-plans'),
    path('admin/subscription-plans/create/', views.admin_create_subscription_plan, name='create-subscription-plan'),
    path('admin/subscription-plans/<int:plan_id>/', views.admin_subscription_plan_detail, name='subscription-plan-detail'),
    path('admin/subscription-plans/<int:plan_id>/update/', views.admin_update_subscription_plan, name='update-subscription-plan'),
    path('admin/subscription-plans/<int:plan_id>/delete/', views.admin_delete_subscription_plan, name='delete-subscription-plan'),
    
    # ========== USER COMPLAINTS MANAGEMENT ========== 
    path('admin/complaints/', views.admin_complaints_list, name='admin-complaints-list'),
    path('admin/complaints/create/', views.admin_create_complaint, name='admin-create-complaint'),
    path('admin/complaints/dashboard/', views.admin_complaints_dashboard, name='admin-complaints-dashboard'),
    path('admin/complaints/<int:complaint_id>/', views.admin_complaint_detail, name='admin-complaint-detail'),
    
    # ========== TECHNICIAN MANAGEMENT ========== 
    path('admin/technicians/', views.technician_list, name='technician-list'),
    path('admin/technicians/add/', views.add_technician, name='add-technician'),
    path('admin/technicians/<int:technician_id>/edit/', views.edit_technician, name='edit-technician'),
    path('admin/technicians/<int:technician_id>/delete/', views.delete_technician, name='delete-technician'),
    path('admin/technicians/<int:technician_id>/', views.technician_detail, name='technician-detail'),
    
    # ========== ADMIN EDIT REQUESTS ==========
    path('admin/edit-requests/', views.admin_edit_requests, name='admin-edit-requests'),
    path('admin/edit-requests/<int:request_id>/process/', views.admin_process_edit_request, name='admin-process-edit-request'),
    path('admin/customer/<uuid:customer_id>/edit/<int:request_id>/', views.admin_edit_customer_profile, name='admin-edit-customer-profile'),
    
    # ========== API ENDPOINTS ==========
    path('api/sensor-data/', views.ingest_sensor_data, name='ingest-sensor-data'),
    path('api/consumption/daily/', views.daily_consumption, name='daily-consumption'),
    path('api/consumption/monthly/', views.monthly_consumption, name='monthly-consumption'),
    
    # ========== ANDROID APP APIs ==========
    path('api/android/register/', views.customer_registration, name='customer-registration'),
    path('api/android/login/', views.customer_login, name='customer-login'),
    path('api/android/userinfo/<uuid:customer_id>/', views.customer_info, name='customer-info'),
    path('api/android/userlocation/<uuid:customer_id>/', views.customer_location, name='customer-location'),
    path('api/android/waterusage/<uuid:customer_id>/', views.customer_water_usage, name='customer-water-usage'),
    path('api/android/rechargeinfo/<uuid:customer_id>/', views.customer_recharge_info, name='customer-recharge-info'),
    path('api/android/purchase/<uuid:customer_id>/', views.customer_purchase_litres, name='customer-purchase-litres'),
    path('api/android/paymentdetails/<uuid:customer_id>/', views.customer_payment_details, name='customer-payment-details'),
    path('api/android/subscriptioninfo/', views.subscription_info, name='subscription-info'),
    path('api/android/subscribe/<uuid:customer_id>/', views.customer_subscribe_plan, name='customer-subscribe-plan'),
    path('api/android/complaint/<uuid:customer_id>/', views.customer_complaint, name='customer-complaint'),
    path('api/android/fcm-token/', views.fcm_token_register, name='fcm-token-register'),
    path('api/android/send-verification/', views.send_email_verification, name='send-email-verification'),
    path('api/android/verify-email/', views.verify_email_totp, name='verify-email-totp'),
    path('api/android/resend-verification/', views.resend_email_verification, name='resend-email-verification'),

    path('api/android/forgot-password/request/', views.forgot_password_request, name='forgot-password-request'), 
    path('api/android/forgot-password/verify/', views.forgot_password_verify, name='forgot-password-verify'), 
    path('api/android/forgot-password/reset/', views.forgot_password_reset, name='forgot-password-reset'),
    #path('api/android/profile/update/<uuid:customer_id>/', views.customer_profile_update, name='customer-profile-update'),

    
    # Chart Data APIs for Android App 
    path('api/android/usage/daily/<uuid:customer_id>/', views.customer_usage_daily_chart, name='customer-usage-daily-chart'), 
    path('api/android/usage/monthly/<uuid:customer_id>/', views.customer_usage_monthly_chart, name='customer-usage-monthly-chart'), 
    path('api/android/usage/hourly/<uuid:customer_id>/', views.customer_usage_hourly_chart, name='customer-usage-hourly-chart'), 
    path('api/android/usage/comparison/<uuid:customer_id>/', views.customer_usage_comparison_chart, name='customer-usage-comparison-chart'),
    path('api/android/sensor-data/<uuid:customer_id>/', views.customer_sensor_data_api),
    
    #water Quote
    path('api/water-quote/', views.water_quote_api, name='water-quote-api'), # single random quote
    path('api/water-quotes/', views.water_quotes_list_api, name='water-quotes-list-api'), #list of all quotes
    
    # Razorpay Payment APIs
    path('api/android/razorpay/create-order/<uuid:customer_id>/', views.create_razorpay_order, name='create-razorpay-order'),
    
    
    # ========== OTA ENDPOINTS ==========
    path('api/ota/provision/', views.provision_device, name='provision-device'),
    path('api/ota/check/', views.check_ota, name='check-ota'),
    
    # ========== ESP DEVICE APIs ==========
    path('api/esp/block-unblock-status/', views.esp_block_unblock_status, name='esp-block-unblock-status'),
    path('api/esp/ota-status-check/', views.esp_ota_status_check, name='esp-ota-status-check'),
    path('api/esp/sensor-data/', views.esp_sensor_data, name='esp-sensor-data'),
    path('api/esp/device-health/', views.esp_device_health, name='esp-device-health'),
    path('api/esp/calibration-factor/', views.esp_calibration_factor, name='esp-calibration-factor'),
    path('api/esp/user-details/', views.esp_get_user_details, name='esp-user-details'),
    path('api/esp/ping/', views.device_ping, name='device-ping'),
    path('api/esp/ping-response/', views.device_ping_response, name='device-ping-response'),

]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

