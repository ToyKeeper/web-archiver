all:

README.html: README.md
	cmark-gfm -t html README.md > README.html

todo:
	@# find TODOs in the entire project tree
	@grep -r -I -E --exclude=".git/*" --exclude="*~" \
		--exclude="pycfg/*" --exclude="pycfg.py" \
		'TODO:|FIXME:' . | grep -v 'TODO:|FIXME:' \
		| perl -pe 's/:\s+/: /;'
	@#grep -i -I -E 'todo:|fixme:' todo.py
	@echo "=== todo.otl ==="
	@# format todo.otl better
	@grep '\[_\]' todo.otl | perl -ne ' s/\t/  /g; s/\[_\]/-/; s/- (\d\d+)%/+ \1%/; tr/a-z/A-Z/ if /<--/; s/<--/<-----/; print if (/<--/) or (not /^    /);'


