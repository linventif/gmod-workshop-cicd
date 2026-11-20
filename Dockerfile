# syntax=docker/dockerfile:1
# Compile the standalone official tool; never download the GMod server.
FROM ubuntu:22.04 AS gmad-build
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential ca-certificates curl premake4 \
 && rm -rf /var/lib/apt/lists/*

# Pin upstream revisions so cache hits and tool updates are intentional.
ARG BOOTIL_REV=d8db9cb21255b62029e5c00da3d311f03f07ad8f
ARG GMAD_REV=8cc36b9f3386f1afd049e85a8f31e3745bbd0c4d
RUN mkdir -p /build/bootil /build/gmad \
 && curl -fsSL --retry 3 "https://github.com/garrynewman/bootil/archive/${BOOTIL_REV}.tar.gz" -o /tmp/bootil.tar.gz \
 && tar -xzf /tmp/bootil.tar.gz --strip-components=1 -C /build/bootil \
 && curl -fsSL --retry 3 "https://github.com/Facepunch/gmad/archive/${GMAD_REV}.tar.gz" -o /tmp/gmad.tar.gz \
 && tar -xzf /tmp/gmad.tar.gz --strip-components=1 -C /build/gmad
WORKDIR /build/bootil/projects
RUN premake4 gmake \
 && make -C linux/gmake config=release -j2
WORKDIR /build/gmad
RUN premake4 --outdir=bin --bootil_lib=/build/bootil/lib/linux/gmake --bootil_inc=/build/bootil/include gmake \
 && make config=release -j2 \
 && strip bin/gmad_linux

FROM ubuntu:22.04 AS runtime-base
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends ca-certificates lib32gcc-s1 lib32stdc++6 libstdc++6 python3 \
 && rm -rf /var/lib/apt/lists/*

FROM runtime-base AS steamcmd-build
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl \
 && mkdir /steamcmd \
 && curl -fsSL --retry 3 https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz -o /tmp/steamcmd.tar.gz \
 && tar -xzf /tmp/steamcmd.tar.gz -C /steamcmd
# Bootstrap during the image build, rather than on every publication.
RUN /steamcmd/steamcmd.sh +quit

FROM runtime-base AS runtime
COPY --from=gmad-build /build/gmad/bin/gmad_linux /usr/local/bin/gmad
COPY --from=steamcmd-build /steamcmd /steamcmd
WORKDIR /app
COPY entrypoint.sh otp.py workshop.py ./
ENTRYPOINT ["bash", "/app/entrypoint.sh"]
