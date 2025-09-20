# Use a minimal, non-root base image for security
FROM gcr.io/distroless/static-debian11:debug

# Set the working directory
WORKDIR /app

# Copy the toolbox binary and the configuration file into the image
COPY ./toolbox .
COPY ./tools.yaml .

# Expose the port the server will run on
EXPOSE 8080

# The command to run the server. It will listen on all interfaces.
ENTRYPOINT ["/app/toolbox", "--tools-file=/app/tools.yaml", "--address=0.0.0.0", "--port=8080"]
