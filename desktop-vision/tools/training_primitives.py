"""Original synthetic game-style suit shapes; no pretrained weights."""
import cv2,numpy as np
from PIL import Image,ImageDraw,ImageFont
from recognizer import normalise_glyph

def draw_suit(index, angular=True):
    im = Image.new('L', (96, 96), 0); d = ImageDraw.Draw(im)
    if not angular:
        font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 75)
        s = ['♠', '♥', '♦', '♣'][index]
        d.text((48, 48), s, fill=255, font=font, anchor='mm')
    elif index == 0:
        d.polygon([(48, 8), (88, 48), (68, 68), (52, 52), (52, 74), (70, 84), (26, 84), (44, 74), (44, 52), (28, 68), (8, 48)], fill=255)
    elif index == 1:
        d.polygon([(8, 30), (28, 12), (48, 32), (68, 12), (88, 30), (48, 84)], fill=255)
    elif index == 2:
        d.polygon([(48, 5), (88, 48), (48, 91), (8, 48)], fill=255)
    else:
        for x,y in [(48, 22), (23, 47), (73, 47), (48, 72)]:
            d.polygon([(x, y-21), (x+21, y), (x, y+21), (x-21, y)], fill=255)
    a=np.asarray(im)
    return normalise_glyph(255-a, 'suit')
