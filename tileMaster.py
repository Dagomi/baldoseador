#!/usr/local/bin/python2.7
# encoding: utf-8
'''
tileMaster -- shortdesc

tileMaster is a description

It defines classes_and_methods

@author:     David Gomez

@copyright:  2017 i2cat. All rights reserved.

@license:    license

@contact:    david.gomez@i2cat.net
'''

__version__ = 0.1
__date__ = '2017-06-20'
__updated__ = '2017-06-20'

import sys
import os
import gi
import subprocess
import time
gi.require_version('Gst', '1.0')
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, Gst, Gtk
from operator import itemgetter
from os import path
from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

# Needed for window.get_xid(), xvimagesink.set_window_handle(), respectively:
# from gi.repository import GdkX11, GstVideo

#Internal imports
import folderToolbox
import config

GObject.threads_init()
Gst.init(None)

DEFAULT_INTERNAL_CONVERSION_FORMAT = "yuv420p"
INPUT_FRAME_FORMATS = [{"identifier": "yuv420p", "ffmpeg" : "yuv420p", "gstreamer_fourcc" : "I420", "blocksize_ratio" : float(6) / float(4), "x264_profile" : "main"},
                       {"identifier": "yuv444p", "ffmpeg" : "yuv444p", "gstreamer_fourcc" : "Y444", "blocksize_ratio" : float(3) / float(1), "x264_profile" : "main"}, #high444 not supported by Apple products
                       {"identifier": "yuv422p", "ffmpeg" : "yuv422p", "gstreamer_fourcc" : "Y42B", "blocksize_ratio" : float(4) / float(2), "x264_profile" : "main"}, #high422 not supported by Apple products                                    
                       ]


VERBOSE = True
PLAYER = False     
TileMode =True
DEBUG = False

#===============================================================================
# Traspose
#===============================================================================
'''
0 = 90CounterCLockwise and Vertical Flip (default)
1 = 90Clockwise
2 = 90CounterClockwise
3 = 90Clockwise and Vertical Flip
4 = No transpose
'''
#===============================================================================
# VideoFlip Config
#===============================================================================
'''
Enum "GstVideoFlipMethod" Default: 0, "none"
(0): none             - Identity (no rotation)
(1): clockwise        - Rotate clockwise 90 degrees
(2): rotate-180       - Rotate 180 degrees
(3): counterclockwise - Rotate counter-clockwise 90 degrees
(4): horizontal-flip  - Flip horizontally
(5): vertical-flip    - Flip vertically
(6): upper-left-diagonal - Flip across upper left/lower right diagonal
(7): upper-right-diagonal - Flip across upper right/lower left diagonal
(8): automatic        - Select flip method based on image-orientation tag
'''
#===============================================================================
# Tile hardcode config
#===============================================================================


# 6 tiles [top,bottom,left,right,flip]
# +------------+
# | 1 |  2 | 3 |
# |---+----+---|
# | 4 | 5  | 6 | 
# +--------+---+

# TILE1 = [0, 1024, 0, 2048, 0] # Tile 0
# TILE1 = [0, 1024, 1024, 1024, 0] # Tile 1
# TILE1 = [0, 1024, 2048, 0 , 0] # Tile 2
# TILE1 = [1024, 0, 0, 2048 , 0] # Tile 3
# TILE1 = [1024, 0, 1024, 1024 , 0] # Tile 4
# TILE1 = [1024, 0, 2048, 0 , 0] # Tile 5

# ResolutionTile = '1024x1024'


# 2 tiles [top,bottom,left,right,flip]
# +-----------+
# |     0     |
# |-----------|
# |     1     | 
# +-----------+

ResolutionTile = "2880x960"
transpose = 4
# TILE1 = [0, 960, 0, 0, 0]
TILE1 = [960, 0, 0, 0, 0]



# 2 tiles Faceboock projection [top,bottom,left,right,flip]
# +---+---+
# |   |   |
# |   |   |
# | 1 | 0 |
# |   |   |
# |   |   |
# +---+---+

# ResolutionTile = "1024x1536"

# TILE1 = [1536, 0, 0, 512, 0]
# TILE1 = [1536, 0, 512, 0, 0]
# TILE1 = [0, 0, 0, 0, 0]
# transpose = 2

class Tiler(object):
    def __init__(self):
        
        print ("i2caTiler")
