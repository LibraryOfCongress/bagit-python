FROM python:3.14
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
RUN pip install --upgrade pip && pip install uv && uv sync --all-extras
RUN mkdir /home/bagit-tester/ && mkdir /home/bagit-tester/.cache && mkdir /home/bagit-tester/.cache/uv
RUN chown bagit-tester /home/bagit-tester/.cache/uv
USER bagit-tester
CMD [ "uv", "run", "pytest" ]
