#!/usr/bin/env python
# Python Photobooth by Malte Küppers
# based on the great work of Chris Evans
# see instructions at http://www.drumminhands.com/2014/06/15/raspberry-pi-photo-booth/
# For detailed german description see http://maltekueppers.de/dc/index.php?post/2015/06/16/Raspberry-Pi-Photobooth


import os
import glob
import time
from time import sleep
import RPi.GPIO as GPIO
import picamera
import atexit
import sys
import random
from PIL import Image
import smtplib
import socket
import pygame
from signal import alarm, signal, SIGALRM, SIGKILL
import gc
import subprocess

########################
### Variables Config ###
########################
led1_pin = 37 # LED 1
led2_pin = 15 # LED 2
led3_pin = 38 # LED 3
led4_pin = 33 # LED 4
button1_pin = 16 # pin for the big red button
button2_pin = 35 # pin for button to shutdown the pi
button3_pin = 36 # pin for button to end the program, but not shutdown the pi

total_pics = 4 # number of pics  to be taken
capture_delay = 2 # delay between pics
prep_delay = 1 # number of seconds at step 1 as users prep to have photo taken
gif_delay = 100 # How much time between frames in the animated gif
file_path = '/var/www/photos/' #where do you want to save the photos

w = 1280
h = 1024
transform_x = 1280 #how wide to scale the jpg when replaying
transfrom_y = 1024 #how high to scale the jpg when replaying
offset_x = 0 #350 #how far off to left corner to display photos
offset_y = 0 #how far off to left corner to display photos
replay_delay = 3 # how much to wait in-between showing pics on-screen after taking
replay_cycles = 3 # how many times to show each photo on-screen after taking

