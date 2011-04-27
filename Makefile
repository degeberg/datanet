# vim: noet

TARGET=assignment1

make-archive: clean
	mkdir build
	cp -r src build/$(TARGET)
	rm -f build/**/*.py[oc]
	rm -rf build/${TARGET}/__pycache__
	(cd build && tar zcf $(TARGET).tar.gz ${TARGET})

clean:
	rm -rf build

.PHONY: make-archive clean
