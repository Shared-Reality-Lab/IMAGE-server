# Stage 1: Build the application
FROM node:20-alpine as build

# Set the working directory inside the container
WORKDIR /app

# Clone git repo into app dir
RUN apk add git
RUN git clone https://github.com/Shared-Reality-Lab/IMAGE-TactileAuthoring.git \
    --depth 1 --single-branch .

# Install dependencies
RUN npm install


# Build the application
# RUN npm run build

# Set npm to ignore scripts
ENV npm_config_ignore_scripts=true

# Run build manually ignoring scripts
WORKDIR /app/packages/svgcanvas
RUN npx rollup -c
WORKDIR /app
RUN npx rollup -c

# Stage 2: Serve the application
FROM nginx:alpine

# Copy the build output from the previous stage to the Nginx HTML directory
COPY --from=build /app/dist/editor/ /usr/share/nginx/html

# Copy a custom Nginx configuration file, if needed (optional)
# COPY nginx.conf /etc/nginx/nginx.conf

# Expose the default Nginx port
EXPOSE 80

# Start the Nginx server
CMD ["nginx", "-g", "daemon off;"]