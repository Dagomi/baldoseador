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

import sys
import os

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter

__version__ = 0.1
__date__ = '2017-06-20'
__updated__ = '2017-06-20'

DEBUG = 0

class Tiler:
    '''Command line options.'''
    program_name = "Tiler"
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%s (%s)' % (program_version, program_build_date)

    # Setup argument parser
    parser = ArgumentParser(description="Tiler", formatter_class=RawDescriptionHelpFormatter)
    ##InputFileFullPath: Path of the Premiere Xml file
    parser.add_argument('-i','--InputFileFullPath')
    parser.add_argument('-V', '--version', action='version', version=__version__)
    

    # Process arguments
    args = parser.parse_args()


    if __name__ == '__main__':
        print ("i2caTiler")

        

