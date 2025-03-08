FROM debian:stable-slim

USER root

RUN apt update
RUN apt install python3 python3-pip wget -y

RUN wget https://www.deb-multimedia.org/pool/main/d/deb-multimedia-keyring/deb-multimedia-keyring_2024.9.1_all.deb
RUN dpkg -i deb-multimedia-keyring_2024.9.1_all.deb

RUN echo "deb https://www.deb-multimedia.org bookworm main non-free" > /etc/apt/sources.list.d/multimedia.list

RUN apt update
RUN apt upgrade -y

RUN apt install vapoursynth vapoursynth-ocr vapoursynth-ffms2 -y

# API port
EXPOSE 5000

COPY . /app
WORKDIR /app

RUN pip3 install -r requirements.txt --break-system-packages

CMD ["python3", "bot.py"]
#CMD ["python3", "telegram_bot.py", "&", "python3", "queue_bot.py", "&", "python3", "bot.py"]

