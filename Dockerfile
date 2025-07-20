FROM python:3.10.4-slim-buster

# 🛠 Fix Debian Buster repo errors and update system
RUN sed -i 's|http://deb.debian.org|http://archive.debian.org|g' /etc/apt/sources.list && \
    sed -i '/security.debian.org/s/^/#/' /etc/apt/sources.list && \
    apt-get update && apt-get upgrade -y

# ✅ Install required packages
RUN apt-get install -y \
    git \
    curl \
    wget \
    python3-pip \
    bash \
    neofetch \
    ffmpeg \
    software-properties-common

# 📦 Python dependencies
COPY requirements.txt .
RUN pip3 install wheel
RUN pip3 install --no-cache-dir -U -r requirements.txt

# 📁 App setup
WORKDIR /app
COPY . .

# 🌐 Expose port
EXPOSE 5000

# 🚀 Run app
CMD flask run -h 0.0.0.0 -p 5000 & python3 -m devgagan
