from skbuild import setup
import io

long_description = io.open("README.md", encoding="utf-8").read()
packages = ['mrzscanner']

setup(name='mrz-scanner-sdk',
      version='1.0.0',
      description='Machine readable zone (MRZ) reading SDK for passport, Visa, ID card and travel document.',
      long_description=long_description,
      long_description_content_type="text/markdown",
      author='yushulx',
      url='https://github.com/yushulx/python-mrz-scanner-sdk',
      license='MIT',
      packages=packages,
      include_package_data=False,
      classifiers=[
           "Development Status :: 5 - Production/Stable",
           "Environment :: Console",
          "Intended Audience :: Developers",
          "Intended Audience :: Education",
          "Intended Audience :: Information Technology",
          "Intended Audience :: Science/Research",
          "License :: OSI Approved :: MIT License",
          "Operating System :: Microsoft :: Windows",
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
      }
      )
