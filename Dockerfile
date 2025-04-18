# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app


# Install Chrome dependencies
RUN apt-get update && \
    apt-get install -y \
        wget \
        gnupg && \
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - && \
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list && \
    apt-get update && \
    apt-get install -y google-chrome-stable && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install any needed packages specified in requirements.txt
# Install Gradio and Python dependencies
RUN pip install -r requirements.txt

# Create a non-root user
RUN useradd -m gruser && \
    chown -R gruser:gruser /app

# Switch to the non-root user
USER gruser:gruser

# Add the path to gunicorn to the user's PATH
ENV PATH=/home/gruser/.local/bin:$PATH

EXPOSE 7860

# Create a directory for logs
RUN mkdir /app/logs
RUN chown -R gruser:gruser /app/logs

# Specify the command to run when the container starts
CMD ["gunicorn", "-b", "0.0.0.0:7860", "--access-logfile", "/app/logs/access.log", "--error-logfile", "/app/logs/error.log", "--log-level", "info", "app:app"]