#         '''Command line options.'''
#         program_name = "Tiler"
#         program_version = "v%s" % __version__
#         program_build_date = str(__updated__)
#         program_version_message = '%s (%s)' % (program_version, program_build_date)
#     
#         # Setup argument parser
#         parser = ArgumentParser(description="Tiler", formatter_class=RawDescriptionHelpFormatter)
#         ##InputFileFullPath: Path of the Premiere Xml file
#         parser.add_argument('-i','--InputFileFullPath')
#         parser.add_argument('-o','--OutputFileFullPath')
#         parser.add_argument('-d','--Debug')
#         parser.add_argument('-v', '--version', action='version', version=__version__)
#         
#     
        # Process arguments
#         args = parser.parse_args()
        
        InputFileFullPath = "/home/immersiatv/Escritorio/CubemapDasher/Dash_Output/Ambisonic/Temp/sp_360left_1_cubemap_2880x1920.mp4"
        OutputFileFullPath = "/home/immersiatv/Escritorio/CubemapDasher/Dash_Output/Ambisonic/Temp"
        #folderToolbox.OutputMainFolders(args.InputFileFullPath,args.OutputFileFullPath)
        folderToolbox.OutputMainFolders(InputFileFullPath,OutputFileFullPath)

        self.window = Gtk.Window()
        self.window.connect('destroy', self.quit)
        self.window.set_default_size(800, 450)
        self.drawingarea = Gtk.DrawingArea()
        self.window.add(self.drawingarea)

        # Create GStreamer pipeline
        self.create_named_pipe()
        self.create_elements()
        self.add_elents()
        self.link_elements()
        if TileMode:
            self.startExternalEncoderAndMuxerProcess()

        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)

        # This is needed to make the video output in our DrawingArea:
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)
     
    def create_elements (self):
        # Create GStreamer elements
        self.pipeline = Gst.Pipeline()
        self.source = Gst.ElementFactory.make("filesrc", "file-source")
        self.source.set_property("location", "/home/immersiatv/Escritorio/CubemapDasher/Dash_Output/Ambisonic/Temp/sp_360left_1_cubemap_2880x1920.mp4")
        
        #Caps 
        caps = ("video/x-raw,format=I420,width=360,height=640")
        self.Capsfilter = Gst.ElementFactory.make("capsfilter","capsfilter")
        self.Capsfilter.set_property("caps", Gst.caps_from_string(caps))
        
        self.decodebin = Gst.ElementFactory.make('decodebin', 'decodebin')
        self.decodebin.connect("pad-added", self.decoder_callback)
        
        self.tee = Gst.ElementFactory.make('tee', 'tee')
        self.tee.connect("pad-added", self.tee_callback)
        
        self.videobox = Gst.ElementFactory.make ('videobox', 'videobox')
        self.videobox.connect("pad-added", self.videobox_callback)
        self.videobox.set_property("bottom", int(TILE1[1]))
        self.videobox.set_property("top", int(TILE1[0]))
        self.videobox.set_property("left",int(TILE1[2]))
        self.videobox.set_property("right",int(TILE1[3]))
        
        self.videoflip = Gst.ElementFactory.make ('videoflip', 'videoflip')
        self.videoflip.set_property("method", TILE1[4])
        
        if DEBUG:
            self.timeoverlay = Gst.ElementFactory.make ('timeoverlay', 'timeoverlay')
            self.timeoverlay.set_property("halignment", 1)
            self.timeoverlay.set_property("valignment", 4)
        
        self.videoconverter = Gst.ElementFactory.make ('videoconvert', 'videoconverter')
        self.decodebin.connect("pad-added", self.videoconvert_callback)
        
        #PLAYER
        if PLAYER:
            self.videosync = Gst.ElementFactory.make ('autovideosink', 'autovideosink')
        
        #filesync
        if TileMode:
            self.elementFilesink = Gst.ElementFactory.make("filesink", "filesink")
            self.elementFilesink.set_property("sync", False)
            self.elementFilesink.set_property("async", True)
            namepipe ="/tmp/temp_files/tile.pipe"
            self.elementFilesink.set_property("location", namepipe )
        
    
    def add_elents(self):
        # Add playbin to the pipeline        
        self.pipeline.add(self.source) 
        self.pipeline.add(self.decodebin)
        self.pipeline.add(self.Capsfilter)
        self.pipeline.add(self.videobox)
        self.pipeline.add(self.videoflip)
        self.pipeline.add(self.videoconverter)
        if PLAYER:
            self.pipeline.add(self.videosync)
        if TileMode:
            self.pipeline.add(self.elementFilesink)
        if DEBUG:
            self.pipeline.add(self.timeoverlay)
    
    def link_elements (self):
        #link
        self.source.link(self.Capsfilter)
        self.Capsfilter.link(self.decodebin)
        self.decodebin.link(self.videobox)
        self.videobox.link(self.videoflip)   
        
        if DEBUG:
            self.videoflip.link(self.timeoverlay)  
            self.timeoverlay.link(self.videoconverter)
        else:
            self.videoflip.link(self.videoconverter)
        
        if PLAYER:
            self.videoconverter.link(self.videosync)   
        
        if TileMode:
            self.videoconverter.link(self.elementFilesink)
        
    def run(self):
        
        #self.window.show_all()
        # You need to get the XID after window.show_all().  You shouldn't get it
        # in the on_sync_message() handler because threading issues will cause
        # segfaults there.
