Review interface
===============================

Review interface refers to the interactive components (mouse and keyboard shortcuts) to assist with the review process.

Common elements
-----------------------------------

 - Double or right click would zoom the data being displayed
 - to rate, click the appropriate button, or press the key corresponding to its letter capitalized
    - This is usually the first later e.g. ``G`` for ``Good``, ``s`` for ``Spikes``, ``R`` for ``Review later``
    - but can also be others (capitalized) if there is overlap with other words: ``M` for ``i'M tired``
 - You can not advance to next sbuject/scan/unit without rating the current one. If you are not sure yet about how to rate it, or need additional details or discussion, simply use ``Review later`` option
 - to advance to next subject, click ``Next`` button.
 - to quit the review temporarily, click ``Quit`` button or press ``Ctrl+Q`` keys.


Review interface - Freesurfer
-------------------------------

 - double click in a given slice to zooms it large.
 - to toggle the colored overlay, right click or press the key ``t``. This works even when a slice is zoomed-in.
 - slider changes the transparency of the overlay in all slices.


Review interface - T1w MRI
-------------------------------
 - Double click to zoom in on any slice.
 - Double click the histogram to zoom the intensity distribution
 - keyboard shortcuts (capitalized letters in label) to rate artefacts
 - Click on any radio button to do the action represented
 - ``alt+s`` to saturate the brainmask to reveal in the hypo-intense texture in the background
     - Press ``alt+s`` again to toggle the saturation,
     - or press ``alt+u`` to show the original unsaturated image
 - ``alt+b`` to show the intensity distribution in background only (after masking out the brain as a single lump)


Review interface - Registration
-------------------------------
 - keyboard shortcuts (capitalized letters in label) to rate the quality of alignment
 - Double click the histogram to zoom the distribution of voxel-wise differences
 - Click on the radio buttons to change the type of blending - Animate or Checkerboard or Edges or Color mix etc.
 - ``alt+1`` to show only the first image
 - ``alt+2`` to show only the second image
 - Double click to zoom in on any slice.


Review interface - Functional MRI
----------------------------------
 - Right click to open a given time point (also known as frame)
 - Use the arrow keys to traverse in time (right/up keys to increase the frame, and left/down key to decrease it)
 - Right click again on slices to zoom them further full-window
 - Press ``alt+s`` to show the std. dev map (voxel-wise, over time)
 -
