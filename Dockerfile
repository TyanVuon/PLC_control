# Use an NVIDIA CUDA image with Ubuntu 22.04 as the base
FROM nvidia/cuda:12.3.2-devel-ubuntu22.04

# Set non-interactive environment to avoid prompts
ENV DEBIAN_FRONTEND=noninteractive

# Update and install essential packages and Python
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment, then install dependencies
RUN python3 -m venv /venv && \
    /venv/bin/pip install --upgrade pip && \
    /venv/bin/pip install \
        torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 && \
    /venv/bin/pip install \
        datasets transformers[torch] grad-cam opencv-python pyserial

# Set the virtual environment path in the container’s PATH
ENV PATH="/venv/bin:$PATH"

# Set up working directory and copy project files
WORKDIR /workspace
COPY . /workspace

# Specify default command for the container
CMD ["/bin/bash"]
