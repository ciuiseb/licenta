FROM python:3.11-slim
WORKDIR /app

# Install system dependencies if required by your ML libraries
RUN apt-get update && apt-get install -y gcc g++ libffi-dev

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# You must add eventlet to run SocketIO in production
RUN pip install eventlet gunicorn

# Copy your application code
COPY . .

# Hugging Face Spaces exposes port 7860 by default
EXPOSE 7860

# Start the server using Gunicorn with eventlet workers for WebSockets
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "-b", "0.0.0.0:7860", "main:app"]