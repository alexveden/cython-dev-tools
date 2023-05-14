PROJ_ROOT:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

p ?= $(PROJ_ROOT)
#GDB_EXECUTABLE:=/usr/local/bin/gdb13
GDB_EXECUTABLE:=gdb

CYTOOL:=cytool

# Python execution which should be used for building module, in debug mode
#   Typically original python is fine for debugging cython modules, but if you need more debug info (python symbols)
# 	you should build or install debug version of python
#
PY_EXEC:=python
#PY_EXEC:=python-dbg

TEST_EXEC:=pytest


.PHONY: build-production build-debug tests tests-debug tests-valgrind run debug lprun-file annotate annotate-file coverage clean

build-production:
	$(CYTOOL) build

build-debug:
	$(CYTOOL) build --debug --annotate

tests: build-debug
	$(CYTOOL) tests $(p)

tests-valgrind: build-debug
	$(CYTOOL) valgrind -t $(p)

tests-debug: build-debug
	$(CYTOOL) debug -t $(p)

run: build-debug
	$(CYTOOL) run $(p)

debug: build-debug
	$(CYTOOL) debug $(p)

lprun-file: build-debug
	$(CYTOOL) lprun cy_tools_samples/profiler/cy_module.pyx@approx_pi2"(10)" -m cy_tools_samples/profiler/cy_module.pyx

annotate-file: build-debug
	$(CYTOOL) annotate $(p) --browser

coverage: build-debug
	$(CYTOOL) cover $(p) --browser

annotate: build-debug
	$(CYTOOL) annotate $(p) --browser

clean:
	$(CYTOOL) clean -y -b