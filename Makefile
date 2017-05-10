COMPILED_MESSAGES=$(patsubst %.po,%.mo, $(wildcard locale/*/LC_MESSAGES/bagit-python.po))

all: messages compile

clean:
	rm -f locale/*/LC_MESSAGES/*.mo

messages:
	xgettext --language=python -d bagit-python --no-location -o locale/bagit-python.pot bagit.py
	# Until http://savannah.gnu.org/bugs/?20923 is fixed:
	sed -i '' -e 's/CHARSET/UTF-8/g' locale/bagit-python.pot
	msgmerge --no-fuzzy-matching --lang=en --output-file=locale/en/LC_MESSAGES/bagit-python.po locale/en/LC_MESSAGES/bagit-python.po locale/bagit-python.pot

%.mo: %.po
	msgfmt -o $@ $<

compile: $(COMPILED_MESSAGES)
