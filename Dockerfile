FROM python:3.6

RUN useradd --user-group bagit-tester && \
    install -d -o bagit-tester /bagit && \
    apt-get update && apt-get install -y gettext && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
WORKDIR /bagit
COPY .git/ /bagit/.git/
COPY *.rst *.py /bagit/
COPY test-data /bagit/test-data/
RUN chown -R bagit-tester /bagit
USER bagit-tester
CMD [ "python", "setup.py", "test" ]
