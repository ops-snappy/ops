PYTHON ?= python
DESTDIR ?=
PREFIX ?= /usr

EXTSCHEMAS := $(wildcard schema/*.extschema)
SANE_OVSSCHEMAS := $(patsubst %.extschema,%.ovsschema,$(EXTSCHEMAS))

default: compile

%.ovsschema: %.extschema
	$(PYTHON) schema/sanitize.py $< $@

compile: $(SANE_OVSSCHEMAS)
	touch schema/vswitch.xml

install: compile
	install -d $(DESTDIR)/$(PREFIX)/share/openvswitch
	set -e; cd schema; for f in *.extschema *.ovsschema *.xml; do \
	    install -m 0644 $$f $(DESTDIR)/$(PREFIX)/share/openvswitch/$$f; \
	done

clean:
	rm -rf $(SANE_OVSSCHEMAS)

