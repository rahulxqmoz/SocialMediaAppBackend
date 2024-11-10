# Use the official Python image from the Docker Hub
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR /app

# Install dependencies
COPY ./requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the Django project code into the Docker image
COPY ./socialapp /app 

EXPOSE 8000
# Expose the port
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "socialapp.asgi:application"]
