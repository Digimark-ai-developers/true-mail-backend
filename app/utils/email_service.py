import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def send_email_with_link(email, link):
    from_email = "191370098@gift.edu.pk"  # Replace with your Gmail address
    from_password = "jxpc cjsg ktvr qjbq"  # Replace with your Gmail password (or App Password)
    try:
        # Create the email
        message = MIMEMultipart()
        message["From"] = from_email
        message["To"] = email
        message["Subject"] = "Verify your Email Address"

        body = f"""
        Hi,

        Please verify your email address by clicking the link below:

        {link}

        If you did not sign up, you can ignore this email.

        Thanks,
        Your Team
        """
        message.attach(MIMEText(body, "plain"))

        # Connect to Gmail SMTP
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(from_email, from_password)
            server.sendmail(from_email, email, message.as_string())

        print(f"Email sent successfully to {email}!")
    except Exception as e:
        print(f"Failed to send email. Error: {e}")
