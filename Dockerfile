# Linux only
FROM ubuntu:22.04
ENV DEBIAN_FRONTEND=noninteractive

# 1) Installer les dépendances système
RUN dpkg --add-architecture i386 \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
      ca-certificates \
      wget \
      unzip \
      lib32gcc-s1 \
      lib32stdc++6 \
      python3 \
      python3-venv \
      dos2unix \
      gettext-base \
 && rm -rf /var/lib/apt/lists/*

# 2) Créer un virtualenv et installer pyotp + steampy
RUN python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir pyotp steampy

# 3) Installer SteamCMD
RUN mkdir -p /steamcmd \
 && cd /steamcmd \
 && wget -qO- https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz \
      | tar zxvf - \
 && chmod +x steamcmd.sh

# 4) Installer GMod DS pour gmad
# Run steamcmd twice: first to initialize, then to actually install
RUN mkdir -p /gmod_ds \
 && /steamcmd/steamcmd.sh \
     +@sSteamCmdForcePlatformType linux \
     +login anonymous \
     +quit \
 && /steamcmd/steamcmd.sh \
     +@sSteamCmdForcePlatformType linux \
     +force_install_dir /gmod_ds \
     +login anonymous \
     +app_update 4020 validate \
     +quit \
 && ln -s /gmod_ds/bin/gmad_linux /usr/local/bin/gmad

# 5) Copier les scripts d’entrée
WORKDIR /app
COPY entrypoint.sh otp.py ./

RUN dos2unix entrypoint.sh \
 && chmod +x entrypoint.sh

# 6) Point d’entrée
ENTRYPOINT ["bash","-lc","source /opt/venv/bin/activate && /app/entrypoint.sh"]
