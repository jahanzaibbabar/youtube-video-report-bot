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

# Create database tables
with app.app_context():
    db.create_all()


def send_email_notification(video_url, report_category, report_details):
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

    msg = MIMEMultipart()
    msg['From'] = app.config["EMAIL_USER"]
    msg['To'] = app.config["EMAIL_RECEIVER"]
    msg['Subject'] = f'New Video Report: {report_category}'

    body = f'''
    A new report has been submitted:

    Video URL: {video_url}
    Report Category: {report_category}
    Report Details: {report_details or "No additional details provided."}
    
    View all reports in the admin dashboard.
    '''

    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(app.config["EMAIL_USER"], app.config["EMAIL_PASS"])
            server.send_message(msg)
        app.logger.info(
            f"Email notification sent to {app.config['EMAIL_RECEIVER']}")
        return True
    except Exception as e:
        app.logger.error(f"Failed to send email notification: {str(e)}")
        return False



# Routes
@app.route('/', methods=["GET", "POST"])
def index():
    video_url = None
    recent_reports = []

    # Get 5 most recent reports
    try:
        recent_reports = VideoReport.query.order_by(
            VideoReport.timestamp.desc()).limit(5).all()
    except Exception as e:
        app.logger.error(f"Error fetching recent reports: {str(e)}")

    # Handle form submission directly
    # if request.method == "POST":
    #     video_url = request.form.get('video_url', '')
    #     report_category = request.form.get('report_category', '')
    #     report_details = request.form.get('report_details', '')

    #     # Simple validation
    #     if not video_url or not report_category:
    #         flash('Please fill in all required fields.', 'danger')
    #         return render_template('index.html', reports=recent_reports)
        
    #     # report video
    #     report_video(video_url, report_category, report_details)

    #     try:
    #         # Create a new report
    #         new_report = VideoReport(video_url=video_url,
    #                                  report_category=report_category,
    #                                  report_details=report_details,
    #                                  timestamp=datetime.now())

    #         # Add to database and commit
    #         db.session.add(new_report)
    #         db.session.commit()

    #         # Send email notification
    #         email_sent = send_email_notification(video_url, report_category,
    #                                              report_details)

    #         if email_sent:
    #             flash(
    #                 'Your report has been submitted successfully and administrators were notified.',
    #                 'success')
    #         else:
    #             flash('Your report has been submitted successfully!',
    #                   'success')

    #         # Update recent reports after submission
    #         recent_reports = VideoReport.query.order_by(
    #             VideoReport.timestamp.desc()).limit(5).all()

    #         return render_template('index.html',
    #                                reports=recent_reports,
    #                                video_url=video_url)

    #     except Exception as e:
    #         db.session.rollback()
    #         app.logger.error(f"Error submitting report: {str(e)}")
    #         flash(
    #             'An error occurred while submitting your report. Please try again.',
    #             'danger')

    return render_template('index.html',
                           reports=recent_reports,
                           video_url=video_url)


@app.route('/submit_report', methods=['POST'])
def submit_report():
    video_url = request.form.get('video_url', '')
    report_category = request.form.get('report_category', '')
    report_details = request.form.get('report_details', '')

    # Simple validation
    if not video_url or not report_category:
        flash('Please fill in all required fields.', 'danger')
        return redirect(url_for('index'))
    
    # report video
    success = report_video(video_url, report_category, report_details)
    if not success:
        flash('Failed to report the video. Please try again.', 'danger')
        return redirect(url_for('index'))
    app.logger.info(
        f"Video reported failed: {video_url}, Category: {report_category}"
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
        email_sent = send_email_notification(video_url, report_category,
                                             report_details)

        if email_sent:
            flash(
                'Your report has been submitted successfully and administrators were notified.',
                'success')
        else:
            flash('Your report has been submitted successfully!', 'success')

        return redirect(url_for('index'))

    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error submitting report: {str(e)}")
        flash(
            'An error occurred while submitting your report. Please try again.',
            'danger')
        return redirect(url_for('index'))


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

