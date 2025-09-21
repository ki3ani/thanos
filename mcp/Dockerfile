# Start with a lightweight Python base image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file first and install dependencies
# (This helps Docker cache this layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY app.py .

# Expose the port the app runs on
EXPOSE 8080

# The command to run when the container starts
CMD ["python", "app.py"]