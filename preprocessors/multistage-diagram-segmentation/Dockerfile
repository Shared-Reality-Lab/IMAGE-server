FROM ultralytics/ultralytics:8.3.119-python

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
COPY /preprocessors/multistage-diagram-segmentation/requirements.txt /usr/src/app/requirements.txt

# Install Python dependencies
RUN pip3 install --upgrade pip && \
    pip3 install --no-cache-dir -r /usr/src/app/requirements.txt

# Copy the schema and config files
COPY /schemas /usr/src/app/schemas
COPY /config /usr/src/app/config

# Create model directory
RUN mkdir -p /usr/src/app/models

# Download YOLOv11 model
RUN wget -O /usr/src/app/models/sam2.1_l.pt https://image.a11y.mcgill.ca/models/semanticSegmentation/sam2.1_l.pt

# Copy your preprocessor application code
# Make sure your python script is named 'diagram_preprocessor.py'
COPY /preprocessors/multistage-diagram-segmentation /usr/src/app 

# Set environment variables needed by the Flask app
ENV FLASK_APP=multistage-diagram-segmentation.py

# Expose the port the application runs on
EXPOSE 5000

# Switch to the non-root user
USER python

# Define the healthcheck command
HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost:5000/health || exit 1

# Define the command to run the application using gunicorn
CMD [ "gunicorn", "multistage-diagram-segmentation:app", "-b", "0.0.0.0:5000", "--capture-output", "--timeout=120", "--log-level=debug" ]