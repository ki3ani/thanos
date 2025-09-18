# Dockerfile

# --- STAGE 1: The "Builder" ---
# This stage's only job is to install our dependencies into a self-contained
# virtual environment. It's the slow, network-heavy part.
FROM python:3.11-slim as builder

# Set the working directory
WORKDIR /app

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy ONLY the requirements file
COPY requirements.txt .

# Install dependencies into the virtual environment
RUN pip install --no-cache-dir -r requirements.txt


# --- STAGE 2: The Final, Lean Image ---
# This stage creates the actual image we will deploy. It's fast and clean.
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy the virtual environment with all pre-installed packages from the builder stage.
# This is much faster and more reliable than running pip install again.
COPY --from=builder /opt/venv /opt/venv

# Activate the virtual environment for all subsequent commands
ENV PATH="/opt/venv/bin:$PATH"

# Copy the generated gRPC code and application code
COPY ./pb ./pb
COPY main.py .

# Expose the port the app runs on
EXPOSE 8080

# The command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]