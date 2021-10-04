from picamera import PiCamera
from time import sleep
from fractions import Fraction
from datetime import datetime

camera = PiCamera()
camera.resolution = (3280, 2464)
camera.start_preview()
sleep(5)
#now = datetime.now()
#d = now.strftime("%m%d%Y_%H%M%S")
filename = './img/'+datetime.now().strftime("%m%d%Y-%H%M%S")+'.jpg'
#camera.capture('./img/'+datetime.now().strftime("%m%d%Y_%H%M%S")+'.jpg')
camera.capture(filename)
camera.stop_preview()
