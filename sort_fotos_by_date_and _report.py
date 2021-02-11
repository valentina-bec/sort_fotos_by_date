##### 
#   final script um die bilder und mov dateien 
#   nach Datum zu sortieren in target ordner
#   wenn unbekanntes datum - > no data
#   wenn unbekannte extention -> andere
#####

import os, tempfile, shutil, sys, datetime
import numpy as np
import os.path
import csv
import glob
import functools
import operator

from PIL import Image
from time import time
from dateutil.relativedelta import relativedelta
from PIL import ImageTk
from tkinter import filedialog
from tkinter.filedialog import askdirectory
from datetime import date, datetime
from pathlib import Path
import pandas as pd
from typing import List, Tuple
from struct import *
from PIL.ExifTags import TAGS
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from csv import writer

class Files():

    def ask_dir(self):
        src = askdirectory()
        return src

    def look_extention(self, filename):
        basename, ext_raw = os.path.splitext(filename) 
        ext = ext_raw.lower()
        return ext

    def list_of_ext(self, src):
        list_of_ext = list()
        for root, dirs, files in os.walk(src):
            for filename in files: 
                basename, ext_raw = os.path.splitext(filename)
                ext = ext_raw.lower()
                list_of_ext.append((ext))
        extentions = []
        for entry in list_of_ext:
            if entry not in extentions:
                extentions.append (entry) # liste de ext zusammengefasst
        
        ext_count = list()
        i = 0
        while (i < len (extentions)):
            ext_count.append( (extentions[i], list_of_ext.count(extentions[i])))
            i = i + 1
        df_ext = pd.DataFrame(ext_count, columns=['ext', '#'])
        return df_ext

    def foto_creation_time(self, root, f): 
        if f.endswith(r'.JPG') or f.endswith('.jpg') or f.endswith(r'.JPEG') or f.endswith('.jpeg'): # für fotos
            im = Image.open(os.path.join(root, f), "r")   
            exif = im.getexif() 
            creation_time_str = exif.get(36867) # creation time of foto                       
            im.close()   
            if not creation_time_str  != '0000:00:00 00:00:00':
                    creation_time_str = None
            else: pass
            if creation_time_str: 
                creation_time_obj = datetime.strptime(creation_time_str, '%Y:%m:%d %H:%M:%S')
                date_foto = creation_time_obj.date()
               
            else: date_foto = None
            return date_foto

    def cr2_creation_time (self, root, filename):
        if filename.endswith(r'.cr2') or filename.endswith('.CR2'):
            with open(os.path.join(root, filename), "rb") as im:
                # read the first 1kb of the file should be enough to find the date / time
                buffer = im.read(1024) 
                 # Search for the datetime entry offset
                (num_of_entries,) = unpack_from('H', buffer, 0x10)
                # Work out where the date time is stored
                datetime_offset = -1
                for entry_num in range(0, num_of_entries-1):
                    (tag_id, tag_type, num_of_value, value) = unpack_from('HHLL', buffer, 0x10 + 2 + entry_num*12)
                    if tag_id == 0x0132:
                        #print ("found datetime at offset %d"%value)
                        datetime_offset = value
                
                datetime_tup = unpack_from(10*'s', buffer, datetime_offset)
                (Y1,Y2,Y3,Y4,S1,M1,M2,S2,D1,D2) = datetime_tup
                year_tup = unpack_from(4*'s', buffer, datetime_offset)
                year_b = functools.reduce(operator.add, (year_tup)) # tup to str
                month_tup = [M1, M2]
                month_b = functools.reduce(operator.add, (month_tup))
                year = int(year_b)
                month = int(month_b)
                day = 1

            im.close()


        date_foto = datetime(year, month, day)
        return date_foto

    def create_dst(self, target, date_foto): # date_foto anstatt creation_time_str 
        if date_foto:
            years= str(date_foto.year)
            months = str(date_foto.month)  

            if os.path.exists(target + "/" + years): pass
            else: os.mkdir(target + "/" + years)
            if os.path.exists(target + '/' + years + '/' + years + '-' + months): pass
            else: os.mkdir(target + "/" + "/" + years + '/' + years + '-' + months)
            return  os.path.join(target + "/"  + years + '/' + years + '-' + months + '/')
        else: 
            if os.path.exists(target + "/" + "no-date"): pass
            else: os.mkdir(target + "/" + "no-date")
            return os.path.join(target + "/"  + "no-date" + '/')

    def mov_creation_time_dst(self, root, target, filename):
        parser = createParser(root + '/'+ filename)
        if not parser:
            pass
        with parser:
            try:
                metadata = extractMetadata(parser)
            except Exception as err:
                print("Metadata extraction error: %s" % err)
                metadata = None
        if metadata:
            print("Unable to extract metadata")

            for line in metadata.exportPlaintext():
                if line.split(':')[0] == '- Creation date':
                    dateobj = datetime.strptime(
                        line.split(':')[1].split()[0], "%Y-%m-%d")
                    if dateobj:
                        year = int(dateobj.year)
                        month = int(dateobj.month)
                        day = int(dateobj.day)

                        date_foto = datetime(year, month, day)
                    else: pass
                    return date_foto                
        else: pass

    def create_new_name(self, filename, dst, marker='-'):
        new_filename_exists = True
        while new_filename_exists:
            basename, fileext = os.path.splitext(filename)
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
                
            value +=1
            filename = '%s%s%d%s' % (base, marker, value, fileext)
            
            new_filename_exists = os.path.isfile(dst + '/' + filename)
            if not new_filename_exists:
                return filename

    def copy_file_g(self, root, filename, target, dst):
        file_exists = os.path.isfile(dst + '/' + filename)
        if file_exists:
            new_filename = self.create_new_name(filename, dst) # funciona
            shutil.copy2(root + '/' + filename, dst + '/' + new_filename) 
            return dst + new_filename
        else: 
            shutil.copy2(root + '/' + filename, dst + '/' + filename) 
            return dst

    def copy_jpg (self, root, filename, target):
        date_foto = self.foto_creation_time(root, filename)
        dst0 = self.create_dst(target, date_foto)
        dst = self.copy_file_g(root, filename, target, dst0)
        print (filename, dst)
        return dst

    def copy_cr2 (self, root, filename, target):
        date_foto = self.cr2_creation_time(root, filename)
        dst0 = self.create_dst(target, date_foto)
        dst = self.copy_file_g(root, filename, target, dst0)
        print (filename, dst)
        return dst
    
    def copy_mov (self, root, filename, target):
        basename, ext_raw = os.path.splitext(filename)

        if os.path.isfile(root + '/' + basename +'.jpg') or os.path.isfile(root + '/' + basename +'.JPG'):
            date_foto = self.foto_creation_time(root, basename + '.jpg')
            dst0 = self.create_dst(target, date_foto)
            dst = self.copy_file_g(root, filename, target, dst0)
            return dst

        else: 
            date_foto = self.mov_creation_time_dst(root, target, filename)
            dst0 = self.create_dst(target, date_foto)
            dst = self.copy_file_g(root, filename, target, dst0)

            shutil.copy2(root + '/' + filename , dst ) 
        print (filename, dst)
        return dst

    def copy_ext (self, root, filename, target, ext):
        
        
        if os.path.exists(target + "/andere"): pass
        else: os.mkdir(target +  "/andere" )
        if os.path.exists(target + "/andere/" + ext): pass
        else: os.mkdir(target +  "/andere/" + ext)
        dst0 = os.path.join(target +  "/andere/"  +  ext + '/')
        dst = self.copy_file_g(root, filename, target, dst0)
        print (filename, dst)
        return dst

    def sort_files (self, src, target):
        list_of_files = list()

        for root, dirs, files in os.walk(src):
            for filename in files:
                ext = self.look_extention(filename)
                if not ext != ".jpg":
                    dst = self.copy_jpg(root, filename, target)
                    list_of_files.append((root, filename, ext, dst))

                elif not ext != ".jpeg":
                    dst = self.copy_jpg(root, filename, target)
                    list_of_files.append((root, filename, ext, dst))
                elif not ext != ".cr2":
                    dst = self.copy_cr2(root, filename, target)
                    list_of_files.append((root, filename, ext, dst)) 

                elif not ext !=".mov":

                    dst = self.copy_mov(root, filename, target)
                    list_of_files.append((root, filename, ext, dst))

                elif not ext !=".mp4":
                    dst = self.copy_mov(root, filename, target)
                    list_of_files.append((root, filename, ext, dst))

                elif not ext !=".gif":
                    dst = self.copy_jpg(root, filename, target) # copy to dst
                    list_of_files.append((root, filename, ext, dst))


                else:
                    dst = self.copy_ext(root, filename, target, ext)
                    list_of_files.append((root, filename, ext, dst))


                
        return list_of_files

    def csv_ext (self, src, df_ext, target, a):
        csv_name = os.path.join(target + '/' + 'list_ext' + '_' + a +'.csv')
        if not os.path.isfile(csv_name):
            csv = open(csv_name, "x")
        else: pass

        with open(csv_name, 'a+', newline='') as write_obj:
            csv_writer = writer(write_obj)
            csv_writer.writerow(['________','________'])                
            csv_writer.writerow([src, datetime.now()])
            csv_writer.writerow(['________','________'])    
        
        df_ext.to_csv(csv_name, index = None, mode = 'a', header= True, sep= '\t') 

    def csv_files (self, src, list_files, target):
        df_files = pd.DataFrame(list_files, columns=['root', 'filename','ext', 'dst'])
        
        csv_name = os.path.join(target + '/' + 'list_files' + '_' +'.csv')

        if not os.path.isfile(csv_name):

            csv = open(csv_name, "x")
        else: pass

        with open(csv_name, 'a+', newline='') as write_obj:
            csv_writer = writer(write_obj)
            csv_writer.writerow(['________','________'])                
            csv_writer.writerow([src, datetime.now()])
            csv_writer.writerow(['________','________'])    
        
        df_files.to_csv(csv_name, index = None, mode = 'a', header= True, sep= '\t') 

    

def main():
    
    f1=Files()
    target = r'D:\fotos'
    src = f1.ask_dir()
    list_files = f1.sort_files(src, target)
    df_ext_src = f1.list_of_ext(src)
    df_ext_target = f1.list_of_ext(src)

    csv_dst = r'C:\Users\Jens\Desktop\Target'
    f1.csv_ext(src, df_ext_src, target, 'src')
    f1.csv_ext(target, df_ext_target, target, 'target')

    
    f1.csv_files(src, list_files, target)

    print (df_ext_src)

main()
