from picamera import PiCamera
from time import sleep
import numpy as np
import cv2
from fractions import Fraction
from datetime import datetime

with PiCamera() as camera:
    camera.resolution = (3264, 2464)
    camera.framerate = 5
    camera.start_preview()
    sleep(5)
    #now = datetime.now()
    #d = now.strftime("%m%d%Y_%H%M%S")
    filename = 'img/'+datetime.now().strftime("%m%d%Y-%H%M%S")+'.jpg'
    #camera.capture('./img/'+datetime.now().strftime("%m%d%Y_%H%M%S")+'.jpg')
<<<<<<< HEAD
    image = np.empty((3264, 2464, 3), dtype=np.uint8)
    camera.capture(image, 'rgb')
    cv2.imwrite(filename, image)
    #camera.capture(filename)
=======
    image = np.empty((2464 * 3280 * 3,), dtype=np.uint8)
    camera.capture(image, 'bgr')
    image = image.reshape((2464, 3280, 3))
    status = cv2.imwrite(filename, image)
    print(status)
>>>>>>> eac9a41d27d61bb3e842c7d989a90fa4c6aa4baf
    camera.stop_preview()
