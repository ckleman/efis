#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec 26 20:47:49 2022
Revised Tuesday Sep 30, 2025
@author: ckleman
"""


import pygame
import sys
import time
#from pygame.locals import *
#import pygame_menu
import math

'''
sudo pip3 install adafruit-circuitpython-bno08x adafruit-circuthpython-mprls adafruit-circuitpython-ads1x15
import board
import busio
import adafruit_mprls # import the pressure sensor
import adafruit_ads1x15.ads1015 as ADS # import library for ADS1015
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_bno08x
from adafruit_bno08x.i2c import BNO08X_I2C


# configure board I2C
i2c = busio.I2C(board.SCL, board.SDA, frequency=800000)


# configure sensors
mpr = adafruit_mprls.MPRLS(i2c, psi_min=0, psi_max=25) # pressure sensor
ads1 = ADS.ADS1015(i2c, 72) # the first ADC board
ads2 = ADS.ADS1015(i2c, 73) # the second ADC board
# ads3 = ADS.ADS1015(i2c, 74) # the third ADC board
# ads4 = ADS.ADS1015(i2c, 75) # the fourth ADC board
bno = BNO08X_I2C(i2c)

# To get board values:

# static pressure:
# SLP = mpr.pressure

# analog voltage
# OilPress = AnalogIn(ads1, ADS.P0) # for pin 0 on the first ADC board.

'''

screenWidth = 1024
screenHeight = 600

step = 0 # used to test rolling AH
pitchStep = 0 # used to test pitching AH
increasing = True # used to test pitching AH
angle_per_step = 1.5
pitchDeg = -15 # degrees of pitch reported by sensors
pitchPPD = 3.3 # pixels to shift per degree
baro = 1013.25 # hPa This is the SLP setting changed for the altimeter
baroSensor = 982 #hPa This is the value the sensor reads.
buttonPressTime = time.time()

pygame.init()
white = (255, 255, 255)
yellow = (250, 180, 5)
black = (0, 0, 0)

surface = pygame.display.set_mode((screenWidth, screenHeight))
pygame.display.set_caption('OpenEFIS')
main_menu = True
set_alt_menu = False
menuFont = pygame.font.Font('freesansbold.ttf', 18)
ALTfont = pygame.font.Font('freesansbold.ttf', 32)
ASfont = pygame.font.Font('freesansbold.ttf', 32)
pitchFont = pygame.font.Font('freesansbold.ttf', 12)

# Button properties
altBtn = pygame.draw.rect(surface, (200, 200, 200), pygame.Rect(874, 0, 150, 50), 0, 5)
incBaroBtn = pygame.draw.rect(surface, (135, 135, 135), pygame.Rect(880, 155, 100, 50), 0, 5)
decBaroBtn = pygame.draw.rect(surface, (135, 135, 135), pygame.Rect(720, 155, 100, 50), 0, 5)
fincBaroBtn = pygame.draw.rect(surface, (135, 135, 135), pygame.Rect(880, 225, 100, 50), 0, 5)
fdecBaroBtn = pygame.draw.rect(surface, (135, 135, 135), pygame.Rect(720, 225, 100, 50), 0, 5)
setAltBtn = pygame.draw.rect(surface, (135, 135, 135), pygame.Rect(825, 330, 150, 50), 0, 5)
exitBtn = pygame.draw.rect(surface, (200, 200, 200), pygame.Rect(75, 0, 100, 50), 0, 5)

def setAlt():
    global set_alt_menu
    if set_alt_menu:
        pygame.draw.rect(surface, (200, 200, 200), pygame.Rect(700, 100, 300, 300), 0, 5)
        
        global baro, buttonPressTime
        
        #incBaroBtn = pygame.draw.rect(surface, (135, 135, 135), pygame.Rect(880, 155, 100, 50), 0, 5)
        incBaroBtnTxt = ALTfont.render('+', True, black)
        incBaroBtnRect = incBaroBtnTxt.get_rect()
        incBaroBtnRect.center = (930, 175)
        surface.blit(incBaroBtnTxt, incBaroBtnRect)
        
        #decBaroBtn = pygame.draw.rect(surface, (135, 135, 135), pygame.Rect(720, 155, 100, 50), 0, 5)
        decBaroBtnTxt = ALTfont.render('-', True, black)
        decBaroBtnRect = decBaroBtnTxt.get_rect()
        decBaroBtnRect.center = (765, 175)
        surface.blit(decBaroBtnTxt, decBaroBtnRect)
        
        #fincBaroBtn = pygame.draw.rect(surface, (135, 135, 135), pygame.Rect(880, 225, 100, 50), 0, 5)
        fincBaroBtnTxt = ALTfont.render('+ +', True, black)
        fincBaroBtnRect = fincBaroBtnTxt.get_rect()
        fincBaroBtnRect.center = (930, 245)
        surface.blit(fincBaroBtnTxt, fincBaroBtnRect)
        
        #fdecBaroBtn = pygame.draw.rect(surface, (135, 135, 135), pygame.Rect(720, 225, 100, 50), 0, 5)
        fdecBaroBtnTxt = ALTfont.render('- -', True, black)
        fdecBaroBtnRect = fdecBaroBtnTxt.get_rect()
        fdecBaroBtnRect.center = (765, 245)
        surface.blit(fdecBaroBtnTxt, fdecBaroBtnRect)
        
        #setAltBtn = pygame.draw.rect(surface, (135, 135, 135), pygame.Rect(825, 330, 150, 50), 0, 5)
        setAltBtnTxt = ALTfont.render('Set', True, black)
        setAltBtnRect = setAltBtnTxt.get_rect()
        setAltBtnRect.center = (900, 355)
        surface.blit(setAltBtnTxt, setAltBtnRect)
        
        #pygame.draw.rect(surface, (135, 135, 135), pygame.Rect(880, 175, 100, 50), 0, 5)
        altTxt = ALTfont.render(str(int(getAlt()))+'  ft', True, black)
        altRect = altTxt.get_rect()
        altRect.center = (850, 300)
        surface.blit(altTxt, altRect)
        
        baroTxt = ALTfont.render('{:.2f}'.format(round((baro/33.863886666667), 2))+'  in-hg', True, black)
        #baroTxt = ALTfont.render(str(round((baro/33.863886666667), 2))+'  in-hg', True, black)
        baroRect = altTxt.get_rect()
        baroRect.center = (815, 125)
        surface.blit(baroTxt, baroRect)
'''        
        if incBaroBtn.collidepoint(pygame.mouse.get_pos()) and pygame.mouse.get_pressed()[0]:
            if((time.time() - buttonPressTime) > 0.25):
                baro += 0.33863886666667
                buttonPressTime = time.time()
        
        if decBaroBtn.collidepoint(pygame.mouse.get_pos()) and pygame.mouse.get_pressed()[0]:
            if((time.time() - buttonPressTime) > 0.25):
                baro -= 0.33863886666667
                buttonPressTime = time.time()
                
        if fincBaroBtn.collidepoint(pygame.mouse.get_pos()) and pygame.mouse.get_pressed()[0]:
            if((time.time() - buttonPressTime) > 0.25):
                baro += 03.3863886666667
                buttonPressTime = time.time()
        
        if fdecBaroBtn.collidepoint(pygame.mouse.get_pos()) and pygame.mouse.get_pressed()[0]:
            if((time.time() - buttonPressTime) > 0.25):
                baro -= 03.3863886666667
                buttonPressTime = time.time()        
        
        if setAltBtn.collidepoint(pygame.mouse.get_pos()) and pygame.mouse.get_pressed()[0]:
            set_alt_menu = False;
            
'''

def getAlt():
    h = (1 - (baroSensor/baro)**0.190284)*44307.69396 # calculate height in meters
    alt = h * 3.28084 # convert meters to feet
    alt = round(alt/10)*10 # round to 10 ft increments
    return alt


def getAirspeed():
    pass

def getVoltage():
    pass

def getOilPress():
    pass

def getOilTemp():
    pass

def getCHTs():
    pass

def draw_menu():
    altBtn = pygame.draw.rect(surface, (200, 200, 200), pygame.Rect(874, 0, 150, 50), 0, 5)
    altBtnTxt = menuFont.render('Altimeter', True, black)
    altBtnRect = altBtnTxt.get_rect()
    altBtnRect.center = (950, 25)
    surface.blit(altBtnTxt, altBtnRect)
    
    '''
    if altBtn.collidepoint(pygame.mouse.get_pos()) and pygame.mouse.get_pressed()[0]:
        global set_alt_menu
        set_alt_menu = True;
        menu = True
    else:
        menu = True'''
        
    exitBtn = pygame.draw.rect(surface, (200, 200, 200), pygame.Rect(75, 0, 100, 50), 0, 5)
    exitBtnTxt = menuFont.render('Exit', True, black)
    exitBtnRect = exitBtnTxt.get_rect()
    exitBtnRect.center = (125, 25)
    surface.blit(exitBtnTxt, exitBtnRect)
    menu = True;
    return menu
    

while True:
    if pygame.event.peek(pygame.QUIT):
        break
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if incBaroBtn.collidepoint(event.pos):
                if((time.time() - buttonPressTime) > 0.25):
                    baro += 0.33863886666667
                    buttonPressTime = time.time()
        
            if decBaroBtn.collidepoint(event.pos):
                if((time.time() - buttonPressTime) > 0.25):
                    baro -= 0.33863886666667
                    buttonPressTime = time.time()
                
            if fincBaroBtn.collidepoint(event.pos):
                if((time.time() - buttonPressTime) > 0.25):
                    baro += 03.3863886666667
                    buttonPressTime = time.time()
        
            if fdecBaroBtn.collidepoint(event.pos):
                if((time.time() - buttonPressTime) > 0.25):
                    baro -= 03.3863886666667
                    buttonPressTime = time.time()        
        
            if setAltBtn.collidepoint(event.pos):
                set_alt_menu = False;
                
            if altBtn.collidepoint(event.pos):
                #global set_alt_menu
                set_alt_menu = True;
            
            if exitBtn.collidepoint(event.pos):
                pygame.quit()
                sys.exit()
    
    pitchCorrection = pitchDeg * pitchPPD
    surface.fill((50, 110, 170))
    airspeed = ASfont.render(str(pitchDeg), True, white)
    airspeedRect = airspeed.get_rect()
    airspeedRect.center = (175, 300)
    
    altitude = getAlt()
    alt = ALTfont.render(str(int(altitude)), True, white)
    altRect = alt.get_rect()
    altRect.center = (850, 300)
    
    #pygame.draw.rect(surface, (50, 110, 170), pygame.Rect(0, 0-pitchCorrection, 1024, 300-pitchCorrection)) # sky
    pygame.draw.rect(surface, (190, 100, 40), pygame.Rect(0, 300+pitchCorrection, 1024, 1200)) # ground
    pygame.draw.line(surface, white, (0, 300+pitchCorrection), (1024, 300+pitchCorrection), 2) # horizon line
    
    pygame.draw.line(surface, white, (462, 250+pitchCorrection), (562, 250+pitchCorrection), 2) # 15 degrees up
    pitch15 = pitchFont.render('15', True, yellow); pitch15Rect = pitch15.get_rect(); pitch15Rect.center = (450, 260+pitchCorrection)
    pitch15r = pitchFont.render('15', True, yellow); pitch15Rectr = pitch15r.get_rect(); pitch15Rectr.center = (574, 260+pitchCorrection)
    
    pygame.draw.line(surface, white, (462, 200+pitchCorrection), (562, 200+pitchCorrection), 2) # 30 degrees up
    pitch30 = pitchFont.render('30', True, yellow); pitch30Rect = pitch30.get_rect(); pitch30Rect.center = (450, 210+pitchCorrection)
    pitch30r = pitchFont.render('30', True, yellow); pitch30Rectr = pitch30r.get_rect(); pitch30Rectr.center = (574, 210+pitchCorrection)
    
    pygame.draw.line(surface, white, (462, 150+pitchCorrection), (562, 150+pitchCorrection), 2) # 45 degrees up
    pitch45 = pitchFont.render('45', True, yellow); pitch45Rect = pitch45.get_rect(); pitch45Rect.center = (450, 160+pitchCorrection)
    pitch45r = pitchFont.render('45', True, yellow); pitch45Rectr = pitch45r.get_rect(); pitch45Rectr.center = (574, 160+pitchCorrection)
    
    pygame.draw.line(surface, white, (462, 100+pitchCorrection), (562, 100+pitchCorrection), 2) # 60 degrees up
    pitch60 = pitchFont.render('60', True, yellow); pitch60Rect = pitch60.get_rect(); pitch60Rect.center = (450, 110+pitchCorrection)
    pitch60r = pitchFont.render('60', True, yellow); pitch60Rectr = pitch60r.get_rect(); pitch60Rectr.center = (574, 110+pitchCorrection)
    
    pygame.draw.line(surface, white, (462, 50+pitchCorrection), (562, 50+pitchCorrection), 2) # 75 degrees up
    pitch75 = pitchFont.render('75', True, yellow); pitch75Rect = pitch75.get_rect(); pitch75Rect.center = (450, 60+pitchCorrection)
    pitch75r = pitchFont.render('75', True, yellow); pitch75Rectr = pitch75r.get_rect(); pitch75Rectr.center = (574, 60+pitchCorrection)
    
    pygame.draw.line(surface, white, (462, 0+pitchCorrection), (562, 0+pitchCorrection), 2) # 90 degrees up
    pitch90 = pitchFont.render('90', True, yellow); pitch90Rect = pitch90.get_rect(); pitch90Rect.center = (450, 10+pitchCorrection)
    pitch90r = pitchFont.render('90', True, yellow); pitch90Rectr = pitch90r.get_rect(); pitch90Rectr.center = (574, 10+pitchCorrection)
    
    pygame.draw.line(surface, white, (462, 350+pitchCorrection), (562, 350+pitchCorrection), 2) # 15 degrees down
    pitchm15 = pitchFont.render('-15', True, yellow); pitchm15Rect = pitchm15.get_rect(); pitchm15Rect.center = (450, 360+pitchCorrection)
    pitchm15r = pitchFont.render('-15', True, yellow); pitchm15Rectr = pitchm15r.get_rect(); pitchm15Rectr.center = (574, 360+pitchCorrection)
    
    pygame.draw.line(surface, white, (462, 400+pitchCorrection), (562, 400+pitchCorrection), 2) # 30 degrees down
    pitchm30 = pitchFont.render('-30', True, yellow); pitchm30Rect = pitchm30.get_rect(); pitchm30Rect.center = (450, 410+pitchCorrection)
    pitchm30r = pitchFont.render('-30', True, yellow); pitchm30Rectr = pitchm30r.get_rect(); pitchm30Rectr.center = (574, 410+pitchCorrection)
    
    pygame.draw.line(surface, white, (462, 450+pitchCorrection), (562, 450+pitchCorrection), 2) # 45 degrees down
    pitchm45 = pitchFont.render('-45', True, yellow); pitchm45Rect = pitchm45.get_rect(); pitchm45Rect.center = (450, 460+pitchCorrection)
    pitchm45r = pitchFont.render('-45', True, yellow); pitchm45Rectr = pitchm45r.get_rect(); pitchm45Rectr.center = (574, 460+pitchCorrection)
    
    pygame.draw.line(surface, white, (462, 500+pitchCorrection), (562, 500+pitchCorrection), 2) # 60 degrees down
    pitchm60 = pitchFont.render('-60', True, yellow); pitchm60Rect = pitchm60.get_rect(); pitchm60Rect.center = (450, 510+pitchCorrection)
    pitchm60r = pitchFont.render('-60', True, yellow); pitchm60Rectr = pitchm60r.get_rect(); pitchm60Rectr.center = (574, 510+pitchCorrection)
    
    pygame.draw.line(surface, white, (462, 550+pitchCorrection), (562, 550+pitchCorrection), 2) # 75 degrees down
    pitchm75 = pitchFont.render('-75', True, yellow); pitchm75Rect = pitchm75.get_rect(); pitchm75Rect.center = (450, 560+pitchCorrection)
    pitchm75r = pitchFont.render('-75', True, yellow); pitchm75Rectr = pitchm75r.get_rect(); pitchm75Rectr.center = (574, 560+pitchCorrection)
    
    pygame.draw.line(surface, white, (462, 600+pitchCorrection), (562, 600+pitchCorrection), 2) # 90 degrees down
    pitchm90 = pitchFont.render('-90', True, yellow); pitchm90Rect = pitchm90.get_rect(); pitchm90Rect.center = (450, 610+pitchCorrection)
    pitchm90r = pitchFont.render('-90', True, yellow); pitchm90Rectr = pitchm90r.get_rect(); pitchm90Rectr.center = (574, 610+pitchCorrection)
    
    pygame.draw.polygon(surface, white, ((505, 215),(519, 215),(512, 200))) # triangle for roll angle bug
    
    surface.blit(pitch15, pitch15Rect)
    surface.blit(pitch30, pitch30Rect)
    surface.blit(pitch45, pitch45Rect)
    surface.blit(pitch60, pitch60Rect)
    surface.blit(pitch75, pitch75Rect)
    surface.blit(pitch90, pitch90Rect)
    surface.blit(pitch15r, pitch15Rectr)
    surface.blit(pitch30r, pitch30Rectr)
    surface.blit(pitch45r, pitch45Rectr)
    surface.blit(pitch60r, pitch60Rectr)
    surface.blit(pitch75r, pitch75Rectr)
    surface.blit(pitch90r, pitch90Rectr)
    surface.blit(pitchm15, pitchm15Rect)
    surface.blit(pitchm30, pitchm30Rect)
    surface.blit(pitchm45, pitchm45Rect)
    surface.blit(pitchm60, pitchm60Rect)
    surface.blit(pitchm75, pitchm75Rect)
    surface.blit(pitchm90, pitchm90Rect)
    surface.blit(pitchm15r, pitchm15Rectr)
    surface.blit(pitchm30r, pitchm30Rectr)
    surface.blit(pitchm45r, pitchm45Rectr)
    surface.blit(pitchm60r, pitchm60Rectr)
    surface.blit(pitchm75r, pitchm75Rectr)
    surface.blit(pitchm90r, pitchm90Rectr)
    

    bankAngle = step * angle_per_step # used to increment bank angle, replace with actual bank angle
    rotated_surface = pygame.transform.rotozoom(surface, bankAngle,2)
    rect = rotated_surface.get_rect(center = (512, 300))
    pygame.draw.rect(surface, (50, 110, 170), pygame.Rect(0, 0, 1024, 600))
    
    surface.blit(rotated_surface, (rect.x, rect.y))
    pygame.draw.arc(surface, white, (312, 100, 400, 400), math.pi/4, 3*math.pi/4, width=5) # AH bank arc
    #pygame.draw.circle(surface, white, (512, 300), 200, width=5) # AH bank circle
    pygame.draw.circle(surface, white, (512, 300), 7, width=5) # airplane circle/dot
    pygame.draw.line(surface, white, (457, 300), (567, 300), 5) # airplane wings
    pygame.draw.line(surface, white, (712, 300), (737, 300), 5) # right horizon line
    pygame.draw.line(surface, white, (312, 300), (287, 300), 5) #left horizon line
    pygame.draw.line(surface, white, (512, 100), (512, 75), 5) # 0 degree bank roll line
    pygame.draw.line(surface, white, (564, 107), (570, 83), 5) # 15 deg left bank marker
    pygame.draw.line(surface, white, (612, 127), (625, 105), 5) # 30 deg left bank marker
    pygame.draw.line(surface, white, (653, 159), (671, 140), 5) # 45 deg left bank marker
    pygame.draw.line(surface, white, (685, 200), (707, 188), 5) # 60 deg left bank marker
    pygame.draw.line(surface, white, (460, 107), (454, 83), 5) # 15 deg right bank marker
    pygame.draw.line(surface, white, (412, 127), (399, 105), 5) # 30 deg right bank marker
    pygame.draw.line(surface, white, (371, 159), (353, 140), 5) # 45 deg right bank marker
    pygame.draw.line(surface, white, (339, 200), (317, 188), 5) # 60 deg right bank marker
    pygame.draw.rect(surface, (0, 0, 0), pygame.Rect(112, 275, 125, 50)) # airspeed box
    pygame.draw.rect(surface, (0, 0, 0), pygame.Rect(787, 275, 125, 50)) # altitude box  
    surface.blit(airspeed, airspeedRect)
    surface.blit(alt, altRect)
    if main_menu:
        main_menu = draw_menu()  
    draw_menu()
    if set_alt_menu:
        setAlt()
    pygame.display.update()
    pygame.time.Clock().tick(60)
    
    step += 1 # step for rolling AH
    if(increasing):
        pitchDeg += 1
        if(pitchDeg >= 90):
            increasing = False
    else:
        pitchDeg -= 1
        if pitchDeg <= -90:
            increasing = True
    
    
pygame.quit()
