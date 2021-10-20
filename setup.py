import setuptools
setuptools.setup(
    name='xfyun-tts',
    version='1.0.0',
    py_modules=['xfyun_tts'],
    entry_points={'console_scripts': ['xfyuntts = xfyun_tts:_main']},
    install_requires=['websocket-client'],
)
