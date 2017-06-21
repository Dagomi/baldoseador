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
DEBUG = 0

# +------------+
# | 1 |  2 | 3 |
# |---+----+---|
# | 4 | 5  | 6 | 
# +--------+---+
        #top,bottom,left,right
TILE_1= ["0" , "360", "0", "640"]
TILE_2 = ["0" , "360", "640", "0"]
TILE_3 = ["360" , "0", "0", "640"]
TILE_4 = ["360" , "0", "640", "0"]

TILE_CUBE = ["0" , "1024", "0", "2048"]

class Tiler(object):
    def __init__(self):
        
        print ("i2caTiler")
        '''Command line options.'''
        program_name = "Tiler"
        program_version = "v%s" % __version__
        program_build_date = str(__updated__)
        program_version_message = '%s (%s)' % (program_version, program_build_date)
    
        # Setup argument parser
        parser = ArgumentParser(description="Tiler", formatter_class=RawDescriptionHelpFormatter)
        ##InputFileFullPath: Path of the Premiere Xml file
        parser.add_argument('-i','--InputFileFullPath')
        parser.add_argument('-o','--OutputFileFullPath')
        parser.add_argument('-d','--Debug')
        parser.add_argument('-v', '--version', action='version', version=__version__)
        
    
        # Process arguments
        args = parser.parse_args()
        
        folderToolbox.OutputMainFolders(args.InputFileFullPath,args.OutputFileFullPath)
        
        self.window = Gtk.Window()
        self.window.connect('destroy', self.quit)
        self.window.set_default_size(800, 450)
        self.drawingarea = Gtk.DrawingArea()
         
        self.window.add(self.drawingarea)

        # Create GStreamer pipeline
        self.create_named_pipe()
        self.create_elements(args)
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
     
    def create_elements (self,args):
        # Create GStreamer elements
        self.pipeline = Gst.Pipeline()
        self.source = Gst.ElementFactory.make("filesrc", "file-source")
        print args.InputFileFullPath
        self.source.set_property("location", args.InputFileFullPath)
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
        self.videobox.set_property("bottom", int(TILE_CUBE[1]))
        self.videobox.set_property("top", int(TILE_CUBE[0]))
        self.videobox.set_property("left",int(TILE_CUBE[2]))
        self.videobox.set_property("right",int(TILE_CUBE[3]))
        
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
        self.pipeline.add(self.videoconverter)
        if PLAYER:
            self.pipeline.add(self.videosync)
        if TileMode:
            self.pipeline.add(self.elementFilesink)
    def link_elements (self):
        #link
        self.source.link(self.Capsfilter)
        self.Capsfilter.link(self.decodebin)
        self.decodebin.link(self.videobox)   
        self.videobox.link(self.videoconverter)
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
        #elif structure_name.startswith("audio"):
        #    fa_pad = self.videobox.get_static_pad("sink")
        #    pad.link(fa_pad)
            
    def videobox_callback(self, decoder, pad):
        if VERBOSE :
            print("Videobox_callback")
        caps = pad.query_caps(None)
        structure_name = caps.to_string()
        if structure_name.startswith("video"):
            fv_pad = self.videoconverter.get_static_pad("sink")
            pad.link(fv_pad)
        #elif structure_name.startswith("audio"):
        #    fa_pad = self.videoconverter.get_static_pad("sink")
        #    pad.link(fa_pad)
    
    def videoconvert_callback(self, decoder, pad):
        if VERBOSE : 
            print("Videoconvert_callback")
        caps = pad.query_caps(None)
        structure_name = caps.to_string()
        if structure_name.startswith("video"):
            fv_pad = self.videoconverter.get_static_pad("sink")
            pad.link(fv_pad)
        #elif structure_name.startswith("audio"):
        #    fa_pad = self.videoconverter.get_static_pad("sink")
        #    pad.link(fa_pad)'/home/immersiatv/workspace/crop_x4_V_0_1/src/tile.pipe'
    def tee_callback(self,decoder,pad):
        if VERBOSE : 
            print("Videoconvert_callback")
        caps = pad.query_caps(None)
        structure_name = caps.to_string()
        if structure_name.startswith("video"):
            fv_pad = self.videoconverter.get_static_pad("sink")
            pad.link(fv_pad)
        #elif structure_name.startswith("audio"):
        #    fa_pad = self.videoconverter.get_static_pad("sink")
        #    pad.link(fa_pad)
            
    def startExternalEncoderAndMuxerProcess(self):
        print("Tile.startExternalEncoderAndMuxerProcess")
        #encoderSettings = self.encoderX264PlusTsMuxerSettings
        outputFullPath= config.OuputhPath
        outputFullPathTile= config.OuputhPath + "/"+ "Tile.mp4"
        inputEncoderFileFullPath = "/tmp/temp_files/tile.pipe"
        inputFramerate = '25'
        print outputFullPath
        command = "cd %s;ffmpeg -f rawvideo -r %s -pix_fmt %s -s 1024x1024 -y -i %s %s " % (outputFullPath,inputFramerate,DEFAULT_INTERNAL_CONVERSION_FORMAT,inputEncoderFileFullPath,outputFullPathTile)
       
        #os.system(command)
        print("Now running command: %s"% (command))
        self.encoderAndMuxerProcess = subprocess.Popen([command], shell = True)    
        

    def create_named_pipe (self):
        print("Create named pipe")
        pipe_name = "/tmp/temp_files/tile.pipe"
        if not os.path.exists(pipe_name):
            os.mkfifo(pipe_name)
            
p = Tiler()
p.run()
        

        

