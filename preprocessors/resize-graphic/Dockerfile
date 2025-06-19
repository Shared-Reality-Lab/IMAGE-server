FROM python:3.12

# Set the working directory inside the container
WORKDIR /usr/src/app

# Create a non-root user to run the application
RUN adduser --disabled-password python

# Update PATH to include local bin for the python user
ENV PATH="/usr/src/app/.local/bin:${PATH}"

# Install system dependencies required for healthcheck (curl) and model downloads (wget)
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y \
    curl wget && \
    rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY /preprocessors/resize-graphic/requirements.txt /usr/src/app/requirements.txt

# Install Python dependencies
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir -r /usr/src/app/requirements.txt

# Copy the schema and config files
COPY /schemas /usr/src/app/schemas
COPY /config /usr/src/app/config

# Copy your preprocessor application code
COPY /preprocessors/resize-graphic /usr/src/app

# Set environment variables needed by the Flask app
ENV FLASK_APP=resize-graphic.py

# Expose the port the application runs on
EXPOSE 80

# Switch to the non-root user
USER python

# Define the healthcheck command
HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:80/health || exit 1

# Define the command to run the application using gunicorn
CMD [ "gunicorn", "resize-graphic:app", "-b", "0.0.0.0:80", "--capture-output", "--timeout=120", "--log-level=debug" ]
