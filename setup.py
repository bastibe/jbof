from setuptools import setup

setup(
    name='jbof',
    version='0.0.1',
    description='A Daset from Just a Bunch of Files',
    author='Bastian Bechtold',
    author_email='basti@bastibe.de',
    url='https://github.com/bastibe/jbof',
    license='GPL v3',
    py_modules=['runforrest'],
    install_requires=['numpy', 'soundfile', 'scipy'],
    python_requires='>=3.6'
)
