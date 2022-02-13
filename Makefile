MODULE_DIR	=	/usr/lib/python2.7/site-packages/PyPlucker
BINDIR		=	/usr/local/bin

MKINSTALLDIRS	=	./mkinstalldirs

install: uninstall
	$(MKINSTALLDIRS) $(MODULE_DIR)
	cp -R PyPlucker/* $(MODULE_DIR)
	ln -s $(MODULE_DIR)/Spider.py $(BINDIR)/plucker-build

clean:
	find . -name '*.pyc' -exec $(RM) -f {} \;

uninstall:
	rm -rf $(MODULE_DIR)
	rm $(BINDIR)/plucker-build

