# Use the base image (Python 3.8+ recommended)
FROM python:3.8-slim

# Set the working directory inside the container
WORKDIR /app/ctrl

# Copy the contents of the current directory into the container
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Streamlit or Flask uses (if applicable)(to be modified)
EXPOSE 5000 

# Define the entry point for your container
CMD ["python", "MergeCtrl.py"]  
