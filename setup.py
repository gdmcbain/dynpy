import os
from setuptools import setup

exec(open('dynpy/version.py').read())

setup(name='dynpy',
      version=__version__,
      description='Dynamical systems for Python',
      author='Artemy Kolchinsky',
      author_email='artemyk@gmail.com',
      url='https://github.com/artemyk/dynpy',
      packages=['dynpy'],
     )