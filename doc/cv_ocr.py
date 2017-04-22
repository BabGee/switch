#-*- coding:utf-8 -*-
import cv
from PIL import Image, ImageFilter
import time
import pytesseract
from string import digits
import numpy as np

start_time = time.time()

def smoothImage(im, nbiter=0, filter=cv.CV_GAUSSIAN):
    for i in range(nbiter):
        cv.Smooth(im, im, filter)

def openCloseImage(im, nbiter=0):
    for i in range(nbiter):
        cv.MorphologyEx(im, im, None, None, cv.CV_MOP_OPEN) #Open and close to make appear contours
        cv.MorphologyEx(im, im, None, None, cv.CV_MOP_CLOSE)

def dilateImage(im, nbiter=0):
    for i in range(nbiter):
        cv.Dilate(im, im)

def erodeImage(im, nbiter=0):
    for i in range(nbiter):
        cv.Erode(im, im)

def thresholdImage(im, value, filter=cv.CV_THRESH_BINARY_INV):
    cv.Threshold(im, im, value, 255, filter)

def resizeImage(im, (width, height)):
    #It appears to me that resize an image can be significant for the ocr engine to detect characters
    res = cv.CreateImage((width,height), im.depth, im.channels)
    cv.Resize(im, res)
    return res

def getContours(im, approx_value=1): #Return contours approximated
    storage = cv.CreateMemStorage(0)
    contours = cv.FindContours(cv.CloneImage(im), storage, cv.CV_RETR_CCOMP, cv.CV_CHAIN_APPROX_SIMPLE)
    contourLow=cv.ApproxPoly(contours, storage, cv.CV_POLY_APPROX_DP,approx_value,approx_value)
    return contourLow

def getIndividualContoursRectangles(contours): #Return the bounding rect for every contours
    contourscopy = contours
    rectangleList = []
    while contourscopy:
        x,y,w,h = cv.BoundingRect(contourscopy)

    return rectangleList

if __name__=="__main__":
	orig = cv.LoadImage("WP_20141015_003.jpg")
	#orig = cv.LoadImage("KENYA_ID_CARD.jpg")


	#Convert in black and white
	res = cv.CreateImage(cv.GetSize(orig), 8, 1)
	cv.CvtColor(orig, res, cv.CV_BGR2GRAY)
	#cv.Threshold(res, 0, 255, cv.CV_THRESH_OTSU)[1]

	#Operations on the image
	openCloseImage(res)
	dilateImage(res, 0)
    	erodeImage(res, 0)
    	smoothImage(res, 0)
    	thresholdImage(res, 150, cv.CV_THRESH_OTSU)
   
    	#Get contours approximated
    	contourLow = getContours(res, 2)
    
    	#Draw them on an empty image
    	final = cv.CreateImage(cv.GetSize(res), 8, 1)
    	cv.Zero(final)
    	cv.DrawContours(final, contourLow, cv.Scalar(255), cv.Scalar(255), 2, cv.CV_FILLED)    
	cv.SaveImage('beforeFinal.png', final)
	

	img = Image.fromstring("L", cv.GetSize(final), final.tostring())#

	#   Make the image bigger (needed for OCR)
	img = img.resize((1000, 500), Image.NEAREST)
	img = img.filter(ImageFilter.SHARPEN)
	'''
	#names = (100, 115, 405, 150)
	names = (90, 130, 700, 160)
	#names = (700, 70, 980, 105)
	#names = (620, 70, 800, 105)
	names = img.crop(names)
	names = pytesseract.image_to_string(names, config='letters')
	print 'Names: %s' % names
	'''

	names = (100, 115, 405, 150)
	names = img.crop(names)
	names = pytesseract.image_to_string(names, config='letters')
	print 'Names: %s' % names

	num = (620, 70, 800, 105)
	num = img.crop(num)
	num = pytesseract.image_to_string(num, config='digits')
	num = ''.join(c for c in str(num) if c in digits)
	print 'ID Number: %s' % num

	dob = (340, 165, 540, 190)
	dob = img.crop(dob)
	dob = pytesseract.image_to_string(dob)
	dob = ''.join(c for c in str(dob) if c in digits)
	from datetime import datetime
	if len(dob)==8:dob = datetime.strptime(dob, '%d%m%Y').isoformat()
	else: dob = datetime.today().isoformat()
	print 'Date of Birth: %s' % dob

	gender = (340, 205, 540, 235)
	gender = img.crop(gender)
	gender = pytesseract.image_to_string(gender, config='gender')
	print 'Gender: %s' % gender

	location = (340, 250, 540, 280)
	location = img.crop(location)
	location = pytesseract.image_to_string(location, config='letters')
	print 'District of Birth: %s' % location

	print "TAT: %s seconds" % (time.time() - start_time)


	'''

    	cv.ShowImage("orig", orig)
    	cv.ShowImage("image", res)
    	cv.SaveImage("modified.png", res)
    	cv.ShowImage("contour", final)
    	cv.SaveImage("contour.png", final)
    	cv.WaitKey(0)
    	'''
