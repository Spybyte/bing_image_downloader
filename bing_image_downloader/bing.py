from pathlib import Path
from os.path import basename
import os
import sys
import urllib.request
import urllib
import imghdr
import re
import cv2
import numpy as np

'''
Python api to download image form Bing.
Author: Guru Prasad (g.gaurav541@gmail.com)
'''


class Bing:
    def __init__(self, query, limit, output_dir, adult, timeout, filters='', headers={}):
        self.download_count = 0
        self.query = query
        self.output_dir = output_dir
        self.adult = adult
        self.filters = filters

        assert type(limit) == int, "limit must be integer"
        self.limit = limit
        assert type(timeout) == int, "timeout must be integer"
        self.timeout = timeout

        self.headers = {'User-Agent': 'Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'}
        self.headers.update(headers)

        self.page_counter = 0
        self.known_hashes = []
        self.known_urls = []

    # Calculate image hash: https://www.pyimagesearch.com/2020/04/20/detect-and-remove-duplicate-images-from-a-dataset-for-deep-learning/
    def dhash(self, image, hashSize=8):
        # convert image from request to an cv2 compatible image
        cv2_image = np.asarray(bytearray(image), dtype="uint8")
        cv2_image = cv2.imdecode(cv2_image, cv2.IMREAD_COLOR)

        # convert the image to grayscale and resize the grayscale image,
        # adding a single column (width) so we can compute the horizontal
        # gradient
        gray = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (hashSize + 1, hashSize))
        # compute the (relative) horizontal gradient between adjacent
        # column pixels
        diff = resized[:, 1:] > resized[:, :-1]
        # convert the difference image to a hash and return it
        return sum([2 ** i for (i, v) in enumerate(diff.flatten()) if v])

    def save_image(self, link, file_path):
        request = urllib.request.Request(link, None, self.headers)
        image = urllib.request.urlopen(request, timeout=self.timeout).read()
        hash = self.dhash(image)

        if hash in self.known_hashes:
            print(f'[Warn] {self.query}: Image already downloaded, ignoring it {link}\n')
            raise
        self.known_hashes.append(hash)

        if not imghdr.what(None, image):
            print(f'[Error] {self.query}: Invalid image, not saving {link}\n')
            raise

        with open(file_path, 'wb') as f:
            f.write(image)


    def download_image(self, link):
        self.download_count += 1

        # Get the image link
        try:
            path = urllib.parse.urlsplit(link).path
            filename = basename(path).split('?')[0]
            file_type = filename.split(".")[-1]
            if file_type.lower() not in ["jpe", "jpeg", "jfif", "exif", "tiff", "gif", "bmp", "png", "webp", "jpg"]:
                file_type = "jpg"

            # Download the image
            print(f"[%] {self.query}: Downloading Image #{self.download_count} from {link}")
            if link in self.known_urls:
                print(f'[%] {self.query}: Image already downloaded, ignoring it {link}\n')
                self.download_count -= 1
            else:
                self.known_urls.append(link)
                self.save_image(link, "{}/{}/{}/".format(os.getcwd(), self.output_dir, self.query) + "Image_{}.{}".format(
                str(self.download_count), file_type))
                print(f"[%] {self.query}: File Downloaded !\n")
        except Exception as e:
            self.download_count -= 1
            print(f"[!] {self.query}: Issue getting: {link}\n[!] {self.query}: Error:: {e}")

    def run(self):
        while self.download_count < self.limit:
            print(f'\n\n[!] {self.query}: Indexing page: {self.page_counter+1}\n')
            # Parse the page source and download pics
            request_url = 'https://www.bing.com/images/async?q=' + urllib.parse.quote_plus(self.query) \
                + '&first=' + str(self.page_counter) + '&count=' + str(self.limit) \
                + '&adlt=' + self.adult + '&qft=' + self.filters
            request = urllib.request.Request(request_url, None, headers=self.headers)
            response = urllib.request.urlopen(request)
            html = response.read().decode('utf8')
            links = re.findall('murl&quot;:&quot;(.*?)&quot;', html)

            print(f"[%] {self.query}: Indexed {len(links)} Images on Page {self.page_counter+1}.")
            print("\n===============================================\n")

            for link in links:
                if self.download_count < self.limit:
                    self.download_image(link)
                else:
                    print(f"\n\n[%] {self.query}: Done. Downloaded {self.download_count} images.")
                    print("\n===============================================\n")
                    break

            self.page_counter += 1
