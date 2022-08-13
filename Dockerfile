FROM fcreplay/base:latest as fightcade-stage

LABEL maintainer="glisignoli"

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

FROM fcreplay/base:latest as flags-stage 
# Download flag icons for thumbnails
RUN cd /opt && \
  git clone https://github.com/hampusborgos/country-flags.git ./flags

FROM fcreplay/base:latest as fonts-stage
# Add fonts for thumbnails
RUN cd /opt && \
  git clone https://github.com/grays/droid-fonts.git

FROM fcreplay/base:latest as fcreplay-stage
# Install fcreplay
RUN mkdir /root/fcreplay
COPY requirements.txt /root/fcreplay
COPY setup.py /root/setup.py
RUN cd /root && python3 setup.py install
RUN cd /root/fcreplay && pip3 install -r requirements.txt
COPY fcreplay /root/fcreplay

FROM fcreplay/base:latest as i3-stage
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


# Copy Stages
COPY --from=fightcade-stage /Fightcade /Fightcade
COPY --from=flags-stage /opt/flags /opt/flags
COPY --from=fonts-stage /opt/droid-fonts /opt/droid-fonts
COPY --from=fcreplay-stage /root/fcreplay /root/fcreplay

CMD ["fcrecord"]
ENTRYPOINT ["/docker-entrypoint.sh"]
