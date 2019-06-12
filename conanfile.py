#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, CMake, tools
import os
import shutil


class FreetypeConan(ConanFile):
    name = "freetype"
    version = "2.9.1"
    description = "FreeType is a freely available software library to render fonts."
    url = "http://github.com/bincrafters/conan-freetype"
    homepage = "https://www.freetype.org"
    license = "FTL"
    topics = ("conan", "freetype", "fonts")
    author = "Bincrafters <bincrafters@gmail.com>"
    exports = ["LICENSE.md"]
    exports_sources = ["CMakeLists.txt", "freetype.pc.in"]
    generators = "cmake"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_png": [True, False],
        "with_zlib": [True, False],
        "with_bzip2": [True, False],
    }
    default_options = {
        'shared': False,
        'fPIC': True,
        'with_png': True,
        'with_zlib': True,
        'with_bzip2': True
    }
    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    def requirements(self):
        if self.options.with_png:
            self.requires.add("libpng/1.6.36@bincrafters/stable")
        if self.options.with_zlib:
            self.requires.add("zlib/1.2.11@conan/stable")
        if self.options.with_bzip2:
            self.requires.add("bzip2/1.0.6@conan/stable")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        del self.settings.compiler.libcxx

    def source(self):
        source_url = "https://download.savannah.gnu.org/releases/"
        version = self.version[:-2]
        archive_file = '{0}-{1}.tar.gz'.format(self.name, version)
        source_file = '{0}/{1}/{2}'.format(source_url, self.name, archive_file)
        sha256 = "bf380e4d7c4f3b5b1c1a7b2bf3abb967bda5e9ab480d0df656e0e08c5019c5e6"
        tools.get(source_file, sha256=sha256)
        os.rename('{0}-{1}'.format(self.name, version), self._source_subfolder)
        self._patch_windows()

    def _patch_windows(self):
        if self.settings.os == "Windows":
            pattern = 'if (WIN32 AND NOT MINGW AND BUILD_SHARED_LIBS)\n' + \
                      '  message(FATAL_ERROR "Building shared libraries on Windows needs MinGW")\n' + \
                      'endif ()\n'
            cmake_file = os.path.join(self._source_subfolder, 'CMakeLists.txt')
            tools.replace_in_file(cmake_file, pattern, '')

    def _patch_msvc_mt(self):
        if self.settings.os == "Windows" and \
           self.settings.compiler == "Visual Studio" and \
           "MT" in self.settings.compiler.runtime:
            header_file = os.path.join(self._source_subfolder, "include", "freetype", "config", "ftconfig.h")
            tools.replace_in_file(header_file, "#ifdef _MSC_VER", "#if 0")

    def _configure_cmake(self):
        cmake = CMake(self)
        system_libraries = ''
        if self.settings.os == 'Linux':
            system_libraries = '-lm'
        cmake.definitions["PC_SYSTEM_LIBRARIES"] = system_libraries
        cmake.definitions["PC_FREETYPE_LIBRARY"] = '-lfreetyped' if self.settings.build_type == 'Debug' else '-lfreetype'
        if self.options.with_png:
            cmake.definitions["PC_PNG_LIBRARY"] = '-l%s' % self.deps_cpp_info['libpng'].libs[0]
        else:
            cmake.definitions["PC_PNG_LIBRARY"] = ''
        if self.options.with_zlib:
            cmake.definitions["PC_ZLIB_LIBRARY"] = '-l%s' % self.deps_cpp_info['zlib'].libs[0]
        else:
            cmake.definitions["PC_ZLIB_LIBRARY"] = ''
        if self.options.with_bzip2:
            cmake.definitions["PC_BZIP2_LIBRARY"] = '-l%s' % self.deps_cpp_info['bzip2'].libs[0]
        else:
            cmake.definitions["PC_BZIP2_LIBRARY"] = ''
        cmake.definitions["PROJECT_VERSION"] = self.version
        cmake.definitions["WITH_ZLIB"] = self.options.with_zlib
        cmake.definitions["WITH_PNG"] = self.options.with_png
        cmake.definitions["WITH_HARFBUZZ"] = False
        cmake.definitions["CMAKE_DISABLE_FIND_PACKAGE_HarfBuzz"] = True
        cmake.configure(build_dir=self._build_subfolder)
        return cmake

    def build(self):
        self._patch_msvc_mt()
        cmake = self._configure_cmake()
        cmake.build()

    def _make_freetype_config(self):
        freetype_config_in = os.path.join(self._source_subfolder, "builds", "unix", "freetype-config.in")
        if not os.path.isdir(os.path.join(self.package_folder, "bin")):
            os.makedirs(os.path.join(self.package_folder, "bin"))
        freetype_config = os.path.join(self.package_folder, "bin", "freetype-config")
        shutil.copy(freetype_config_in, freetype_config)
        libs = "-lfreetyped" if self.settings.build_type == "Debug" else "-lfreetype"
        staticlibs = "-lm %s" % libs if self.settings.os == "Linux" else libs
        libtool_version = "22.0.16"  # check docs/version.txt, this is a different version mumber!
        tools.replace_in_file(freetype_config, r"%PKG_CONFIG%", r"/bin/false")  # never use pkg-config
        tools.replace_in_file(freetype_config, r"%prefix%", r"$conan_prefix")
        tools.replace_in_file(freetype_config, r"%exec_prefix%", r"$conan_exec_prefix")
        tools.replace_in_file(freetype_config, r"%includedir%", r"$conan_includedir")
        tools.replace_in_file(freetype_config, r"%libdir%", r"$conan_libdir")
        tools.replace_in_file(freetype_config, r"%ft_version%", r"$conan_ftversion")
        tools.replace_in_file(freetype_config, r"%LIBSSTATIC_CONFIG%", r"$conan_staticlibs")
        tools.replace_in_file(freetype_config, r"-lfreetype", libs)
        tools.replace_in_file(freetype_config, r"export LC_ALL", """export LC_ALL
BINDIR=$(dirname $0)
conan_prefix=$(dirname $BINDIR)
conan_exec_prefix=${{conan_prefix}}/bin
conan_includedir=${{conan_prefix}}/include
conan_libdir=${{conan_prefix}}/lib
conan_ftversion={version}
conan_staticlibs="{staticlibs}"
""".format(version=libtool_version, staticlibs=staticlibs))

    def package(self):
        cmake = self._configure_cmake()
        cmake.install()
        self._make_freetype_config()
        self.copy("FTL.TXT", dst="licenses", src=os.path.join(self._source_subfolder, "docs"))
        self.copy("GPLv2.TXT", dst="licenses", src=os.path.join(self._source_subfolder, "docs"))
        self.copy("LICENSE.TXT", dst="licenses", src=os.path.join(self._source_subfolder, "docs"))

    @staticmethod
    def _chmod_plus_x(filename):
        if os.name == 'posix':
            os.chmod(filename, os.stat(filename).st_mode | 0o111)

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
        if self.settings.os == "Linux":
            self.cpp_info.libs.append("m")
        self.cpp_info.includedirs.append(os.path.join("include", "freetype2"))
        freetype_config = os.path.join(self.package_folder, "bin", "freetype-config")
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
        self.env_info.FT2_CONFIG = freetype_config
        self._chmod_plus_x(freetype_config)
