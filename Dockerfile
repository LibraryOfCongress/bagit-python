FROM ghcr.io/astral-sh/uv:0.11.5-python3.14-trixie
RUN useradd --user-group bagit-tester
RUN install -d -o bagit-tester /bagit
WORKDIR /bagit
COPY pyproject.toml /bagit/pyproject.toml
COPY .git/ /bagit/.git/
COPY *.rst /bagit/
COPY src/ /bagit/src/
COPY test.py /bagit/
COPY test-data /bagit/test-data/
COPY utils/ /bagit/
ENV UV_LINK_MODE=copy
RUN mkdir /home/bagit-tester/ && mkdir /home/bagit-tester/.cache && mkdir /home/bagit-tester/.cache/uv && \
    apt-get update && apt-get install dos2unix -y && find test-data -name 'README' |xargs dos2unix
RUN chown bagit-tester /home/bagit-tester/.cache/uv
USER bagit-tester
CMD [ "uv", "run", "pytest" ]
