import subprocess
import requests
import re
import os
import sys
import argparse
import distro
from exceptions import *


DEBIAN_DISTROS = [
    "ubuntu",
    "kali",
    "astra",
    "google",
    "pureos",
    "raspberry",
    "dyson",
    "limux",
    "parrot"
]
NAME = sys.argv[0].split('/')[-1]
try:
    DISTRO = distro.name().lower().split()[0]
except IndexError:
    DISTRO = ''
print(f"Running {NAME} on {DISTRO}")
if DISTRO not in DEBIAN_DISTROS:
    raise DistError


parser = argparse.ArgumentParser(
    prog=NAME,
    description="Python script that downloads all package dependencies recursively"
)
parser.add_argument("-p", "--path", help="The path to the debian package. (in this folder a new folder named: {}"
                                         " will be created and the packages will be downloaded there)", required=True)
args = parser.parse_args()

URL = "https://packages.debian.org/stretch/amd64/{}/download"
PACKAGE_PATH = args.path
TARGET_PATH = ''
PACKAGE = ''
if os.path.exists(PACKAGE_PATH):
    split = PACKAGE_PATH.split('/')
    if split[-1].endswith(".deb"):
        PACKAGE_PATH = '/' + '/'.join(split[:-1])
        TARGET_PATH = os.path.join(split[:-1], NAME)
        PACKAGE = split[-1]
    else:
        TARGET_PATH = os.path.join(PACKAGE_PATH, NAME)
        PACKAGE = subprocess.check_output("ls -la %s | awk '{print  $NF}' | grep -oPm1 '.*(?:deb)'" % TARGET_PATH
                                          , shell=True).decode()
    if not os.path.isfile(os.path.join(TARGET_PATH, PACKAGE)):
        raise FileError
else:
    raise PathError
os.makedirs(TARGET_PATH, exist_ok=True)


def get_dependencies():
    return subprocess.check_output(f"dpkg -I {os.path.join(PACKAGE_PATH, PACKAGE)} | grep -oP '(?<=Depends\: ).*'", shell=True).decode()


def check_response(req: requests.Response):
    return req.status_code == 200


def parse_dependencies(dependencies: str):
    parsed = []
    for dep in dependencies.split(','):
        parsed.append(dep.split()[0])
    return parsed


def get_link_from_html(data:str):
    try:
        res = re.search('(?<=href=")(http://ftp.is).*(?=">)', data).group()
    except AttributeError:
        res = re.search('(?<=href=")(http://security).*(?=">)', data).group()
    return res


def get_download_link_for_dependency(dependency: str):
    print(f"Retrieving url for: {dependency}")
    response = requests.get(url=URL.format(dependency))
    if not check_response(response):
        raise BadRequest
    data = response.content
    link = get_link_from_html(data.decode())
    return {"name": link.split("/")[-1], "url": link}


def get_urls_for_multiple_dependencies(dependencies: list):
    urls = []
    for dep in dependencies:
        urls.append(get_download_link_for_dependency(dep))
    return urls


def download_from_url(package_dict: dict):
    path = os.path.join(TARGET_PATH, package_dict['name'])
    url = package_dict['url']
    response = requests.get(url)
    if not check_response(response):
        raise BadRequest
    print(f"Writing to")
    with open(path, 'wb') as file:
        for chunk in response.iter_content(chunk_size=16384):
            if chunk:
                file.write(chunk)


def download_multiple_files(urls: list):
    for url in urls:
        download_from_url(url)


def main():
    dependencies = parse_dependencies(get_dependencies())
    urls = get_urls_for_multiple_dependencies(dependencies)
    download_multiple_files(urls)


if __name__ == '__main__':
    main()
