from setuptools import setup, find_packages

setup(
    name="voice-assistant",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        'zmq',
        'requests',
    ]
) 