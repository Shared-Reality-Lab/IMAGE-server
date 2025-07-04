ARG REGISTRY_TAG
# Stage 1: Build the application
FROM ghcr.io/shared-reality-lab/tat-service:${REGISTRY_TAG} as build

# Set the working directory inside the container
WORKDIR /app

# Clone git repo into app dir
# RUN apk add git
# RUN git clone https://github.com/Shared-Reality-Lab/IMAGE-TactileAuthoring.git \
#     --depth 1 --single-branch .

# Install dependencies
# RUN npm install


# Build the application
# RUN npm run build

# Set npm to ignore scripts
# ENV npm_config_ignore_scripts=true

# Run build manually ignoring scripts
# WORKDIR /app/packages/svgcanvas
# RUN npx rollup -c
# WORKDIR /app
# RUN npx rollup -c

# Stage 2: Serve the application
FROM nginx:alpine

# Copy the build output from the previous stage to the Nginx HTML directory
COPY --from=build /app/dist/editor/ /usr/share/nginx/html

# Add a static health check file
COPY services/tat/healthcheck.html /usr/share/nginx/html/

# Copy a custom Nginx configuration file, if needed (optional)
# COPY nginx.conf /etc/nginx/nginx.conf

# Expose the default Nginx port
EXPOSE 80

# Healthcheck
HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=5 CMD curl -f http://localhost/healthcheck.html || exit 1

# Create config.js and start the Nginx server
CMD sh -c "echo \"window.APP_CONFIG = { serverUrl: '\${SERVER_URL}' };\" > /usr/share/nginx/html/config.js && nginx -g 'daemon off;'"