"""

Image processing utilities

"""

import numpy as np
from scipy import ndimage

def background_mask(mri, thresh_perc=1):
    """Creates the background mask from an MRI"""

    grad_magnitude = gradient_magnitude(mri)
    nonzero_grad_mag = grad_magnitude[grad_magnitude>0]

    thresh_val = np.percentile(nonzero_grad_mag.flatten(), thresh_perc)
    background_mask = grad_magnitude < thresh_val

    se36 = ndimage.generate_binary_structure(3, 6)
    closed = ndimage.binary_closing(background_mask, se36, iterations=6)
    final_mask = ndimage.binary_erosion(closed, se36, iterations=5)

    return final_mask


def gradient_magnitude(mri):
    """Computes the gradient magnitude"""

    grad = np.asarray(np.gradient(mri))
    grad_magnitude = np.sqrt(np.sum(np.power(grad, 2.), axis=0))

    return grad_magnitude


def mask_image(input_img, update_factor=0.5, init_percentile=2):
    """
    Estimates the foreground mask for a given image.

    Similar to 3dAutoMask from AFNI.
    """

    prev_clip_level = np.percentile(input_img, init_percentile)
    while True:
        mask_img = input_img >= prev_clip_level
        cur_clip_level = update_factor*np.median(input_img[mask_img])
        print((cur_clip_level, prev_clip_level))
        if np.isclose(cur_clip_level, prev_clip_level, rtol=0.05):
            break
        else:
            prev_clip_level = cur_clip_level

    se36 = ndimage.generate_binary_structure(3, 6)
    mask_img = ndimage.binary_closing(mask_img, se36, iterations=3)

    return mask_img
