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
if DISTRO not in DEBIAN_DISTROS:
    raise DistError


parser = argparse.ArgumentParser(
    prog=NAME,
    description="Python script that downloads all package dependencies recursively"
)
parser.add_argument("-p", "--path", help="The path to the debian package. (in this folder a new folder named: {}"
                                         " will be created and the packages will be downloaded there)", required=True)
parser.add_argument('-f', '--folder', help="The name of the folder that will store the downloaded packages")
parser.add_argument('--download-path', help="The path where the download folder will be created")
parser.add_argument('--force', help="Force overwrite of existing files", action="store_true")
args = parser.parse_args()

FORCE = args.force
FOLDER_NAME = "dependencies_python" if not args.folder else args.folder
URL = "https://packages.debian.org/stretch/amd64/{}/download"
PACKAGE_PATH = args.path
TARGET_PATH = None
if args.download_path:
    if not os.path.exists(args.download_path):
        raise PathError
    TARGET_PATH = args.download_path
PACKAGE = None

if os.path.exists(PACKAGE_PATH) and not TARGET_PATH:
    split = PACKAGE_PATH.split('/')
    if split[-1].endswith(".deb"):
        PACKAGE_PATH = '/' + '/'.join(split[:-1])
        TARGET_PATH = os.path.join(PACKAGE_PATH, FOLDER_NAME)
        PACKAGE = split[-1]
    else:
        TARGET_PATH = os.path.join(PACKAGE_PATH, FOLDER_NAME)
        PACKAGE = subprocess.check_output("echo -n $(ls -la %s | awk '{print  $NF}' | grep -oPm1 '.*(?:deb)')" % PACKAGE_PATH, shell=True).decode()
    print(f"Downloading dependencies for: {PACKAGE} \nDownload path: {TARGET_PATH}")
    if not os.path.isfile(os.path.join(PACKAGE_PATH, PACKAGE)):
        print(PACKAGE.encode())
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
    name = package_dict['name']
    path = os.path.join(TARGET_PATH, name)
    url = package_dict['url']
    response = requests.get(url)
    if not check_response(response):
        raise BadRequest
    print(f"Writing to: {name}")
    if not os.path.exists(path) or FORCE:
        with open(path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=16384):
                if chunk:
                    file.write(chunk)
    else:
        print(f"{name} exists, skipping")


def download_multiple_files(urls: list):
    for url in urls:
        download_from_url(url)


def main():
    dependencies = parse_dependencies(get_dependencies())
    urls = get_urls_for_multiple_dependencies(dependencies)
    download_multiple_files(urls)


if __name__ == '__main__':
    main()
