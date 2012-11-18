import math

import Image
import Levenshtein


class ImageCompare(object):
    """Compares two images."""

    def __init__(self, imga, imgb, maxsize=256):
        """Save a copy of the image objects."""

        sizea, sizeb = imga.size, imgb.size

        aspect = sizea[0] / sizea[1]

        newx = min(sizea[0], sizeb[0], maxsize)
        newy = min(math.ceil(sizea[1]*aspect),
                   math.ceil(sizeb[1]*aspect),
                   math.ceil(maxsize*aspect))

        # Rescale to a common size:
        imga = imga.resize((newx, newy), Image.BICUBIC)
        imgb = imgb.resize((newx, newy), Image.BICUBIC)

        # Store the images in B/W Int format
        self._imga = imga.convert('I')
        self._imgb = imgb.convert('I')

        # Store the common image size
        self.x, self.y = newx, newy

    def _img_int(self, img):
        """Convert an image to a list of pixels."""

        x, y = img.size

        for i in xrange(x):
            for j in xrange(y):
                yield img.getpixel((i, j))

    @property
    def imga_int(self):
        """Return a tuple representing the first image."""

        if not hasattr(self, '_imga_int'):
            self._imga_int = tuple(self._img_int(self._imga))

        return self._imga_int

    @property
    def imgb_int(self):
        """Return a tuple representing the second image."""

        if not hasattr(self, '_imgb_int'):
            self._imgb_int = tuple(self._img_int(self._imgb))

        return self._imgb_int

    @property
    def mse(self):
        """Return the mean square error between the two images."""

        if not hasattr(self, '_mse'):
            tmp = sum((a-b)**2 for a, b in zip(self.imga_int, self.imgb_int))
            self._mse = float(tmp) / self.x / self.y

        return self._mse

    @property
    def psnr(self):
        """Calculate the peak signal-to-noise ratio."""

        if not hasattr(self, '_psnr'):
            self._psnr = 20 * math.log(255 / math.sqrt(self.mse), 10)

        return self._psnr

    @property
    def nrmsd(self):
        """Calculate the normalized root mean square deviation."""

        if not hasattr(self, '_nrmsd'):
            self._nrmsd = math.sqrt(self.mse) / 255

        return self._nrmsd

    @property
    def levenshtein(self):
        """Calculate the Levenshtein distance."""

        if not hasattr(self, '_lv'):
            stra = ''.join((chr(x) for x in self.imga_int))
            strb = ''.join((chr(x) for x in self.imgb_int))

            lv = Levenshtein.distance(stra, strb)

            self._lv = float(lv) / self.x / self.y

        return self._lv


class FuzzyImageCompare(object):
    """Compares two images based on the previous comparison values."""

    def __init__(self, imga, imgb, lb=1, tol=15):
        """Store the images in the instance."""

        self._imga, self._imgb, self._lb, self._tol = imga, imgb, lb, tol

    def compare(self):
        """Run all the comparisons."""

        if hasattr(self, '_compare'):
            return self._compare

        lb, i = self._lb, 2

        diffs = {
            'levenshtein': [],
            'nrmsd': [],
            'psnr': [],
        }

        stop = {
            'levenshtein': False,
            'nrmsd': False,
            'psnr': False,
        }

        while not all(stop.values()):
            cmp = ImageCompare(self._imga, self._imgb, i)

            diff = diffs['levenshtein']
            if len(diff) >= lb+2 and \
                abs(diff[-1] - diff[-lb-1]) <= abs(diff[-lb-1] - diff[-lb-2]):
                stop['levenshtein'] = True
            else:
                diff.append(cmp.levenshtein)

            diff = diffs['nrmsd']
            if len(diff) >= lb+2 and \
                abs(diff[-1] - diff[-lb-1]) <= abs(diff[-lb-1] - diff[-lb-2]):
                stop['nrmsd'] = True
            else:
                diff.append(cmp.nrmsd)

            diff = diffs['psnr']
            if len(diff) >= lb+2 and \
                abs(diff[-1] - diff[-lb-1]) <= abs(diff[-lb-1] - diff[-lb-2]):
                stop['psnr'] = True
            else:
                try:
                    diff.append(cmp.psnr)
                except ZeroDivisionError:
                    diff.append(-1)  # to indicate that the images are identical

            i *= 2

        self._compare = {
            'levenshtein': 100 - diffs['levenshtein'][-1] * 100,
            'nrmsd': 100 - diffs['nrmsd'][-1] * 100,
            'psnr': diffs['psnr'][-1] == -1 and 100.0 or diffs['psnr'][-1],
        }

        return self._compare

    def similarity(self):
        """Try to calculate the image similarity."""

        cmp = self.compare()

        lnrmsd = (cmp['levenshtein'] + cmp['nrmsd']) / 2
        return lnrmsd
        return min(lnrmsd * cmp['psnr'] / self._tol, 100.0)  # TODO: fix psnr!
