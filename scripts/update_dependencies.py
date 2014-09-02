#!/usr/bin/env python

"""
Updates the dependency lists in makefile.deps for all object files produced
from sources in src and subfolders, so that changing a header file always
leads to the recompilation of all the files depending on this header.
"""

import os, re, fnmatch, util2, update_vs, update_vs2008
pjoin = os.path.join

DIRS = ["src", pjoin("src", "utils"), pjoin("src", "installer"), pjoin("src", "ifilter"), pjoin("src", "previewer"), pjoin("src", "mui"), pjoin("src", "memtrace"), pjoin("src", "regress"), pjoin("src", "uia"), pjoin("ext", "unarr"), pjoin("ext", "unarr", "common"), pjoin("ext", "unarr", "rar"), pjoin("ext", "unarr", "zip"), pjoin("ext", "unarr", "_7z")]
INCLUDE_DIRS = DIRS + [pjoin("mupdf", "include"), pjoin("ext", "bzip2"), pjoin("ext", "CHMlib", "src"), pjoin("ext", "freetype2", "include"), pjoin("ext", "jbig2dec"), pjoin("ext", "libdjvu"), pjoin("ext", "libjpeg-turbo"), pjoin("ext", "libwebp"), pjoin("ext", "lzma", "C"), pjoin("ext", "openjpeg"), pjoin("ext", "synctex"), pjoin("zlib")]
OBJECT_DIRS = { "src\\utils": "$(OU)", "src\\ifilter": "$(ODLL)", "src\\previewer": "$(ODLL)", "src\\mui": "$(OMUI)", "src\\memtrace": "$(OM)", "src\\uia": "$(OUIA)", "ext\\unarr": "$(OUN)", "ext\\unarr\\common": "$(OUN)", "ext\\unarr\\rar": "$(OUN)", "ext\\unarr\\zip": "$(OUN)" } # default: "$(OS)"
MAKEFILE = "makefile.deps"
DEPENDENCIES_PER_LINE = 3

def prependPath(files, basefile=None):
	result = []
	include_dirs = INCLUDE_DIRS
	if basefile:
		include_dirs = [os.path.dirname(basefile)] + include_dirs

	for file in files:
		if file in ["string.h", "math.h"]:
			continue # skip names of system headers which also exist in mupdf/include/mupdf/fitz
		for dir in include_dirs:
			path = os.path.normpath(pjoin(dir, file))
			if os.path.exists(path):
				result.append(path)
				break
	return result

def getObjectPath(file):
	file = file.replace("/", "\\")
	for (path, odir) in OBJECT_DIRS.items():
		if file.startswith(path + "\\"):
			return odir
	return "$(OS)"

@util2.memoize
def extractIncludes(file):
	content = open(file, "r").read()
	content = content.replace("\r\n", "\n")
	# filter out multi-line comments (could contain #include lines as examples)
	content = re.sub(r'(?s)/\*.*?\*/', '/* */', content)
	# try to filter out "#if 0 ... #endif" sections (hacky)
	content = re.sub(r'(?sm)^#if 0$.*?^#endif$', '', content)
	includes = re.findall(r'(?m)^#include ["<]([^">]+)[">]', content)
	includes = prependPath(includes, file)

	for inc in includes:
		includes += extractIncludes(inc)
	return util2.uniquify(includes)

def createDependencyList():
	dependencies = {}
	for dir in DIRS:
		all_c_files = fnmatch.filter(os.listdir(dir), "*.c*")
		for file in all_c_files:
			file = pjoin(dir, file)
			dependencies[file] = extractIncludes(file)
	return dependencies

def flattenDependencyList(dependencies):
	flatlist = []
	for file in dependencies.keys():
		if dependencies[file]:
			opath = getObjectPath(file)
			filename = os.path.splitext(os.path.split(file)[1])[0]
			# TODO: normalizing paths already in prependPath makes getObjectPath fail under cygwin
			deplist = sorted(dependencies[file], key=lambda s: str.lower(s.replace("/", "\\")))
			for depgroup in util2.group(deplist, DEPENDENCIES_PER_LINE):
				flatlist.append("%s\\%s.obj: $B\\%s" % (opath, filename, " $B\\".join(depgroup)))
	return flatlist

def normalizePaths(paths):
	return re.sub(r"( |\\)[^.\\\s]+\\..\\", r"\1", paths.replace("/", "\\"))

def injectDependencyList(flatlist):
	flatlist = "\n".join(sorted(flatlist, key=str.lower))
	flatlist = normalizePaths(flatlist)
	content  = "## Header-dependencies for src\* and src\*\*\n"
	content += "### the list below is auto-generated by update_dependencies.py\n"
	content += "B=$(BASEDIR)\n"
	content += flatlist + "\n"

	open(MAKEFILE, "wb").write(content.replace("\n", "\r\n"))

def main():
	util2.chdir_top()
	injectDependencyList(flattenDependencyList(createDependencyList()))

if __name__ == "__main__":
	main()
	update_vs.main()
	update_vs2008.main()