#         self.xid = self.drawingarea.get_property('window').get_xid()

        self.pipeline.set_state(Gst.State.PLAYING)
        Gtk.main()

    def quit(self, window):
        self.pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit()

    def on_sync_message(self, bus, msg):
        if msg.get_structure().get_name() == 'prepare-window-handle':
            if VERBOSE:     
                print("prepare-window-handle")
        msg.src.set_window_handle(self.xid)

    def on_eos(self, bus, msg):
        print('on_eos')
        self.pipeline.set_state(Gst.State.NULL)
        Gtk.main_quit()
        time.sleep(2)
        exit(1)


    def on_error(self, bus, msg):
        print('on_error():', msg.parse_error())

    def decoder_callback(self, decoder, pad):
        if VERBOSE :
            print("Decoder_callback")
        caps = pad.query_caps(None)
        structure_name = caps.to_string()
        if structure_name.startswith("video"):
            fv_pad = self.videobox.get_static_pad("sink")
            pad.link(fv_pad)
            
    def videobox_callback(self, decoder, pad):
        if VERBOSE :
            print("Videobox_callback")
        caps = pad.query_caps(None)
        structure_name = caps.to_string()
        if structure_name.startswith("video"):
            fv_pad = self.videoconverter.get_static_pad("sink")
            pad.link(fv_pad)

    
    def videoconvert_callback(self, decoder, pad):
        if VERBOSE : 
            print("Videoconvert_callback")
        caps = pad.query_caps(None)
        structure_name = caps.to_string()
        if structure_name.startswith("video"):
            fv_pad = self.videoconverter.get_static_pad("sink")
            pad.link(fv_pad)
    def tee_callback(self,decoder,pad):
        if VERBOSE : 
            print("Videoconvert_callback")
        caps = pad.query_caps(None)
        structure_name = caps.to_string()
        if structure_name.startswith("video"):
            fv_pad = self.videoconverter.get_static_pad("sink")
            pad.link(fv_pad)

            
    def startExternalEncoderAndMuxerProcess(self):
        print("Tile.startExternalEncoderAndMuxerProcess")
        outputFullPathTile= config.OuputhPath + "/"+ "Tile.mp4"
        inputEncoderFileFullPath = "/tmp/temp_files/tile.pipe"
        inputFramerate = config.frameRate
        
        base_cmd = 'ffmpeg -y -f rawvideo ' 
        base_cmd += '-r %s ' % inputFramerate
        base_cmd += '-pix_fmt %s ' % DEFAULT_INTERNAL_CONVERSION_FORMAT
        base_cmd += '-s %s ' % ResolutionTile
        base_cmd += '-i %s ' %  inputEncoderFileFullPath
        if transpose == 0 or transpose == 1 or transpose == 2 or transpose == 3:
            base_cmd += '-vf "transpose="%s ' % transpose
        base_cmd += '%s ' % outputFullPathTile
        
        #os.system(command)
        print("Now running command: %s"% (base_cmd))
        self.encoderAndMuxerProcess = subprocess.Popen([base_cmd], shell = True)    
        

    def create_named_pipe (self):
        print("Create named pipe")
        pipe_name = "/tmp/temp_files/tile.pipe"
        if not os.path.exists(pipe_name):
            os.mkfifo(pipe_name)
            
p = Tiler()
p.run()
        

        

