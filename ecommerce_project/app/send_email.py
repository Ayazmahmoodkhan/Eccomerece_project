import os
from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Email Configuration
conf = ConnectionConfig(
    MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    MAIL_FROM=os.getenv("MAIL_FROM"),
    MAIL_PORT=int(os.getenv("MAIL_PORT")),
    MAIL_SERVER=os.getenv("MAIL_SERVER"),
    USE_CREDENTIALS=True,
    MAIL_STARTTLS=False,
    MAIL_SSL_TLS=True,
    VALIDATE_CERTS=True,
)


# Background Email Sending Function
def send_email_background(background_tasks: BackgroundTasks, subject: str, email_to: str, body: dict):
    login_url = "https://192.168.1.32/login" 
    html_body = f"""
    <html>
        <body>
            <h1>{body.get("title", "No Title")}</h1>
            <p>Hello {body.get("name", "User")},</p>
            <p>Thank you for signing up. We're excited to have you on board!</p>

            <p>Click the link below to log in:</p>
            <p><a href="{login_url}" style="padding:10px 20px; background-color:blue; color:white; text-decoration:none; border-radius:5px;">
            Login to Your Account</a></p>

            <p>Feel free to explore our platform and reach out if you have any questions.</p>
        </body>
    </html>
    """

    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        body=html_body,  
        subtype=MessageType.html,
    )

    fm = FastMail(conf)
    background_tasks.add_task(fm.send_message, message)

# payment confirmation email

def send_payment_confirmation(background_tasks: BackgroundTasks, email_to: str, name: str, order_id: int, amount: float):
    subject = "Payment Confirmation - Order #" + str(order_id)
    body = {
        "title": "Payment Successful",
        "name": name,
        "order_id": order_id,
        "amount": f"${amount / 100:.2f}",
    }

    send_email_background(background_tasks, subject, email_to, body)
