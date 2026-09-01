# syntax=docker/dockerfile:1
FROM ultralytics/ultralytics:8.3.119-python

# Set the working directory inside the container
WORKDIR /usr/src/app

# Create a non-root user to run the application
RUN adduser --disabled-password python

# Update PATH to include local bin for the python user
ENV PATH="/usr/src/app/.local/bin:${PATH}"

# Install system dependencies required for healthcheck
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    curl && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY /preprocessors/object-segmentation/requirements.txt /usr/src/app/requirements.txt

# Install Python dependencies
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir -r /usr/src/app/requirements.txt

# Copy the schema, config, and shared utils files
COPY /schemas /usr/src/app/schemas
COPY /config /usr/src/app/config
COPY /utils /usr/src/app/utils

# Create model directory
RUN mkdir -p /usr/src/app/models

# Download SAM 3 (gated on Hugging Face: facebook/sam3). Requires an
# HF_TOKEN build secret from an account with approved access, passed via
# BuildKit's --secret (never a plain ARG, which would bake the token into
# the image's layer history).
RUN --mount=type=secret,id=HF_TOKEN \
    pip3 install --no-cache-dir huggingface_hub && \
    huggingface-cli download facebook/sam3 sam3.pt \
        --local-dir /usr/src/app/models \
        --token "$(cat /run/secrets/HF_TOKEN)"

# Copy the preprocessor application code
COPY /preprocessors/object-segmentation /usr/src/app

# Set environment variables needed by the Flask app
ENV FLASK_APP=object-segmentation.py

# Expose the port the application runs on
EXPOSE 5000

# Switch to the non-root user
USER python

# Define the healthcheck command
HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:5000/health || exit 1

# Define the command to run the application using gunicorn
CMD [ "gunicorn", "object-segmentation:app", "-b", "0.0.0.0:5000", "--capture-output", "--timeout=120", "--log-level=debug" ]
