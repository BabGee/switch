#!/usr/bin/python

from PIL import Image, ImageFilter
import time
import pytesseract
from string import digits
import numpy as np

start_time = time.time()

img = Image.open('WP_20141015_003.jpg')
img = img.convert("RGBA")

pixdata = img.load()

for y in xrange(img.size[1]):
 for x in xrange(img.size[0]):
 	if pixdata[x, y][0] < 128:
		 pixdata[x, y] = (0, 0, 0, 255)
	if pixdata[x, y][1] < 136:
		 pixdata[x, y] = (0, 0, 0, 255)
	if pixdata[x, y][2] > 0:
		 pixdata[x, y] = (255, 255, 255, 255)


#   Make the image bigger (needed for OCR)
img = img.resize((1000, 500), Image.NEAREST)
img = img.filter(ImageFilter.SHARPEN)
img = img.convert('RGB')

names = (100, 115, 405, 150)
names = img.crop(names)
names = pytesseract.image_to_string(names)
print 'Names: %s' % names

num = (620, 70, 800, 105)
num = img.crop(num)
num = pytesseract.image_to_string(num)
num = ''.join(c for c in str(num) if c in digits)
print 'ID Number: %s' % num

dob = (340, 165, 540, 190)
dob = img.crop(dob)
dob = pytesseract.image_to_string(dob)
dob = ''.join(c for c in str(dob) if c in digits)
from datetime import datetime
dob = datetime.strptime(dob, '%d%m%Y')
print 'Date of Birth: %s' % dob

gender = (340, 205, 540, 235)
gender = img.crop(gender)
gender.save('region.gif')
gender = pytesseract.image_to_string(gender)
print 'Gender: %s' % gender

location = (340, 250, 540, 280)
location = img.crop(location)
location = pytesseract.image_to_string(location)
print 'District of Birth: %s' % location

print "TAT: %s seconds" % (time.time() - start_time)