start_again = False
####################
### Other Config ###
####################
GPIO.setmode(GPIO.BOARD)
GPIO.setup(led1_pin,GPIO.OUT) # LED 1
GPIO.setup(led2_pin,GPIO.OUT) # LED 2
GPIO.setup(led3_pin,GPIO.OUT) # LED 3
GPIO.setup(led4_pin,GPIO.OUT) # LED 4
GPIO.setup(button1_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # falling edge detection on button 1
GPIO.setup(button2_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # falling edge detection on button 2
GPIO.setup(button3_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP) # falling edge detection on button 3
GPIO.output(led1_pin,False);
GPIO.output(led2_pin,False);
GPIO.output(led3_pin,False);
GPIO.output(led4_pin,False); #for some reason the pin turns on at the beginning of the program. why?????????????????????????????????

#################
### Functions ###
#################

def lightshow(stime):
	GPIO.output(led1_pin,False)
	GPIO.output(led2_pin,False)
	GPIO.output(led3_pin,False)
	sleep(stime)
	GPIO.output(led1_pin,True)
	sleep(stime)
	GPIO.output(led2_pin,True)
	sleep(stime)
	GPIO.output(led3_pin,True)		
	sleep(stime)
		

	
def reset_event_detection_shutdown():
	sleep(0.5)
	GPIO.remove_event_detect(button2_pin)
	sleep(0.1)
	GPIO.add_event_detect(button2_pin, GPIO.FALLING, callback=shut_it_down, bouncetime=300) 
	
def reset_event_detection_reboot():
	sleep(0.5)
	GPIO.remove_event_detect(button3_pin)
	sleep(0.1)
	GPIO.add_event_detect(button3_pin, GPIO.FALLING, callback=exit_photobooth, bouncetime=300) 


def cleanup():
  print('Ended abruptly')
  GPIO.cleanup()
atexit.register(cleanup)

def shut_it_down(channel):
	sleep(0.5)
	counter=0
	while GPIO.input(channel) == GPIO.LOW :
		counter=counter+1
		sleep(0.1)
	     
	if (counter >= 8): 
		print str(counter) + "counter"
		print "Shutting down..." 
		GPIO.remove_event_detect(button2_pin)
		lightshow(1)
		#GPIO.output(led1_pin,True);
		#GPIO.output(led2_pin,True);
		#GPIO.output(led3_pin,True);
		#GPIO.output(led4_pin,True);
		time.sleep(3)
		os.system("sudo shutdown now -h")
    	
	else:
		print "Press longer to shutdown!"
		print str(counter) + "counter"
		reset_event_detection_shutdown()


def exit_photobooth(channel):	
    sleep(0.5)
    print "reboot Call"
    counter=0 
    while GPIO.input(channel) == GPIO.LOW :
    	counter=counter+1
    	print "B-Press"
    	sleep(0.1)		
    	
	if (counter >= 2): 
		print str(counter) + "counter"
		print "Rebooting..." 
		GPIO.remove_event_detect(button3_pin)
		lightshow(1)
		#GPIO.output(led1_pin,True);
		#GPIO.output(led2_pin,True);
		#GPIO.output(led3_pin,True);
		#GPIO.output(led4_pin,True);
		time.sleep(3)
		os.system("sudo reboot")
    	
	else:
		print "Press longer to reboot!"
		print str(counter) + "counter"
		reset_event_detection_reboot()
    
def clear_pics(foo): #why is this function being passed an arguments?
    #delete files in folder on startup
	files = glob.glob(file_path + '*')
	for f in files:
		os.remove(f) 
	#light the lights in series to show completed
	print "Deleted previous pics"
	GPIO.output(led1_pin,False); #turn off the lights
	GPIO.output(led2_pin,False);
	GPIO.output(led3_pin,False);
	GPIO.output(led4_pin,False)
	pins = [led1_pin, led2_pin, led3_pin, led4_pin]
	for p in pins:
		GPIO.output(p,True); 
		sleep(0.25)
		GPIO.output(p,False);
		sleep(0.25)
       

def display_pics(jpg_group):
    # this section is an unbelievable nasty hack - for some reason Pygame
    # needs a keyboardinterrupt to initialise in some limited circs (second time running)
    class Alarm(Exception):
        pass
    def alarm_handler(signum, frame):
        raise Alarm
    signal(SIGALRM, alarm_handler)
    alarm(3)
    try:
        pygame.init()
        screen = pygame.display.set_mode((w,h),pygame.FULLSCREEN) 
        alarm(0)
    except Alarm:
        raise KeyboardInterrupt
    pygame.display.set_caption('Photo Booth Pics')
    pygame.mouse.set_visible(False) #hide the mouse cursor	
   
    filename = file_path + jpg_group + "-montage.jpg"
    img=pygame.image.load(filename) 
    img = pygame.transform.scale(img,(transform_x,transfrom_y))
    screen.blit(img,(offset_x,offset_y))
    pygame.display.flip() # update the display
    time.sleep(replay_delay*4) # pause 	
	 


def countdown_overlay( camera ):
    n=4
    for i  in range(1,n):
	gc.collect()
	# Load the arbitrarily sized image
    	img = Image.open(str(i)+'.png')
    	# Create an image padded to the required size with
    	# mode 'RGB'
    	pad = Image.new('RGB', (
        	((img.size[0] + 31) // 32) * 32,
        	((img.size[1] + 15) // 16) * 16,
        	))
    	# Paste the original image into the padded one
    	pad.paste(img, (0, 0))
	# Add the overlay with the padded image as the source,
    	# but the original image's dimensions
	o = camera.add_overlay(pad.tostring(), size=img.size)
    	# By default, the overlay is in layer 0, beneath the
	# preview (which defaults to layer 2). Here we make
    	# the new overlay semi-transparent, then move it above
	# the preview
	o.alpha = 100 #128
    	o.layer = 3
	sleep(1)
	camera.remove_overlay(o)
   	del img
   	del pad
	
def process_pics(now):
    # this section is an unbelievable nasty hack - for some reason Pygame
    # needs a keyboardinterrupt to initialise in some limited circs (second time running)
    class Alarm(Exception):
        pass
    def alarm_handler(signum, frame):
        raise Alarm
    signal(SIGALRM, alarm_handler)
    alarm(3)
    try:
        pygame.init()
        screen = pygame.display.set_mode((w,h),pygame.FULLSCREEN) 
        alarm(0)
    except Alarm:
        raise KeyboardInterrupt
    pygame.display.set_caption('Photo Booth Pics')
    pygame.mouse.set_visible(False) #hide the mouse cursor	
    filename = "wait.png"
    img=pygame.image.load(filename) 
    img = pygame.transform.scale(img,(transform_x,transfrom_y))
    screen.blit(img,(offset_x,offset_y))
    pygame.display.flip() # update the display
    GPIO.output(led3_pin,True) #turn on the LED
    graphicsmagick = "montage "+ file_path + now + "-01.jpg " + file_path + now + "-02.jpg " + file_path + now + "-03.jpg " + file_path + now + "-04.jpg -geometry 640x512+2+2 "+ file_path + now + "-montage.jpg "
    os.system(graphicsmagick)
    bilder_wech="cp "+ file_path + now + "-01.jpg " + file_path + now + "-02.jpg " + file_path + now + "-03.jpg " + file_path + now + "-04.jpg "+ file_path + "single/"
    os.system(bilder_wech)
    bilder_wech="rm -f "+ file_path + now + "-01.jpg " + file_path + now + "-02.jpg " + file_path + now + "-03.jpg " + file_path + now + "-04.jpg " 
    os.system(bilder_wech)
    pygame.quit()
     
			
# define the photo taking function for when the big button is pressed 
def start_photobooth(): 
	################################# Begin Step 1 ################################# 
	print "Get Ready"
	start_again = False 
	GPIO.output(led2_pin,True);
	camera = picamera.PiCamera()
	camera.framerate = 24
	camera.vflip = True
	camera.hflip = True
	camera.rotation = 180
	#camera.saturation = -100
	camera.start_preview()
	GPIO.output(led2_pin,False);
	sleep(0.5)
	countdown_overlay(camera)
	i=4 #iterate the blink of the light in prep, also gives a little time for the camera to warm up
	while i < prep_delay :
	  GPIO.output(led1_pin,True); sleep(.5) 
	  GPIO.output(led1_pin,False); sleep(.5); i+=1
	
	################################# Begin Step 2 #################################
	print "Taking pics" 
	now = time.strftime("%Y%m%d%H%M%S") #get the current date and time for the start of the filename
	try: #take the photos
		for i, filename in enumerate(camera.capture_continuous(file_path + now + '-' + '{counter:02d}.jpg')):
			GPIO.output(led2_pin,True) #turn on the LED
			print(filename)
			graphicsmagick = "composite -gravity southwest /home/pi/watermark3.png " + filename + " " + filename + "&"
			os.system(graphicsmagick)
			sleep(0.5) #pause the LED on for just a bit
			GPIO.output(led2_pin,False) #turn off the LED
			
			
			if i == total_pics-1:
				break
			else:
				sleep(capture_delay) # pause in-between shots
				countdown_overlay(camera)
	finally:
		camera.stop_preview()
		camera.close()
	########################### Begin Step 3 #################################
	print "Processing Pics..."
	
	process_pics(now) 
	GPIO.output(led3_pin,True) #turn on the LED
	GPIO.output(led3_pin,False) #turn off the LED
	########################### Begin Step 4 #################################
	#GPIO.output(led4_pin,True) #turn on the LED
	GPIO.output(led1_pin,True)
	try:
		display_pics(now)
	except Exception, e:
		tb = sys.exc_info()[2]
		traceback.print_exception(e.__class__, e, tb)
	pygame.quit()
	print "Done"
	#GPIO.output(led4_pin,False) #turn off the LED
	GPIO.output(led1_pin,False)
	random_pics(file_path)



def random_pics(file_path):
	GPIO.output(led2_pin,True)
	idle = True
	GPIO.add_event_detect(button1_pin, GPIO.FALLING)
	if GPIO.event_detected(button1_pin):
		#pygame.quit()
		print "IDLE set to false"
		idle = False
	class Alarm(Exception):
        	pass
	def alarm_handler(signum, frame):
        	raise Alarm
	signal(SIGALRM, alarm_handler)
	alarm(3)
	try:
        	pygame.init()
	        screen = pygame.display.set_mode((w,h),pygame.FULLSCREEN)
        	alarm(0)
	except Alarm:
        	raise KeyboardInterrupt
        	
	while not GPIO.event_detected(button1_pin) :
		piclist = list()
		x = 0
		for infile in glob.glob(os.path.join(file_path,'*.jpg')):
			piclist.append(infile)
		print random.choice(piclist)
		pygame.display.set_caption('Photo Booth Pics')
		pygame.mouse.set_visible(False) #hide the mouse cursor
		filename = random.choice(piclist)
		del piclist
		img=pygame.image.load(filename)
		img = pygame.transform.scale(img,(transform_x,transfrom_y))
		screen.blit(img,(offset_x,offset_y))
		pygame.display.flip() # update the display
		sleep(3)
		#print "next pic..."
		gc.collect()	

	pygame.quit()
	print "killed random image process"
	GPIO.remove_event_detect(button1_pin)
	start_again = True
	GPIO.output(led2_pin,False)
	
####################
### Main Program ###
####################

# when a falling edge is detected on button2_pin and button3_pin, regardless of whatever   
# else is happening in the program, their function will be run    
GPIO.add_event_detect(button2_pin, GPIO.FALLING, callback=shut_it_down, bouncetime=300) 

#choose one of the two following lines to be un-commented
GPIO.add_event_detect(button3_pin, GPIO.FALLING, callback=exit_photobooth, bouncetime=300) #use third button to exit python. Good while developing
#GPIO.add_event_detect(button3_pin, GPIO.FALLING, callback=clear_pics, bouncetime=300) #use the third button to clear pics stored on the SD card from previous events


print "Photo booth app running..." 
GPIO.output(led1_pin,True); #light up the lights to show the app is running
time.sleep(0.5)
GPIO.output(led2_pin,True);
time.sleep(0.5)
GPIO.output(led3_pin,True);
time.sleep(0.5)
GPIO.output(led4_pin,True);

#Falsche und defekte Bilder entfernen
systembefehl = "rm -f /var/www/photos/*-0*.jpg &"
os.system(systembefehl)
gc.enable()
print "OK"
while True:
	while start_again == False:
		GPIO.wait_for_edge(button1_pin, GPIO.FALLING)
		start_again = True
		GPIO.output(led1_pin,False); #turn off the lights
		GPIO.output(led2_pin,False);
		GPIO.output(led3_pin,False);
		GPIO.output(led4_pin,False);

	GPIO.output(led1_pin,True); #light up the lights to show the app is running
	
	time.sleep(0.3) #debounce
	
	start_photobooth()
	
