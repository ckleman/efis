import pygame
from pygame._sdl2 import touch

# Initialize Pygame
pygame.init()

# Set up the screen
screen_width, screen_height = 1024, 600
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("SunFounder Touch Input Test (Low-level)")

# Main loop
running = True
print("Polling touch devices. Touch the screen to get finger data.")

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # Poll touch devices directly
    num_devices = touch.get_num_devices()
    if num_devices > 0:
        first_device_id = touch.get_device(0)
        num_fingers = touch.get_num_fingers(first_device_id)

        if num_fingers > 0:
            # Get the first active finger
            finger_data = touch.get_finger(first_device_id, 0)
            normalized_x = finger_data['x']
            normalized_y = finger_data['y']

            # Convert to screen coordinates
            screen_x = int(normalized_x * screen_width)
            screen_y = int(normalized_y * screen_height)
            
            print(f"Active finger at: ({screen_x}, {screen_y})")

    # Update the display
    screen.fill((0, 0, 0))
    pygame.display.flip()

# Quit Pygame
pygame.quit()
