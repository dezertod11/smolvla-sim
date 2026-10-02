from glob import glob

from setuptools import setup

setup(
    name="vla_bridge",
    version="0.1.0",
    packages=["vla_bridge"],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/vla_bridge"]),
        ("share/vla_bridge", ["package.xml"]),
        ("share/vla_bridge/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    entry_points={
        "console_scripts": [
            "runtime_publisher = vla_bridge.runtime_probe:publisher",
            "runtime_subscriber = vla_bridge.runtime_probe:subscriber",
        ]
    },
)
