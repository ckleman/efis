#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Dec 26 20:47:49 2022
Updated: unified mouse + touch handling, pitch/horizon refactor, 
optimized touch event polling for performance.
"""

import pygame
import time
import math

screenWidth = 1024
screenHeight = 600

step = 0
increasing = True
angle_per_step = 1.5
pitchDeg = -15
pitchPPD = 3.3
baro = 1013.25
baroSensor = 982

# --- Unified input handling ---
buttonPressTimes = {}
BUTTON_HOLD_DELAY = 0.25

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


# --- Helper Functions ---

def handle_button_press(button_id, rect, increment=0, set_menu=False, touch_positions=None):
    global baro, set_alt_menu, buttonPressTimes
    # Mouse input
    if pygame.mouse.get_pressed()[0] and rect.collidepoint(pygame.mouse.get_pos()):
        last_time = buttonPressTimes.get(button_id, 0)
        if (time.time() - last_time) > BUTTON_HOLD_DELAY:
            if increment != 0:
                baro += increment
            if set_menu:
                set_alt_menu = False
            buttonPressTimes[button_id] = time.time()
    # Touch input
    if touch_positions:
        for pos in touch_positions:
            if rect.collidepoint(pos):
                last_time = buttonPressTimes.get(button_id, 0)
                if (time.time() - last_time) > BUTTON_HOLD_DELAY:
                    if increment != 0:
                        baro += increment
                    if set_menu:
                        set_alt_menu = False
                    buttonPressTimes[button_id] = time.time()


def getAlt():
    h = (1 - (baroSensor / baro) ** 0.190284) * 44307.69396
    alt = h * 3.28084
    alt = round(alt / 10) * 10
    return alt


def draw_pitch_markers(pitchCorrection):
    markers = [90, 75, 60, 45, 30, 15]
    for deg in markers:
        # Up markers
        y = 300 - deg * pitchPPD + pitchCorrection
        surface.blit(pitchFont.render(str(deg), True, yellow), (450, y))
        surface.blit(pitchFont.render(str(deg), True, yellow), (574, y))
        pygame.draw.line(surface, white, (462, y), (562, y), 2)
        # Down markers
        y = 300 + deg * pitchPPD + pitchCorrection
        surface.blit(pitchFont.render(f'-{deg}', True, yellow), (450, y))
        surface.blit(pitchFont.render(f'-{deg}', True, yellow), (574, y))
        pygame.draw.line(surface, white, (462, y), (562, y), 2)


def draw_horizon_and_airplane(pitchCorrection):
    # AH bank arc
    pygame.draw.arc(surface, white, (312, 100, 400, 400), math.pi/4, 3*math.pi/4, 5)
    # Airplane center dot and wings
    pygame.draw.circle(surface, white, (512, 300), 7, 5)
    pygame.draw.line(surface, white, (457, 300), (567, 300), 5)
    pygame.draw.line(surface, white, (312, 300), (287, 300), 5)
    pygame.draw.line(surface, white, (712, 300), (737, 300), 5)
    # Roll triangle
    pygame.draw.polygon(surface, white, ((505, 215),(519, 215),(512, 200)))


def draw_menu(touch_positions):
    global set_alt_menu
    altBtn = pygame.draw.rect(surface, (200, 200, 200), pygame.Rect(874, 0, 150, 50), 0, 5)
    surface.blit(menuFont.render('Altimeter', True, black), (950-50, 25-10))
    handle_button_press("altBtn", altBtn, set_menu=True, touch_positions=touch_positions)
    return True


def setAlt(touch_positions):
    global set_alt_menu
    if not set_alt_menu:
        return
    pygame.draw.rect(surface, (200, 200, 200), pygame.Rect(700, 100, 300, 300), 0, 5)
    # Buttons: id, rect_params, increment, label
    buttons = [
        ("incBaroBtn", (880, 155, 100, 50), 0.33863886666667, '+'),
        ("decBaroBtn", (720, 155, 100, 50), -0.33863886666667, '-'),
        ("fincBaroBtn", (880, 225, 100, 50), 3.3863886666667, '+ +'),
        ("fdecBaroBtn", (720, 225, 100, 50), -3.3863886666667, '- -'),
        ("setAltBtn", (825, 330, 150, 50), 0, 'Set')
    ]
    for btn_id, rect_params, increment, label in buttons:
        rect = pygame.draw.rect(surface, (135, 135, 135), pygame.Rect(*rect_params), 0, 5)
        surface.blit(ALTfont.render(label, True, black), (rect.centerx-25, rect.centery-15))
        handle_button_press(btn_id, rect, increment=increment, set_menu=(btn_id=="setAltBtn"), touch_positions=touch_positions)
    # Display altitude and baro
    surface.blit(ALTfont.render(f"{int(getAlt())}  ft", True, black), (850-25, 300-15))
    surface.blit(ALTfont.render(f"{round(baro/33.863886666667,2)}  in-hg", True, black), (815-25, 125-15))


# --- Main Loop ---
while True:
    if pygame.event.peek(pygame.QUIT):
        break

    # --- Poll events once per frame ---
    touch_positions = []
    for event in pygame.event.get([pygame.FINGERDOWN]):
        touch_positions.append((int(event.x * screenWidth), int(event.y * screenHeight)))

    pitchCorrection = pitchDeg * pitchPPD
    surface.fill((50, 110, 170))
    airspeed = ASfont.render(str(pitchDeg), True, white)
    airspeedRect = airspeed.get_rect(center=(175, 300))
    alt = ALTfont.render(str(int(getAlt())), True, white)
    altRect = alt.get_rect(center=(850, 300))

    # Draw ground
    pygame.draw.rect(surface, (190, 100, 40), pygame.Rect(0, 300+pitchCorrection, 1024, 1200))

    # Draw pitch, horizon, and airplane
    draw_pitch_markers(pitchCorrection)
    draw_horizon_and_airplane(pitchCorrection)

    surface.blit(airspeed, airspeedRect)
    surface.blit(alt, altRect)

    draw_menu(touch_positions)
    if set_alt_menu:
        setAlt(touch_positions)

    pygame.display.update()
    pygame.time.Clock().tick(60)

    # Update AH roll and pitch
    step += 1
    if increasing:
        pitchDeg += 1
        if pitchDeg >= 90:
            increasing = False
    else:
        pitchDeg -= 1
        if pitchDeg <= -90:
            increasing = True

pygame.quit()
