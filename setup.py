import json
from setuptools.command import build_ext
from setuptools import setup, Extension
import sys
import os
import io
from setuptools.command.install import install
import platform
import shutil
from pathlib import Path
import site

dbr_lib_dir = ''
dbr_include = ''
dbr_lib_name = 'DynamsoftLabelRecognizer'

if sys.platform == "linux" or sys.platform == "linux2":
    # Linux
    dbr_lib_dir = 'lib/linux'
elif sys.platform == "win32":
    # Windows
    dbr_lib_name = 'DynamsoftLabelRecognizerx64'
    dbr_lib_dir = 'lib/win'

if sys.platform == "linux" or sys.platform == "linux2":
    ext_args = dict(
        library_dirs=[dbr_lib_dir],
        extra_compile_args=['-std=c++11'],
        extra_link_args=["-Wl,-rpath=$ORIGIN"],
        libraries=[dbr_lib_name],
        include_dirs=['include']
    )


long_description = io.open("README.md", encoding="utf-8").read()

if sys.platform == "linux" or sys.platform == "linux2" or sys.platform == "darwin":
    module_mrzscanner = Extension(
        'mrzscanner', ['src/mrzscanner.cpp'], **ext_args)
else:
    module_mrzscanner = Extension('mrzscanner',
                                  sources=['src/mrzscanner.cpp'],
                                  include_dirs=['include'], library_dirs=[dbr_lib_dir], libraries=[dbr_lib_name])


def copyfiles(src, dst):
    if os.path.isdir(src):
        filelist = os.listdir(src)
        for file in filelist:
            libpath = os.path.join(src, file)
            shutil.copy2(libpath, dst)
    else:
        shutil.copy2(src, dst)

def updateConfigFile(config_file):
    try:
        # open json file
        with open(config_file, 'r+') as f:
            data = json.load(f)
            # before
            print(data['CharacterModelArray'][0]['DirectoryPath'])
            # after
            data['CharacterModelArray'][0]['DirectoryPath'] = os.path.join(os.path.dirname(config_file), 'model')
            print(data['CharacterModelArray'][0]['DirectoryPath'])
            
            # write json file
            f.seek(0) # rewind
            f.write(json.dumps(data))
    except Exception as e:
        print(e)
        pass

class CustomBuildExt(build_ext.build_ext):
    def run(self):
        build_ext.build_ext.run(self)
        dst = os.path.join(self.build_lib, "mrzscanner")
        copyfiles(dbr_lib_dir, dst)
        filelist = os.listdir(self.build_lib)
        for file in filelist:
            filePath = os.path.join(self.build_lib, file)
            if not os.path.isdir(file):
                copyfiles(filePath, dst)
                # delete file for wheel package
                os.remove(filePath)

        model_dest = os.path.join(dst, 'model')
        if (not os.path.exists(model_dest)):
            os.mkdir(model_dest)

        copyfiles(os.path.join(os.path.join(
            Path(__file__).parent, 'model')), model_dest)
        shutil.copy2('MRZ.json', dst)

        # Update model configuration for package installation directory
        packages = site.getsitepackages()
        print(packages)
        for package in packages:
            if 'site-packages' in package:
                try:
                    # configure model path in MRZ.json
                    config_file = os.path.join(dst, 'MRZ.json')
                    # open json file
                    with open(config_file, 'r+') as f:
                        data = json.load(f)
                        # before
                        print(data['CharacterModelArray'][0]['DirectoryPath'])
                        # after
                        data['CharacterModelArray'][0]['DirectoryPath'] = os.path.join(package, 'mrzscanner', 'model')
                        print(data['CharacterModelArray'][0]['DirectoryPath'])
                        
                        # write json file
                        f.seek(0) # rewind
                        f.write(json.dumps(data))
                except Exception as e:
                    print(e)
                    pass
                break

class CustomBuildExtDev(build_ext.build_ext):
    def run(self):
        build_ext.build_ext.run(self)
        dev_folder = os.path.join(Path(__file__).parent, 'mrzscanner')
        copyfiles(dbr_lib_dir, dev_folder)
        filelist = os.listdir(self.build_lib)
        for file in filelist:
            filePath = os.path.join(self.build_lib, file)
            if not os.path.isdir(file):
                copyfiles(filePath, dev_folder)

        model_dest = os.path.join(dev_folder, 'model')
        if (not os.path.exists(model_dest)):
            os.mkdir(model_dest)

        copyfiles(os.path.join(os.path.join(
            Path(__file__).parent, 'model')), model_dest)
        shutil.copy2('MRZ.json', dev_folder)
        
        updateConfigFile(os.path.join(dev_folder, 'MRZ.json'))


class CustomInstall(install):
    def run(self):
        install.run(self)


setup(name='mrz-scanner-sdk',
      version='1.0.4',
      description='Machine readable zone (MRZ) reading SDK for passport, Visa, ID card and travel document.',
      long_description=long_description,
      long_description_content_type="text/markdown",
      author='yushulx',
      url='https://github.com/yushulx/python-mrz-scanner-sdk',
      license='MIT',
      packages=['mrzscanner'],
      ext_modules=[module_mrzscanner],
      classifiers=[
           "Development Status :: 5 - Production/Stable",
           "Environment :: Console",
           "Intended Audience :: Developers",
          "Intended Audience :: Education",
          "Intended Audience :: Information Technology",
          "Intended Audience :: Science/Research",
          "License :: OSI Approved :: MIT License",
          "Operating System :: Microsoft :: Windows",
          "Operating System :: MacOS",
          "Operating System :: POSIX :: Linux",
          "Programming Language :: Python",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3 :: Only",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: 3.7",
          "Programming Language :: Python :: 3.8",
          "Programming Language :: Python :: 3.9",
          "Programming Language :: Python :: 3.10",
          "Programming Language :: C++",
          "Programming Language :: Python :: Implementation :: CPython",
          "Topic :: Scientific/Engineering",
          "Topic :: Software Development",
      ],
      install_requires=['opencv-python', 'mrz'],
      entry_points={
          'console_scripts': ['scanmrz=mrzscanner.scripts:scanmrz']
      },
      cmdclass={
          'install': CustomInstall,
          'build_ext': CustomBuildExt,
          'develop': CustomBuildExtDev},
      )
