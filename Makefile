COMPILED_MESSAGES=$(patsubst %.po,%.mo, $(wildcard locale/*/LC_MESSAGES/bagit-python.po))

all: messages compile

clean:
	rm -f src/bagit/locale/*/LC_MESSAGES/*.mo

messages:
	xgettext --language=python -d bagit-python --no-location -o src/bagit/locale/bagit-python.pot src/bagit/__init__.py
	# Until http://savannah.gnu.org/bugs/?20923 is fixed:
	sed -i '' -e 's/CHARSET/UTF-8/g' src/bagit/locale/bagit-python.pot
	msgmerge --no-fuzzy-matching --lang=en --output-file=src/bagit/locale/en/LC_MESSAGES/bagit-python.po src/bagit/locale/en/LC_MESSAGES/bagit-python.po src/bagit/locale/bagit-python.pot

%.mo: %.po
	msgfmt -o $@ $<

compile: $(COMPILED_MESSAGES)
