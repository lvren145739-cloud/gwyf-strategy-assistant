"""One-shot visible-card recognition. No game process access or network I/O."""
from pathlib import Path
import base64
import time
import cv2
import numpy as np
cv2.setNumThreads(1)

ROOT = Path(__file__).resolve().parent
RANKS = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
SUITS = ['spades', 'hearts', 'diamonds', 'clubs']


def png_data(im):
    ok, data = cv2.imencode('.png', im)
    if not ok:
        raise ValueError('图片编码失败')
    return 'data:image/png;base64,' + base64.b64encode(data).decode('ascii')


def order_corners(points):
    # Keep the polygon cyclic. Sorting top/bottom pairs can cross the edges
    # when a side-view card is strongly rotated.
    p = np.asarray(points, np.float32).reshape(4, 2)
    center = p.mean(axis=0)
    p = p[np.argsort(np.arctan2(p[:, 1]-center[1], p[:, 0]-center[0]))]
    return np.roll(p, -int(np.argmin(p.sum(axis=1))), axis=0).astype(np.float32)


def find_cards(image, region=None):
    """Paper contours inside a calibrated row; rejects text-sized components."""
    h, w = image.shape[:2]
    region = region or [0, 0, 1, 1]
    if len(region) != 4 or not all(np.isfinite(x) for x in region):
        raise ValueError('牌区无效')
    l, t, r, b = region
    if not 0 <= l < r <= 1 or not 0 <= t < b <= 1:
        raise ValueError('请在截图上框出有效牌区')
    x0, y0, x1, y1 = int(l*w), int(t*h), int(r*w), int(b*h)
    roi = image[y0:y1, x0:x1]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    # Neutral paper can be tinted by coloured table lighting.
    mask = cv2.inRange(hsv, np.array([0, 0, 190]), np.array([180, 90, 255]))
    # Keep separated neighbouring cards separated (closing can join their edges).
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    found = []
    for contour in contours:
        area = cv2.contourArea(contour)
        x, y, cw, ch = cv2.boundingRect(contour)
        if area < max(75, w*h*0.00009) or cw < 15 or ch < 10:
            continue
        if not .3 <= cw/ch <= 6 or area/(cw*ch) < .38:
            continue
        hull = cv2.convexHull(contour)
        if area/max(1, cv2.contourArea(hull)) < .80:
            continue
        q = None
        for epsilon in (.025, .035, .045, .06):
            candidate = cv2.approxPolyDP(hull, epsilon*cv2.arcLength(hull, True), True)
            if len(candidate) == 4:
                q = candidate
                break
        if q is None:
            continue
        if len(q) != 4 or not cv2.isContourConvex(q):
            continue
        q = order_corners(q)
        mat = cv2.getPerspectiveTransform(q, np.float32([[0, 0], [95, 0], [95, 127], [0, 127]]))
        card = cv2.warpPerspective(roi, mat, (96, 128))
        found.append({'rect': [x+x0, y+y0, cw, ch], 'quad': (q+[x0, y0]).tolist(),
                      'clipped': x <= 1 or y <= 1 or x+cw >= x1-x0-1 or y+ch >= y1-y0-1,
                      'image': card})
    return sorted(found, key=lambda c: c['rect'][0])


def normalise_glyph(image, kind='rank'):
    """Convert a rank/suit crop to a centred ink mask, invariant to ink colour."""
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(ink)
    components = [(i, s) for i, s in enumerate(stats[1:], 1) if s[4] >= 3]
    if not components:
        return np.zeros((48, 48), np.uint8)
    # Both rank 10 and the game's angular clubs have disconnected components.
    # Retain meaningful components so four-diamond clubs cannot become diamonds.
    biggest = max(s[4] for _, s in components)
    components = [(i, s) for i, s in components if s[4] >= biggest*.10]
    clean = np.zeros_like(ink)
    for i, _ in components:
        clean[labels == i] = 255
    ys, xs = np.where(clean > 0)
    if not len(xs):
        return np.zeros((48, 48), np.uint8)
    glyph = clean[ys.min():ys.max()+1, xs.min():xs.max()+1]
    gh, gw = glyph.shape
    scale = min(38/gw, 38/gh)
    gw, gh = max(1, round(gw*scale)), max(1, round(gh*scale))
    glyph = cv2.resize(glyph, (gw, gh), interpolation=cv2.INTER_AREA)
    out = np.zeros((48, 48), np.uint8)
    out[(48-gh)//2:(48-gh)//2+gh, (48-gw)//2:(48-gw)//2+gw] = glyph
    return out


def card_glyphs(card):
    # Game cards have the rank in the top left and a large suit lower right.
    return normalise_glyph(card[0:51, 0:43]), normalise_glyph(card[49:126, 27:95], 'suit')


