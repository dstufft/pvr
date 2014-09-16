# Copyright 2014 Donald Stufft
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import absolute_import, division, print_function

import collections
import hashlib
import html.parser
import os
import os.path
import posixpath
import subprocess
import urllib.parse

import packaging.version
import requests


class NoAcceptableFile(Exception):
    """
    Raised when we cannot locate an acceptable file for pip.
    """


Candidate = collections.namedtuple("Candidate", ["version", "url", "filename"])


class LinkExtractor(html.parser.HTMLParser):

    def __init__(self, *args, **kwargs):
        self.base_url = kwargs.pop("base_url")

        super(LinkExtractor, self).__init__(*args, **kwargs)

        self.links = []

    def handle_starttag(self, tag, attrs):
        # We only care about <a> tags.
        if tag != "a":
            return

        # If there's no attrs then we don't care about this link either
        if not attrs:
            return

        # We only care about rel="internal" links
        for attr, value in attrs:
            if attr == "rel" and value == "internal":
                break
        else:
            return

        # Finally, make our link absolute and then save it, unless there isn't
        # a href attr.
        for attr, value in attrs:
            if attr == "href":
                self.links.append(urllib.parse.urljoin(self.base_url, value))


class PipInstaller(object):

    def __init__(self, environment, cache_dir=None):
        if cache_dir is not None:
            os.path.join(cache_dir, "pip")

        self.environment = environment
        self.cache_dir = cache_dir
        self.session = requests.session()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self.session.close()

    def find(self, index_url="https://pypi.python.org/simple/"):
        simple = urllib.parse.urljoin(index_url, "pip/")

        # Fetch the simple page for pip.
        resp = self.session.get(simple)
        resp.raise_for_status()

        # Parse the simple page looking for links
        parser = LinkExtractor(base_url=simple)
        parser.feed(resp.text)
        parser.close()

        # Go over all the links we've located, and extract the version from
        # them.
        candidates = []
        for link in parser.links:
            parsed = urllib.parse.urlparse(link)
            filename = posixpath.basename(parsed.path)

            # We only support installation from Wheels.
            if not filename.endswith(".whl"):
                continue

            wheel_parts = filename.split("-")

            candidates.append(
                Candidate(
                    version=packaging.version.parse(wheel_parts[1]),
                    url=link,
                    filename=filename,
                ),
            )

        # Ensure we have a candidate
        if not candidates:
            raise NoAcceptableFile(
                "Cannot locate any installable files for pip."
            )

        # Sort the versions, and return the latest one
        return sorted(candidates, key=lambda x: x.version, reverse=True)[0]

    def download(self, candidate):
        # Hash our URL to use as a cache key to prevent repeat downloads
        hashed = hashlib.sha256(candidate.url.encode("utf8")).hexdigest()
        cache_path = os.path.join(self.cache_dir, hashed, candidate.filename)

        # Check to see if we have something for this URL cached already and
        # if it's not, go and fetch it.
        if not os.path.exists(cache_path):
            # Download the file
            resp = self.session.get(candidate.url)
            resp.raise_for_status()

            # Create our cache directory if it does not exist
            if not os.path.exists(os.path.dirname(cache_path)):
                os.makedirs(os.path.dirname(cache_path))

            # Cache the file.
            with open(cache_path, "wb") as fp:
                fp.write(resp.content)

        return cache_path

    def install(self):
        # Locate the latest version of pip
        candidate = self.find()

        # Download the file and store it in our cache.
        filename = self.download(candidate)

        # Now that we have the latest version of pip, do our hijinx to install
        # it.
        subprocess.check_call(
            [
                # TODO: This is called "Scripts" on Windows, at least in venv,
                #       is it the same in virtualenv? Also it's likely
                #       python.exe on Windows as well.
                os.path.join(self.environment, "bin", "python"),
                "-c",
                "import pip; pip.main(['install', '{0}'])".format(filename),
            ],
            env={"PYTHONPATH": filename},
            stdout=subprocess.DEVNULL,
        )
