#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""
import os
from setuptools import setup, find_packages
from distutils.core import Extension

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    # TODO: put package requirements here
]

setup_requirements = [
    'pytest-runner',
    # TODO(paulross): put setup requirements (distutils extensions, etc.) here
]

test_requirements = [
    'pytest',
    # TODO: put package test requirements here
]


extra_compile_args = [
    '-Wall',
    '-Wextra',
    '-Werror',
    '-Wfatal-errors',
    '-Wpedantic',
    # Some internal Python library code does not like this with C++11.
    # '-Wno-c++11-compat-deprecated-writable-strings',
    # '-std=c++11',
    '-std=c99',
    # Until we use m_coalesce
    # '-Wno-unused-private-field',

    # # Temporary
    # '-Wno-unused-variable',
    # '-Wno-unused-parameter',
]

DEBUG = False

if DEBUG:
    extra_compile_args.extend(['-g3', '-O0', '-DDEBUG=1', '-UNDEBUG'])
else:
    extra_compile_args.extend(['-O3', '-UDEBUG', '-DNDEBUG'])

setup(
    name='pymemtrace',
    version='0.1.0',
    description="Python memory tracing.",
    long_description=readme + '\n\n' + history,
    author="Paul Ross",
    author_email='apaulross@gmail.com',
    url='https://github.com/paulross/pymemtrace',
    packages=find_packages('pymemtrace'),  # include=['pymemtrace']),
    package_dir={'': 'pymemtrace'},
    include_package_data=True,
    install_requires=requirements,
    license="MIT license",
    zip_safe=False,
    keywords='pymemtrace',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    setup_requires=setup_requirements,
    ext_modules=[
        Extension(
            "custom",
            sources=[
              'pymemtrace/src/cpy/cCustom.c',
            ],
            include_dirs=[
                '/usr/local/include',
                # os.path.join('pymemtrace', 'src', 'include'),
            ],
            library_dirs=[os.getcwd(), ],  # path to .a or .so file(s)
            extra_compile_args=extra_compile_args,
        ),
        Extension(
            "cPyMemTrace",
            sources=[
              'pymemtrace/src/c/get_rss.c',
              'pymemtrace/src/c/pymemtrace_util.c',
              'pymemtrace/src/cpy/cPyMemTrace.c',
            ],
            include_dirs=[
                '/usr/local/include',
                os.path.join('pymemtrace', 'src', 'include'),
            ],
            library_dirs=[os.getcwd(), ],  # path to .a or .so file(s)
            extra_compile_args=extra_compile_args,
        ),
        Extension(
            "cMemLeak",
            sources=[
              'pymemtrace/src/cpy/cMemLeak.c',
            ],
            include_dirs=[
                '/usr/local/include',
                # os.path.join('pymemtrace', 'src', 'include'),
            ],
            library_dirs=[os.getcwd(), ],  # path to .a or .so file(s)
            extra_compile_args=extra_compile_args,
        ),
    ]
)
