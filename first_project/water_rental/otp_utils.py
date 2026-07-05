"""
OTP (One-Time Password) Utilities for Email Verification

This module provides functions to:
1. Generate random 6-digit OTP codes
2. Send OTP via email
3. Validate OTP codes and check expiration
"""

import secrets
from datetime import datetime, timezone, timedelta
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
import logging

logger = logging.getLogger(__name__)

# OTP expiration time in minutes (default 10 minutes)
OTP_EXPIRATION_MINUTES = 10


def generate_otp():
    """
    Generate a random 6-digit OTP code.
    
    Returns:
        str: A 6-digit OTP code
    """
    otp_code = str(secrets.randbelow(1000000)).zfill(6)
    return otp_code


def send_otp_email(email, otp_code, customer_name=None):
    """
    Send OTP email to customer's registered email address.
    
    Args:
        email (str): Customer's email address
        otp_code (str): The 6-digit OTP code
        customer_name (str, optional): Customer's name for personalized email
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    try:
        # Email subject
        subject = 'Your Email Verification Code - AquaGuard'
        
        # Email body
        if customer_name:
            greeting = f"Hello {customer_name},"
        else:
            greeting = "Hello,"
            
        message = f"""
{greeting}

Thank you for signing up with AquaGuard!

To verify your email address and complete your registration, please use the following verification code:

    {otp_code}

This code will expire in {OTP_EXPIRATION_MINUTES} minutes.

If you did not request this code, please ignore this email and your account will not be activated.

Important: Never share this code with anyone.

Best regards,
AquaGuard Team
"""
        
        # HTML email version
        html_message = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; }}
        .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; }}
        .header {{ color: #2c3e50; margin-bottom: 20px; }}
        .otp-code {{ font-size: 36px; font-weight: bold; color: #3498db; letter-spacing: 5px; margin: 20px 0; text-align: center; }}
        .footer {{ color: #7f8c8d; font-size: 12px; margin-top: 20px; border-top: 1px solid #ecf0f1; padding-top: 20px; }}
        .warning {{ color: #e74c3c; font-size: 12px; margin-top: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h2 class="header">{greeting}</h2>
        
        <p>Thank you for signing up with AquaGuard!</p>
        
        <p>To verify your email address and complete your registration, please use the following verification code:</p>
        
        <div class="otp-code">{otp_code}</div>
        
        <p>This code will expire in {OTP_EXPIRATION_MINUTES} minutes.</p>
        
        <p class="warning">Important: Never share this code with anyone.</p>
        
        <p>If you did not request this code, please ignore this email and your account will not be activated.</p>
        
        <div class="footer">
            <p>Best regards,<br>AquaGuard Team</p>
        </div>
    </div>
</body>
</html>
"""
        
        # Send email
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"OTP email sent successfully to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send OTP email to {email}: {str(e)}")
        return False


def validate_otp(customer, provided_otp_code):
    """
    Validate OTP code for a customer.
    
    Checks:
    1. OTP code matches
    2. OTP has not expired
    3. OTP exists and is not empty
    
    Args:
        customer: Customer object
        provided_otp_code (str): The OTP code provided by the user
        
    Returns:
        dict: {
            'valid': bool,
            'message': str,
            'expired': bool  # True if OTP expired
        }
    """
    # Check if OTP exists
    if not customer.otp_code:
        return {
            'valid': False,
            'message': 'No OTP found. Please request a new OTP.',
            'expired': False
        }
    
    # Check if OTP has expired
    if not customer.otp_created_at:
        return {
            'valid': False,
            'message': 'OTP creation time is missing. Please request a new OTP.',
            'expired': True
        }
    
    # Calculate OTP age
    current_time = datetime.now(timezone.utc)
    otp_age = current_time - customer.otp_created_at
    expiration_time = timedelta(minutes=OTP_EXPIRATION_MINUTES)
    
    if otp_age > expiration_time:
        return {
            'valid': False,
            'message': f'OTP has expired. Please request a new OTP.',
            'expired': True
        }
    
    # Check if OTP matches
    if str(customer.otp_code) != str(provided_otp_code):
        return {
            'valid': False,
            'message': 'Invalid OTP code. Please check and try again.',
            'expired': False
        }
    
    # OTP is valid
    return {
        'valid': True,
        'message': 'OTP verified successfully',
        'expired': False
    }


def clear_otp(customer):
    """
    Clear OTP from customer after successful verification.
    
    Args:
        customer: Customer object
    """
    customer.otp_code = None
    customer.otp_created_at = None
    customer.otp_verified = True
    customer.email_verified = True
    customer.save(update_fields=['otp_code', 'otp_created_at', 'otp_verified', 'email_verified'])
    logger.info(f"OTP cleared for customer {customer.email}")


def resend_otp(customer):
    """
    Resend OTP to customer by generating a new one and sending email.
    
    Args:
        customer: Customer object
        
    Returns:
        dict: {
            'success': bool,
            'message': str
        }
    """
    try:
        # Generate new OTP
        new_otp = generate_otp()
        
        # Update customer with new OTP
        customer.otp_code = new_otp
        customer.otp_created_at = datetime.now(timezone.utc)
        customer.save(update_fields=['otp_code', 'otp_created_at'])
        
        # Send new OTP email
        if send_otp_email(customer.email, new_otp, customer.name):
            logger.info(f"OTP resent successfully to {customer.email}")
            return {
                'success': True,
                'message': f'OTP has been resent to {customer.email}'
            }
        else:
            return {
                'success': False,
                'message': 'Failed to send OTP email. Please try again.'
            }
    except Exception as e:
        logger.error(f"Failed to resend OTP for {customer.email}: {str(e)}")
        return {
            'success': False,
            'message': f'Error: {str(e)}'
        }
