FROM python:3.10-buster

LABEL maintainer="glisignoli"

# Required packages for build/run
RUN apt-get update && apt-get install -y \
  bash \
  ffmpeg \
  fontconfig \
  git \
  i3 \
  i3status \
  pulseaudio \
  software-properties-common \
  wget \
  x11vnc \
  xterm \
  xvfb \
  zenity \
  zlib1g-dev

RUN apt-add-repository contrib && \
  apt-add-repository non-free

# Newer version of mplayer
RUN apt-get update && apt-get install -y \
  libaa1-dev libasound2-dev libcaca-dev libcdparanoia-dev libdca-dev \
  libdirectfb-dev libenca-dev libfontconfig1-dev libfreetype6-dev \
  libfribidi-dev libgif-dev libgl1-mesa-dev libjack-jackd2-dev libopenal1 libpulse-dev \
  libsdl1.2-dev libvdpau-dev libxinerama-dev libxv-dev libxvmc-dev libxxf86dga-dev \
  libxxf86vm-dev librtmp-dev libsctp-dev libass-dev libfaac-dev libsmbclient-dev libtheora-dev \
  libogg-dev libxvidcore-dev libspeex-dev libvpx-dev libdv4-dev \
  libopencore-amrnb-dev libopencore-amrwb-dev libmp3lame-dev liblivemedia-dev libtwolame-dev \
  libmad0-dev libgsm1-dev libbs2b-dev liblzo2-dev ladspa-sdk libfaad-dev \
  libmpg123-dev libopus-dev libbluray-dev libaacs-dev libx264-dev \
  yasm build-essential

RUN cd /opt && \
  wget http://www.mplayerhq.hu/MPlayer/releases/MPlayer-1.4.tar.xz && \
  tar xvf MPlayer-1.4.tar.xz && \
  cd /opt/MPlayer-1.4 && \
  ./configure --prefix=/opt/mplayer && \
  make && \
  make install && \
  rm -rf /opt/MPlayer-1.4.tar.xz && \
  cd /opt && \
  rm -rf /opt/MPlayer-1.4

RUN dpkg --add-architecture i386 && \
  apt update && \
  apt install -y \
    wine \
    wine32 \
    wine64 \
    libwine \
    libwine:i386 \
    fonts-wine \
    winetricks

RUN pip3 install --upgrade cython pip scikit-build

# Fix wine sound and video recording
RUN winetricks -q avifil32
RUN winetricks -q d3dx9
RUN winetricks sound=pulse

# Download Fightcade linux
RUN cd / && \
  wget https://www.fightcade.com/download/linux && \
  tar xvf linux && \
  mkdir -p /Fightcade/emulator/fbneo/config && \
  mkdir -p /Fightcade/emulator/fbneo/ROMs && \
  rm -rf /linux

# Pre-create 'fightcade' directory
RUN mkdir -p /Fightcade/emulator/fbneo/fightcade

# Copy any 'custom/missing' savestates
COPY ./files/savestates/* /Fightcade/emulator/fbneo/savestates/

# Pre-create 'lua' direcory
RUN mkdir -p /Fightcade/emulator/fbneo/lua

# Copy lua script
COPY ./files/framecount.lua /Fightcade/emulator/fbneo/lua/

# Create empty framecount.txt
RUN echo 0 > /Fightcade/emulator/fbneo/lua/framecount.txt

# Download flag icons for thumbnails
RUN cd /opt && \
  git clone https://github.com/hampusborgos/country-flags.git ./flags

# Add fonts for thumbnails
RUN cd /opt && \
  git clone https://github.com/grays/droid-fonts.git

# Install fcreplay
COPY fcreplay /root/fcreplay
COPY requirements.txt /root/fcreplay
COPY setup.py /root/setup.py
RUN cd /root && python3 setup.py install
RUN cd /root/fcreplay && pip3 install -r requirements.txt


# Setup i3 for autostart
RUN mkdir -p /root/.config/i3
COPY files/i3_config /root/.config/i3/config
COPY files/startup.sh /root/i3_startup.sh
RUN chmod 0755 /root/i3_startup.sh

# Create Xauthroity and empty log file
RUN touch /root/.Xauthority && touch /root/fcreplay.log

# Disable pulseaudio auto suspend
COPY files/default.pa /etc/pulse/default.pa
COPY files/system.pa /etc/pulse/system.pa

# Copy over configuration files for xaudio fix
COPY files/fcadefbneo.default.ini /Fightcade/emulator/fbneo/config/fcadefbneo.default.ini
COPY files/fcadefbneo.ini /Fightcade/emulator/fbneo/config/fcadefbneo.ini

COPY files/docker-entrypoint.sh /docker-entrypoint.sh

# Create an empty config.json file to overwrite with docker
RUN touch /root/config.json

CMD ["fcrecord"]
ENTRYPOINT ["/docker-entrypoint.sh"]
