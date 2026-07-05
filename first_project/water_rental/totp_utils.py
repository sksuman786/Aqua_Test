"""
TOTP (Time-Based One-Time Password) Utilities for Email Verification

This module provides functions to:
1. Generate TOTP secret for a customer
2. Generate TOTP code (6-digit)
3. Verify TOTP code
4. Send TOTP via email
"""

import pyotp
from django.core.mail import send_mail
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def generate_totp_secret():
    """
    Generate a random TOTP secret.
    
    Returns:
        str: Base32-encoded TOTP secret
    """
    secret = pyotp.random_base32()
    return secret


def get_totp_code(secret):
    """
    Get the current 6-digit TOTP code from secret.
    
    Args:
        secret (str): Base32-encoded TOTP secret
        
    Returns:
        str: Current 6-digit TOTP code
    """
    totp = pyotp.TOTP(secret)
    return totp.now()


def verify_totp_code(secret, code):
    """
    Verify if TOTP code matches the secret.
    Allows for time drift (±1 time window = ±30 seconds).
    
    Args:
        secret (str): Base32-encoded TOTP secret
        code (str): 6-digit TOTP code to verify
        
    Returns:
        bool: True if code is valid, False otherwise
    """
    try:
        totp = pyotp.TOTP(secret)
        # Allow for time drift of ±1 time window (30 seconds each way)
        return totp.verify(code, valid_window=1)
    except Exception as e:
        logger.error(f"TOTP verification error: {str(e)}")
        return False


def send_totp_email(email, totp_code, customer_name=None):
    """
    Send TOTP code via email to customer's registered email address.
    
    Args:
        email (str): Customer's email address
        totp_code (str): The 6-digit TOTP code
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

    {totp_code}

This code is valid for 30 seconds and will refresh automatically.

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
        
        <div class="otp-code">{totp_code}</div>
        
        <p>This code is valid for 30 seconds and will refresh automatically.</p>
        
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
        
        logger.info(f"TOTP email sent successfully to {email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send TOTP email to {email}: {str(e)}")
        return False


def get_totp_provisioning_url(email, secret, issuer="AquaGuard"):
    """
    Get provisioning URL for manual TOTP setup (QR code generation).
    Useful if user wants to set up authenticator app manually.
    
    Args:
        email (str): Customer's email
        secret (str): TOTP secret
        issuer (str): Issuer name (appears in authenticator app)
        
    Returns:
        str: Provisioning URL for QR code
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)

def send_password_reset_email(email, totp_code, customer_name=None): 
    """ 
    Send password reset TOTP code via email. 
     
    Args: 
        email (str): Customer's email address 
        totp_code (str): The 6-digit TOTP code 
        customer_name (str, optional): Customer's name for personalized email 
         
    Returns: 
        bool: True if email was sent successfully, False otherwise 
    """ 
    try: 
        subject = 'Password Reset Code - AquaGuard' 
         
        if customer_name: 
            greeting = f"Hello {customer_name}," 
        else: 
            greeting = "Hello," 
             
        message = f""" 
{greeting} 
 
We received a request to reset your AquaGuard account password. 
 
Your password reset code is: 
 
    {totp_code} 
 
This code is valid for 5 minutes. 
 
If you did not request a password reset, please ignore this email. Your password will 
remain unchanged. 
 
Important: Never share this code with anyone. 
 
Best regards, 
AquaGuard Team 
""" 
         
        html_message = f""" 
<!DOCTYPE html> 
<html> 
<head> 
    <meta charset="UTF-8"> 
    <style> 
        body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; }} 
        .container {{ max-width: 600px; margin: 0 auto; background-color: white; padding: 
20px; border-radius: 8px; }} 
        .header {{ color: #2c3e50; margin-bottom: 20px; }} 
        .otp-code {{ font-size: 36px; font-weight: bold; color: #e74c3c; letter-spacing: 
5px; margin: 20px 0; text-align: center; }} 
        .footer {{ color: #7f8c8d; font-size: 12px; margin-top: 20px; border-top: 1px 
solid #ecf0f1; padding-top: 20px; }} 
        .warning {{ color: #e74c3c; font-size: 12px; margin-top: 10px; }} 
    </style> 
</head> 
<body> 
    <div class="container"> 
        <h2 class="header">{greeting}</h2> 
         
        <p>We received a request to reset your AquaGuard account password.</p> 
         
        <p>Your password reset code is:</p> 
         
        <div class="otp-code">{totp_code}</div> 
         
        <p>This code is valid for 5 minutes.</p> 
         
        <p class="warning">Important: Never share this code with anyone.</p> 
         
        <p>If you did not request a password reset, please ignore this email. Your 
password will remain unchanged.</p> 
         
        <div class="footer"> 
            <p>Best regards,<br>AquaGuard Team</p> 
        </div> 
    </div> 
</body> 
</html> 
""" 
         
        send_mail( 
            subject=subject, 
            message=message, 
            from_email=settings.DEFAULT_FROM_EMAIL, 
            recipient_list=[email], 
            html_message=html_message, 
            fail_silently=False 
        ) 
        logger.info(f"Password reset email sent successfully to {email}") 
        return True 
    except Exception as e: 
        logger.error(f"Failed to send password reset email to {email}: {str(e)}") 
        return False 