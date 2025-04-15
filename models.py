from app import db
from datetime import datetime

class VideoReport(db.Model):
    """Model for video reports submitted by users"""
    id = db.Column(db.Integer, primary_key=True)
    video_url = db.Column(db.String(2048), nullable=False)
    report_category = db.Column(db.String(100), nullable=False)
    report_details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<VideoReport {self.id}: {self.report_category}>'
    
    def format_timestamp(self):
        """Return formatted timestamp for display"""
        return self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
