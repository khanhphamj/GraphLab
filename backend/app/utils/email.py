"""Email utilities for sending verification and password reset emails"""

import os
import logging
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import ssl

logger = logging.getLogger(__name__)

# Email settings - should come from environment variables
SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@graphlab.com")
FROM_NAME = os.getenv("FROM_NAME", "GraphLab")

# Frontend URLs for email links
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None
) -> bool:
    """Send an email using SMTP"""
    try:
        # Create message
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{FROM_NAME} <{FROM_EMAIL}>"
        message["To"] = to_email

        # Add text content
        if text_content:
            text_part = MIMEText(text_content, "plain")
            message.attach(text_part)

        # Add HTML content
        html_part = MIMEText(html_content, "html")
        message.attach(html_part)

        # Send email
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            if SMTP_USE_TLS:
                server.starttls(context=context)
            if SMTP_USERNAME and SMTP_PASSWORD:
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(FROM_EMAIL, to_email, message.as_string())

        logger.info(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False


async def send_verification_email(email: str, token: str) -> bool:
    """Send email verification email"""
    verification_url = f"{FRONTEND_URL}/auth/verify-email?token={token}"
    
    subject = "Verify your GraphLab email"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Verify your email</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #2c3e50;">Verify your email address</h1>
            
            <p>Thank you for signing up for GraphLab! Please click the button below to verify your email address:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{verification_url}" 
                   style="background-color: #3498db; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Verify Email Address
                </a>
            </div>
            
            <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #7f8c8d;">{verification_url}</p>
            
            <p>This link will expire in 24 hours.</p>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #7f8c8d; font-size: 12px;">
                If you didn't create an account with GraphLab, you can safely ignore this email.
            </p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Verify your GraphLab email address
    
    Thank you for signing up for GraphLab! Please visit the following link to verify your email address:
    
    {verification_url}
    
    This link will expire in 24 hours.
    
    If you didn't create an account with GraphLab, you can safely ignore this email.
    """
    
    return await send_email(email, subject, html_content, text_content)


async def send_password_reset_email(email: str, token: str) -> bool:
    """Send password reset email"""
    reset_url = f"{FRONTEND_URL}/auth/reset-password?token={token}"
    
    subject = "Reset your GraphLab password"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Reset your password</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #2c3e50;">Reset your password</h1>
            
            <p>You requested to reset your GraphLab password. Click the button below to set a new password:</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" 
                   style="background-color: #e74c3c; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Reset Password
                </a>
            </div>
            
            <p>If the button doesn't work, you can copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #7f8c8d;">{reset_url}</p>
            
            <p>This link will expire in 24 hours.</p>
            
            <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
            <p style="color: #7f8c8d; font-size: 12px;">
                If you didn't request a password reset, you can safely ignore this email. Your password will not be changed.
            </p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Reset your GraphLab password
    
    You requested to reset your GraphLab password. Please visit the following link to set a new password:
    
    {reset_url}
    
    This link will expire in 24 hours.
    
    If you didn't request a password reset, you can safely ignore this email. Your password will not be changed.
    """
    
    return await send_email(email, subject, html_content, text_content)
