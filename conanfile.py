#!/usr/bin/env python
# -*- coding: utf-8 -*-

from conans import ConanFile, CMake, tools
import os


class FreetypeConan(ConanFile):
    name = "freetype"
    version = "2.8.1"
    description = "FreeType is a freely available software library to render fonts."
    url = "http://github.com/bincrafters/conan-freetype"
    homepage = "https://www.freetype.org"
    license = "BSD"
    author = "Bincrafters <bincrafters@gmail.com>"
    exports = ["LICENSE.md", "FindFreetype.cmake"]
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
    default_options = (
        "shared=False", 
        "fPIC=True", 
        "with_png=True", 
        "with_zlib=True",
        "with_bzip2=True",
    )
    source_subfolder = "source_subfolder"
    build_subfolder = "build_subfolder"

    def requirements(self):
        if self.options.with_png:
            self.requires.add("libpng/1.6.34@bincrafters/stable")
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
        source_url = "http://downloads.sourceforge.net/project/freetype/freetype2"
        version = self.version[:-2]
        archive_file = '{0}-{1}.tar.gz'.format(self.name, version)
        source_file = '{0}/{1}/{2}'.format(source_url, version, archive_file)
        tools.get(source_file)
        os.rename('{0}-{1}'.format(self.name, version), self.source_subfolder)
        self.patch_windows()

    def patch_windows(self):
        if self.settings.os == "Windows":
            pattern = 'if (WIN32 AND NOT MINGW AND BUILD_SHARED_LIBS)\n' + \
                      '  message(FATAL_ERROR "Building shared libraries on Windows needs MinGW")\n' + \
                      'endif ()\n'
            cmake_file = os.path.join(self.source_subfolder, 'CMakeLists.txt')
            tools.replace_in_file(cmake_file, pattern, '')

    def configure_cmake(self):
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
        if self.settings.os != "Windows":
            cmake.definitions['CMAKE_POSITION_INDEPENDENT_CODE'] = self.options.fPIC
        elif self.settings.os == "Windows" and self.settings.compiler == "Visual Studio":
            cmake.definitions['CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS'] = self.options.shared
        cmake.definitions["WITH_ZLIB"] = self.options.with_zlib
        cmake.definitions["WITH_PNG"] = self.options.with_png
        cmake.definitions["WITH_HARFBUZZ"] = False
        cmake.definitions["CMAKE_DISABLE_FIND_PACKAGE_HarfBuzz"] = True
        cmake.configure(build_dir=self.build_subfolder)
        return cmake

    def build(self):
        cmake = self.configure_cmake()
        cmake.build()

    def package(self):
        cmake = self.configure_cmake()
        cmake.install()
        self.copy("FindFreetype.cmake")
        self.copy("FTL.TXT", dst="licenses", src=os.path.join(self.source_subfolder, "docs"))
        self.copy("GPLv2.TXT", dst="licenses", src=os.path.join(self.source_subfolder, "docs"))
        self.copy("LICENSE.TXT", dst="licenses", src=os.path.join(self.source_subfolder, "docs"))

    def package_info(self):
        self.cpp_info.libs = tools.collect_libs(self)
        if self.settings.os == "Linux":
            self.cpp_info.libs.append("m")
        self.cpp_info.includedirs.append(os.path.join("include", "freetype2"))
