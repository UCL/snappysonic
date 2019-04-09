# coding=utf-8

"""Main loop for tracking visualisation"""
from sys import version_info
from cv2 import (rectangle, putText, circle, imread, imshow)
from numpy import zeros, uint8
from sksurgeryutils.common_overlay_apps import OverlayBaseApp
from sksurgerytorsosimulator.algorithms.algorithms import (configure_tracker,
                                                           lookupimage, noisy,
                                                           check_us_buffer)

class OverlayApp(OverlayBaseApp):
    """Inherits from OverlayBaseApp,
    adding code to read in video buffers, and display a frame
    of data that depends on the position of an external tracking system,
    e.g. surgeryarucotracker"""

    def __init__(self, config):
        """Overides overlay base app's init, to initialise the
        external tracking system. Together with a video source"""

        if "ultrasound buffer" in config:
            #and call the constructor for the base class
            if version_info > (3, 0):
                super().__init__(config.get("ultrasound buffer"))
            else:
                #super doesn't work the same in py2.7
                OverlayBaseApp.__init__(self, config.get("ultrasound buffer"))
        else:
            raise KeyError("Configuration must contain an ultrasound buffer")

        self._video_buffers = self._fill_video_buffers(config)

        self._tracker = None

        if "tracker config" in config:
            self._tracker = configure_tracker(config.get("tracker config"))


        self._backgroundimage = self._create_background_image(config)

        self._defaultimage = None
        if "default image" in config:
            self._defaultimage = imread(config.get("default image"))
        else:
            self._defaultimage = self._backgroundimage.copy()

    def update(self):
        """Update the background renderer with a new frame,
        move the model and render"""
        #add a method to move the rendered models
        image = self._get_image_with_tracking()

        self.vtk_overlay_window.set_video_image(image)
        self.vtk_overlay_window.Render()
        #self.vtk_overlay_window._RenderWindow.Render()

    def _get_image_with_tracking(self):
        """
        Internal method to get an image from the video
        buffer based on the tracker position
        """
        port_handles, _, _, tracking, _ = self._tracker.get_frame()

        tempimg = self._backgroundimage.copy()

        pts = None
        if port_handles:
            for i in range(len(port_handles)):
                if port_handles[i] == 0:
                    pts = (tracking[i][0, 3], tracking[i][1, 3])
                    circle(tempimg, pts, 5, [255, 255, 255])

        imshow('tracking', tempimg)

        if pts:
            for usbuffer in self._video_buffers:
                inframe, image = lookupimage(usbuffer, pts)
                if inframe:
                    return image

        temping2 = self._defaultimage.copy()
        temping3 = self._defaultimage.copy()
        noise = noisy(temping2)
        return noise + temping3

    def _fill_video_buffers(self, config):
        """
        internal method to fill video buffers
        """
        vidbuffers = []
        frame_counter = 0
        if "buffer descriptions" in config:
            for usbuffer in config.get("buffer descriptions"):
                check_us_buffer(usbuffer)
                start_frame = usbuffer.get("start frame")
                end_frame = usbuffer.get("end frame")
                tempbuffer = []
                if start_frame == frame_counter:
                    while frame_counter <= end_frame:
                        ret, image = self.video_source.read()
                        if not ret:
                            raise ValueError("Failed Reading video file",
                                             config.get("ultrasound buffer"))

                        frame_counter = frame_counter + 1
                        tempbuffer.append(image)
                print("adding frame ", len(tempbuffer), " images to buffer ",
                      usbuffer.get("name"))
                usbuffer.update({"buffer" : tempbuffer})

                vidbuffers.append(usbuffer)

        return vidbuffers

    def _create_background_image(self, config):
        """
        Creates a backgound image on which we can draw tracking information.
        """
        #this is a bit of a hack. Is there a better way? It assumes we're using
        #ARuCo
        _, bgimage = self._tracker._capture.read()
        bgimage = zeros((bgimage.shape), uint8)
        if "buffer descriptions" in config:
            for usbuffer in config.get("buffer descriptions"):
                pt0 = (usbuffer.get("x0"), usbuffer.get("y0"))
                pt1 = (usbuffer.get("x1"), usbuffer.get("y1"))
                rectangle(bgimage, pt0, pt1, [255, 255, 255])
                putText(bgimage, usbuffer.get("name"), pt0, 0,
                        1.0, [255, 255, 255])
        return bgimage
