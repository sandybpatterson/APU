"""Save one LDPlayer window copy to APU/look.png (read-only, taps nothing)."""
import os, sys
sys.path.insert(0, r"C:\Users\trent\foodstreet-bot")
import cv2, flash
flash.ON = True
img = flash.grab((1600, 900))
p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "look.png")
cv2.imwrite(p, img); print(p, img.shape)
