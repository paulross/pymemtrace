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
    'psutil',
]

setup_requirements = [
    'pytest',
    'pytest-runner',
]

test_requirements = [
    'pytest',
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
    version='0.1.1',
    description="Python memory tracing.",
    long_description=readme + '\n\n' + history,
    long_description_content_type='text/x-rst',
    author="Paul Ross",
    author_email='apaulross@gmail.com',
    url='https://github.com/paulross/pymemtrace',
    packages=find_packages(),  # include=['pymemtrace']),
    include_package_data=True,
    install_requires=requirements,
    license="MIT license",
    zip_safe=False,
    keywords='pymemtrace',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: C',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    setup_requires=setup_requirements,
    # Extensions
    ext_modules=[
        Extension(
            "pymemtrace.custom",
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
            "pymemtrace.cPyMemTrace",
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
            "pymemtrace.cMemLeak",
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
