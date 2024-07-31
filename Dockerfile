FROM python:bookworm AS git-base
WORKDIR /g6
COPY . .
RUN find . -mindepth 1 -maxdepth 1 \( -name '.*' ! -name '.' ! -name '..' \) -o \( -name '*.md' -o -name '*.yml' \) -exec bash -c 'echo "Deleting {}"; rm -rf {}' \;

FROM ghcr.io/navystack/gnuboard-g6:base-nightly AS base
RUN rm -rf /g6/requirements.txt
COPY --from=git-base --chown=$user:$user /g6/requirements.txt /g6/requirements.txt

RUN /venv/bin/python3 -m pip install -r requirements.txt
RUN find . -type f \( -name '__pycache__' -o -name '*.pyc' -o -name '*.pyo' \) -exec bash -c 'echo "Deleting {}"; rm -f {}' \;

FROM python:slim-bookworm AS final

ARG user=g6
RUN useradd --create-home --shell /bin/bash $user

COPY --from=base --chown=$user:$user /standby-g6 /g6
COPY --from=base --chown=$user:$user /venv /venv
COPY --from=base --chown=$user:$user /usr/bin/tini /usr/bin/tini

USER g6
WORKDIR /g6
VOLUME /g6/data
EXPOSE 8000

ENTRYPOINT ["tini", "--"]
# Utilising tini as our init system within the Docker container for graceful start-up and termination.
# Tini serves as an uncomplicated init system, adept at managing the reaping of zombie processes and forwarding signals.
# This approach is crucial to circumvent issues with unmanaged subprocesses and signal handling in containerised environments.
# By integrating tini, we enhance the reliability and stability of our Docker containers.
# Ensures smooth start-up and shutdown processes, and reliable, safe handling of signal processing.

CMD ["/venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]