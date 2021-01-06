FROM ubuntu:18.04

ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

# Install Python3 etc
RUN apt-get update && apt-get install -y \
  build-essential \
  wget \
  xz-utils \
  ffmpeg \
  libssl1.0.0 \
  libasound2 \
  python3 \
  python3-pip

COPY ./ ./

RUN pip3 install --upgrade pip
RUN pip3 install -r requirements.txt

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8

EXPOSE 80

CMD streamlit run app.py