from setuptools import setup
import os


def package_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join("..", path, filename))
    return paths


extra_files = package_files("./fcreplay/data")

setup(
    name="fcreplay",
    version="0.9",
    description="Fcreplay python code",
    url="http://github.com/glisignoli/fcreplay",
    author="Gino Lisignoli",
    author_email="glisignoli@gmail.com",
    license="GPL3",
    packages=["fcreplay"],
    package_data={"": extra_files},
    entry_points={"console_scripts": ["fcreplay=fcreplay.__main__:main"]},
    install_requires=["attrs==22.1.0; python_version >= '3.5'", "backoff==2.1.2; python_version >= '3.7'", "beautifulsoup4==4.11.1; python_full_version >= '3.6.0'", 'bootstrap-flask==2.0.2', "cachetools==5.2.0; python_version ~= '3.7'", 'cerberus==1.3.4', "certifi==2022.6.15; python_full_version >= '3.6.0'", "charset-normalizer==2.1.0; python_full_version >= '3.6.0'", "click==8.1.3; python_version >= '3.7'", 'cmd2==2.4.2', "contextlib2==21.6.0; python_full_version >= '3.6.0'", 'debugpy==1.6.2', "deprecated==1.2.13; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'", 'docker==6.0.0b2', 'docopt==0.6.2', 'feedgen==0.9.0', 'flask==2.2.2', 'flask-cors==3.0.10', 'flask-sqlalchemy==2.5.1', 'flask-wtf==1.0.1', "google-api-core==2.8.2; python_full_version >= '3.6.0'", 'google-api-python-client==2.56.0', "google-auth==2.10.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4, 3.5'", 'google-auth-httplib2==0.1.0', 'google-auth-oauthlib==0.5.2', "googleapis-common-protos==1.56.4; python_version >= '3.7'", "greenlet==2.0.0a2; python_version >= '3' and (platform_machine == 'aarch64' or (platform_machine == 'ppc64le' or (platform_machine == 'x86_64' or (platform_machine == 'amd64' or (platform_machine == 'AMD64' or (platform_machine == 'win32' or platform_machine == 'WIN32'))))))", 'grpcio==1.48.0rc1', 'gunicorn==20.1.0', "httplib2==0.20.4; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'", 'i3ipc==2.2.1', "idna==3.3; python_version >= '3.5'", 'internetarchive==3.0.2', "itsdangerous==2.1.2; python_version >= '3.7'", 'jinja2==3.1.2', "jsonpatch==1.32; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'", "jsonpointer==2.3; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'", 'junit-xml==1.9', 'lxml==4.9.1', "markupsafe==2.1.1; python_version >= '3.7'", 'mouseinfo==0.1.3', 'oauth2client==4.1.3', "oauthlib==3.2.0; python_full_version >= '3.6.0'", "opentelemetry-api==1.12.0; python_full_version >= '3.6.0'", 'opentelemetry-distro==0.33b0', 'opentelemetry-exporter-otlp-proto-grpc==1.12.0', "opentelemetry-instrumentation==0.33b0; python_full_version >= '3.6.0'", 'opentelemetry-instrumentation-flask==0.33b0', 'opentelemetry-instrumentation-requests==0.33b0', "opentelemetry-instrumentation-wsgi==0.33b0; python_full_version >= '3.6.0'", "opentelemetry-proto==1.12.0; python_full_version >= '3.6.0'", "opentelemetry-sdk==1.12.0; python_full_version >= '3.6.0'", "opentelemetry-semantic-conventions==0.33b0; python_full_version >= '3.6.0'", "opentelemetry-util-http==0.33b0; python_full_version >= '3.6.0'", "packaging==21.3; python_full_version >= '3.6.0'", 'pillow==9.2.0', 'pip==22.2.2', "progressbar2==4.0.0; python_version >= '3.7'", "protobuf==3.20.1; python_version >= '3.7'", 'psycopg2==2.9.3', "pyasn1==0.5.0rc1; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4, 3.5'", "pyasn1-modules==0.3.0rc1; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4, 3.5'", 'pyautogui==0.9.53', 'pygetwindow==0.0.9', 'pymsgbox==1.0.9', "pyparsing==3.0.9; python_version > '3.0'", 'pyperclip==1.8.2', 'pyrect==0.2.0', 'pyscreeze==0.1.28', "python-dateutil==2.8.2; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2'", 'python-logging-loki==0.3.1', "python-utils==3.3.3; python_version >= '3.7'", 'python-xlib==0.31', "python3-xlib==0.15; platform_system == 'Linux' and python_version >= '3.0'", 'pytweening==1.0.4', 'pytz==2022.2.1', 'pyyaml==6.0', 'requests==2.28.1', "requests-oauthlib==1.3.1; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'", 'retrying==1.3.3', 'rfc3339==6.2', "rsa==4.9; python_full_version >= '3.6.0' and python_version < '4'", 'schedule==1.1.0', 'schema==0.7.5', "setuptools==64.0.3; python_version >= '3.7'", "six==1.16.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2'", "soupsieve==2.3.2.post1; python_full_version >= '3.6.0'", 'sqlalchemy==1.4.40', 'sqlalchemy-utils==0.38.3', "tqdm==4.64.0; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3'", "typing-extensions==4.3.0; python_version >= '3.7'", "uritemplate==4.1.1; python_full_version >= '3.6.0'", 'urllib3==1.26.11', 'wcwidth==0.2.5', "websocket-client==1.3.3; python_version >= '3.7'", 'werkzeug==2.2.2', "wrapt==1.14.1; python_version >= '2.7' and python_version not in '3.0, 3.1, 3.2, 3.3, 3.4'", 'wtforms==3.0.1'















































































                      ],
    dependency_links=['git+https://github.com/glisignoli/pylinkvalidator@9af220529dc56a1b16998d0c5bf9e37c45d31448#egg=pylinkvalidator', 'git+https://github.com/tokland/youtube-upload.git@6a30b55d0fd4976571a5b9b34c01fd41cec49c7a#egg=youtube-upload'


                      ],
    zip_safe=False,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3.10",
        "Topic :: Utilities",
    ],
)
