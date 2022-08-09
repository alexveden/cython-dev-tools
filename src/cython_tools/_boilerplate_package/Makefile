PROJ_ROOT:=$(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

p ?= $(PROJ_ROOT)
#GDB_EXECUTABLE:=/usr/local/bin/gdb13
GDB_EXECUTABLE:=gdb

CYTOOL:=./cytool

# Python execution which should be used for building module, in debug mode
#   Typically original python is fine for debugging cython modules, but if you need more debug info (python symbols)
# 	you should build or install debug version of python
#
PY_EXEC:=python
#PY_EXEC:=python-dbg

TEST_EXEC:=pytest


.PHONY: build build-debug tests coverage debug-file debug-tests debug-valgrind

build:
	$(CYTOOL) build

tests: build
	export PYTHONPATH=$(PROJ_ROOT):$(PYTHONPATH); python -m $(TEST_EXEC) $(p)
