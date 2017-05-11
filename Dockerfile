FROM python:3.6
RUN useradd --user-group bagit-tester
RUN install -d -o bagit-tester /bagit
USER bagit-tester
WORKDIR /bagit
COPY .git/ /bagit/.git/
COPY *.rst *.py /bagit/
COPY test-data /bagit/test-data/
CMD [ "python", "setup.py", "test" ]
