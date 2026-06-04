# Use the pre-built environment image
FROM dream-base:latest

# Copy only the application source code
COPY src/ /app/src/

# Set the Python path
ENV PYTHONPATH=/app/src

# Run the main scheduler
CMD ["python", "src/main.py"]
