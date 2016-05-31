FROM python:3.5
RUN mkdir /bagit
WORKDIR /bagit
COPY *.py /bagit/
COPY test-data /bagit/test-data/
CMD [ "python", "setup.py", "test" ]
