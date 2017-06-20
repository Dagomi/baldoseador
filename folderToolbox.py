'''
Create all the folder structure.
@author: David Gomez david.gomez@i2cat.com
'''
import glob
import os
import shutil

import config


#External Tools
def OutputMainFolders(InputFileFullPath,OutputFileFullPath):
    
    print 
    print 
    # create #logger with 'Folder Generation'

    #=============================================================================
    #Create the Main Output Folder and define the log file
    #=============================================================================
    config.OuputhPath = OutputFileFullPath
    source_xml = os.path.realpath(InputFileFullPath)
    config.InputhPath = os.path.dirname(InputFileFullPath)
    path_list = source_xml.split(os.sep)
    name_premier_project = path_list[len(path_list)-2]
    

    config.PremierProjectName = name_premier_project

    absoluteOutputPath = OutputFileFullPath + "/" +  name_premier_project
    #Allows the videos in MPEG-DASH format: Video-> h264 or h265 and audio in aac.
    # This videos are removed at the end of the encoder process

    #Premier Folder
    if (not(os.path.exists(absoluteOutputPath))):
        os.mkdir(absoluteOutputPath)
        config.MainPathFolder = absoluteOutputPath

    #Temps Folder
    if (not(os.path.exists(absoluteOutputPath + "/temp_files"))):
        os.mkdir(absoluteOutputPath + "/temp_files")
        config.TempFolder = absoluteOutputPath + "/temp_files"

    #===========================================================================
    # Create Video Folder Structure
    #===========================================================================
    #Video Folder
    if (not(os.path.exists(absoluteOutputPath + "/" + "tiles"))):
        os.mkdir(absoluteOutputPath + "/" + "tiles")


