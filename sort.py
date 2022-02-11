#!/usr/bin/env python3


# TODO data stamp from other files


import os
import shutil
import datetime
import exifread

from datetime import datetime
import pandas as pd
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from csv import writer
from PIL import Image


# extract the files from src
class Src:
    def __init__(self, src: object, target: object = None):
        self.src = src
        self.target = target
        self.l_ext = dict()  # maybe dict not necessary
        self.l_files = list()
        self.files_count = 0
        pass

    def extract_files(self):
        # walk trough the folders
        for root, dirs, files in os.walk(os.path.join(self.src)):
            lf_nr = 1
            for filename in files:
                # add the file to the list
                self.l_files.append((root, filename))
                self.files_count += 1
                # create a File Class
                name_str = 'F_{}'.format(lf_nr)
                # print(name_str)
                name_str = File(self.src, self.target, name_str, root, filename)
                lf_nr += 1
        return name_str

    @staticmethod
    def create_dst(final_dst):
        folders = list(filter(None, (final_dst.split('/'))))  # filtered none values
        le = len(folders)
        for i in range(1, le + 1):
            folder = '/' + '/'.join(folders[:i])
            if os.path.exists(folder):
                pass
            else:
                os.mkdir(folder)
                pass


# make class object iterable
class IterRegistry(type):
    def __iter__(cls):
        return iter(cls._registry)


# create for each file an object
def bin_sort(data):
    fails = [b'', b'\x00\x05\x16']  # AppleDouble
    if data in fails:
        return None
    if data == b'\xff\xd8\xff':
        return 'jpg'
    if data == b'GIF':
        return 'gif'
    if data == b'{\n ':
        return 'json'
    if data == b'\x89PN':
        return 'png'
    if data == b'\x00\x00\x00':
        return 'video'  # TODO  need differentiation between heic and mov
    if data == b'II*':
        return 'cr2'
    else:
        return 'NaN'


class File(Src):  # removed object, it works
    __metaclass__ = IterRegistry
    _registry = []

    def __init__(self, src, target, name, root, filename):
        Src.__init__(self, src, target)  # super()
        self._registry.append(self)
        self.name = name
        self.root = root
        self.filename = filename
        ext = self.ext_bin()
        self.ext = ext
        creation_time = self.get_creation()
        self.ctime = creation_time
        dst = self.dst_f()
        self.dst = '{}/{}'.format(target, dst)

        pass

    # select, extract imgs / movies
    def ext_bin(self):
        # opening for [r]eading as [b]inary
        in_file = open(os.path.join(self.root, self.filename), "rb")

        # read the first three bytes
        data = in_file.read(3)
        in_file.close()

        # convert the bytes to a format
        ext_b = bin_sort(data)

        if ext_b is None:
            # remove the file
            self._registry.remove(self)
            del self.name

        else:
            return ext_b

    # Foto functions
    def get_creation(self):
        l1 = ['jpg', 'png', 'cr2']

        if self.ext in l1:
            return self.date_from_exif()

        if self.ext == 'gif':
            # TODO
            return 'How to?'

        if self.ext == 'json':
            # TODO
            return 'json'

        if self.ext == 'video':  # TODO heic does not work
            # date_from_meta(self)
            return self.date_from_meta()

        if self.ext == 'NaN':
            # TODO
            return 'NaN'
        else:
            # TODO
            return self.ext

    def date_from_exif(self):
        # TODO : double find of exif- datetime: could be better
        # openfile
        # global date_str
        f = open(os.path.join(self.root, self.filename), 'rb')
        # extract data from exif
        data = exifread.process_file(f)
        f.close()

        if data:
            date_str = data['EXIF DateTimeOriginal'].values

        # extract data with PIL
        else:
            with Image.open(os.path.join(self.root, self.filename)) as img:
                if img:
                    # read metadata, creation time
                    data_PIL = img._getexif()
                    date_str = data_PIL[36867]
            # and close
            img.close()

        # convert date string into object
        if date_str:
            time_obj = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
            return time_obj  # .date()
        else:
            return 'no time'

    def date_from_meta(self):  # TODO improve
        parser = createParser('{}/{}'.format(self.root, self.filename))
        if not parser:
            pass
        with parser:
            try:
                metadata = extractMetadata(parser)
            except Exception as err:
                print("Metadata extraction error: %s" % err)
                return "Unable to extract metadata"
        if metadata:
            for line in metadata.exportPlaintext():
                if line.split(':')[0] == '- Creation date':
                    dateobj = datetime.strptime(line.split(':')[1].split()[0], "%Y-%m-%d")

                    return dateobj  # .date()
        else:
            # TODO something for heic

            return 'No data, probable heic'

    # preparation to copy

    def dst_f(self):
        # format 2021-03-23
        # <class 'datetime.datetime'>
        # strip date
        if isinstance(self.ctime, datetime):
            y = self.ctime.year
            m = self.ctime.month
            y_m = '{}-{:0>2s}'.format(str(y)[2:], str(m))  # format dest/ year / yy - mm
            return '{}/{}'.format(y, y_m)
        else:
            return 'no date'

    def new_filename(self, marker='-'):  # TODO to improve
        new_filename_exists = True
        while new_filename_exists:
            basename, fileext = os.path.splitext(self.filename)
            if marker not in basename:
                base = basename
                value = 0
            else:
                base, counter = basename.rsplit(marker, 1)
                try:
                    value = int(counter)
                except ValueError:
                    base = basename
                    value = 0

            value += 1
            filename = '%s%s%d%s' % (base, marker, value, fileext)

            new_filename_exists = os.path.isfile('{}/{}'.format(self.dst, filename))
            if not new_filename_exists:
                return filename

    def copy_file(self):
        # set destination
        self.create_dst(self.dst)
        source = '{}/{}'.format(self.root, self.filename)
        destination = '{}/{}'.format(self.dst, self.filename)
        if os.path.isfile(destination):
            filename = self.new_filename()
            destination = '{}/{}'.format(self.dst, filename)
        else:
            pass

        shutil.copy2(source, destination)
        print(destination)
        pass

    def report(self, target):
        report = []
        for item in File._registry:
            if isinstance(item, File):
                report.apppend([self.root, self.filename, self.ext, self.dst])

        df_files = pd.DataFrame(report, columns=['root', 'filename', 'ext', 'dst'])

        csv_name: str = os.path.join('{}/list.csv'.format(target))

        if not os.path.isfile(csv_name):
            csv = open(csv_name, "x")

        with open(csv_name, 'a+', newline='') as write_obj:
            csv_writer = writer(write_obj)
            csv_writer.writerow(['________', '________'])
            csv_writer.writerow([self.src, datetime.now()])
            csv_writer.writerow(['________', '________'])

        df_files.to_csv(csv_name, index=False, mode='a', header=True, sep='\t')
        pass
