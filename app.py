import os
import logging
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix


from bot import report_video
# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)


# Define base for SQLAlchemy models
class Base(DeclarativeBase):
    pass


# Initialize SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///videoreports.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Email configuration
app.config["EMAIL_ENABLED"] = os.environ.get("EMAIL_ENABLED",
                                             "False").lower() == "true"
app.config["EMAIL_USER"] = os.environ.get("EMAIL_USER", "")
app.config["EMAIL_PASS"] = os.environ.get("EMAIL_PASS", "")
app.config["EMAIL_RECEIVER"] = os.environ.get("EMAIL_RECEIVER", "")

# Initialize the database with the app
db.init_app(app)

# Import models here to avoid circular imports
from models import VideoReport
from email.mime.base import MIMEBase
from email import encoders

# Create database tables
with app.app_context():
    db.create_all()


def send_email_notification(video_url, report_category, report_details, success, screenshot_path=None):
    """Send email notification about the new report"""
    if not app.config["EMAIL_ENABLED"]:
        app.logger.info("Email notifications are disabled.")
        return False

    # If any of the email configuration is missing, log a warning and return
    if not app.config["EMAIL_USER"] or not app.config[
            "EMAIL_PASS"] or not app.config["EMAIL_RECEIVER"]:
        app.logger.warning(
            "Email configuration is incomplete. Please check your environment variables."
        )
        return False

    # Create the email message
    msg = MIMEMultipart('related')
    msg['From'] = app.config["EMAIL_USER"]
    msg['To'] = app.config["EMAIL_RECEIVER"]

    status = "Success" if success else "Failure"
    msg['Subject'] = f'New Video Report! Type: {report_category} - Status: {status}'

    # Email body
    body = f"""
    <html>
        <body>
            <p>A new video report has been submitted.</p>
            <p><strong>Status:</strong> {status}</p>
            <p><strong>Video URL:</strong> {video_url}</p>
            <p><strong>Report Category:</strong> {report_category}</p>
            <p><strong>Report Details:</strong> {report_details or "No additional details provided."}</p>
            <p><strong>Screenshot:</strong></p>
            {f'<img src="cid:screenshot" alt="Screenshot" style="max-width: 600px;"/>' if screenshot_path else "<p>No screenshot available.</p>"}
        </body>
    </html>
    """
    msg.attach(MIMEText(body, 'html'))

    # Attach screenshot inline if available
    if screenshot_path:
        try:
            with open(screenshot_path, 'rb') as f:
                screenshot_data = f.read()
            screenshot_filename = os.path.basename(screenshot_path)

            attachment = MIMEBase('application', 'octet-stream')
            attachment.set_payload(screenshot_data)
            encoders.encode_base64(attachment)
            attachment.add_header('Content-Disposition', f'attachment; filename={screenshot_filename}')
            attachment.add_header('Content-ID', '<screenshot>')
            attachment.add_header('X-Attachment-Id', 'screenshot')
            msg.attach(attachment)
        except Exception as e:
            app.logger.warning(f"Failed to attach screenshot: {str(e)}")

    # Send the email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(app.config["EMAIL_USER"], app.config["EMAIL_PASS"])
            server.send_message(msg)
        app.logger.info(f"Email notification sent to {app.config['EMAIL_RECEIVER']}")
        return True
    except Exception as e:
        app.logger.error(f"Failed to send email notification: {str(e)}")
        return False



# Routes
@app.route('/', methods=["GET", "POST"])
def index():
    screenshot_path = request.args.get('screenshot_path', None)
    recent_reports = []
    # Get 5 most recent reports
    try:
        recent_reports = VideoReport.query.order_by(
            VideoReport.timestamp.desc()).limit(5).all()
    except Exception as e:
        app.logger.error(f"Error fetching recent reports: {str(e)}")


    return render_template('index.html',
                           reports=recent_reports,
                           screenshot_path=screenshot_path)


@app.route('/submit_report', methods=['POST'])
def submit_report():
    video_url = request.form.get('video_url', '')
    report_category = request.form.get('report_category', '')
    report_details = request.form.get('report_details', '')
    screenshot_path = None

    # Simple validation
    if not video_url or not report_category:
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('index'))
    
    # report video
    success, screenshot_path = report_video(video_url, report_category, report_details)
    
    email_sent = send_email_notification(video_url, report_category,
                                             report_details, success, screenshot_path)
    
    if not success:
        flash('Failed to report the video. Please try again.', 'danger')
        return redirect(url_for('index', screenshot_path=screenshot_path ))
    
    app.logger.info(
        f"Video reported successfully: {video_url}, Category: {report_category}"
    )
    
        
    try:
        # Create a new report
        new_report = VideoReport(video_url=video_url,
                                 report_category=report_category,
                                 report_details=report_details,
                                 timestamp=datetime.now())

        # Add to database and commit
        db.session.add(new_report)
        db.session.commit()

        # Send email notification
        

        if email_sent:
            flash(
                'Your report has been submitted successfully and administrators were notified.',
                'success')
        else:
            flash('Your report has been submitted successfully!', 'success')

        return redirect(url_for('index', screenshot_path=screenshot_path))

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error submitting report: {str(e)}")
        flash(
            'An error occurred while submitting your report. Please try again.',
            'danger')
        return redirect(url_for('index', screenshot_path=screenshot_path))


@app.route('/history')
def history():
    try:
        # Get all reports ordered by most recent first
        reports = VideoReport.query.order_by(
            VideoReport.timestamp.desc()).all()
        return render_template('history.html', reports=reports)
    except Exception as e:
        app.logger.error(f"Error fetching report history: {str(e)}")
        flash('An error occurred while fetching report history.', 'danger')
        return redirect(url_for('index'))


# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('index.html'), 404


@app.errorhandler(500)
def server_error(e):
    app.logger.error(f"Server error: {str(e)}")
    return render_template('index.html'), 500


# Route to download the log file as a text file
@app.route('/logs')
def download_logs():
    log_file_path = 'youtube_reporter.log'
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, 'r') as log_file:
                logs = log_file.read()
            return logs, 200, {
                'Content-Type': 'text/plain',
                'Content-Disposition': f'attachment; filename={os.path.basename(log_file_path)}'
            }
        except Exception as e:
            app.logger.error(f"Error reading log file: {str(e)}")
            flash('An error occurred while accessing the log file.', 'danger')
            return redirect(url_for('index'))
    else:
        app.logger.warning("Log file not found.")
        flash('Log file not found.', 'danger')
        return redirect(url_for('index'))


