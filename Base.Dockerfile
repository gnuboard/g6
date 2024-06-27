FROM python:bookworm AS git-base

ARG user=g6
RUN useradd --create-home --shell /bin/bash $user

WORKDIR /g6
COPY . .

RUN mkdir -p /g6/data
RUN chown -R $user:$user /g6
# Encountering issues with the ownership change of the ./data directory.
# The exact cause is unclear, however, the COPY --chown option does not 
# seem to be working as expected for the ./data directory.
# As a result, we're utilising the RUN command to correctly set the ownership.

RUN find . -mindepth 1 -maxdepth 1 \( -name '.*' ! -name '.' ! -name '..' \) -o \( -name '*.md' -o -name '*.yml' \) -exec bash -c 'echo "Deleting {}"; rm -rf {}' \;

FROM python:bookworm AS env-builder

ARG user=g6
RUN useradd --create-home --shell /bin/bash $user

ARG TARGETARCH
COPY --from=git-base /g6/requirements.txt /g6/requirements.txt

WORKDIR /g6
RUN --mount=target=/var/lib/apt/lists,type=cache,sharing=locked \
    --mount=target=/var/cache/apt,type=cache,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean \
    && apt-get update \
    && apt-get -y --no-install-recommends install \
        locales \
        tini

RUN if [ "$TARGETARCH" = "arm" ]; then \
    apt-get update \
    && apt-get -y install \
        cmake \
        ninja-build \
        build-essential \
        g++ \
        gobjc \
        meson \
        liblapack-dev \
        libblis-dev \
        libblas-dev \
        rustc \
        cargo \
        libopenblas-dev \
        python3-dev; \
    fi

RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen
RUN dpkg-reconfigure --frontend=noninteractive locales
RUN python3 -m venv /venv
RUN /venv/bin/python3 -m pip install -r requirements.txt
COPY --from=git-base --chown=$user:$user /g6 /standby-g6