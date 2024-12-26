# Use the base image (Python 3.8+ recommended)
FROM python:3.8-slim

# Upgrade pip to the latest version
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean \
    && python -m pip install --upgrade pip

# Set the working directory inside the container
WORKDIR /app/ctrl

# Copy the contents of the current directory into the container
COPY . .


# Install Python dependencies using the updated pip
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port Streamlit or Flask uses (if applicable)
EXPOSE 5000 

# Define the entry point for your container
CMD ["python", "MergeCtrl.py"]
