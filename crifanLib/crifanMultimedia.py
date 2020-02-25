#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Filename: crifanMultimedia.py
Function: crifanLib's python multimedia (audio, video, image) related functions
Version: v20200225
Note:
1. latest version and more can found here:
https://github.com/crifan/crifanLibPython
"""

__author__ = "Crifan Li (admin@crifan.com)"
__version__ = "v20200225"
__copyright__ = "Copyright (c) 2020, Crifan Li"
__license__ = "GPL"

import os
import io
import re
import base64
import requests
import logging

cfgDefaultImageResample = None
try:
    from PIL import Image
    from PIL import ImageDraw
    cfgDefaultImageResample = Image.BICUBIC # Image.LANCZOS
except:
    print("need Pillow if use crifanMultimedia Image functions")

try:
    import audioread
except:
    print("need audioread if use crifanMultimedia audio functions")

from crifanLib.crifanSystem import runCommand, getCommandOutput
from crifanLib.crifanFile  import isFileObject, readBinDataFromFile, findNextNumberFilename
from crifanLib.crifanDatetime  import getCurDatetimeStr

################################################################################
# Config
################################################################################

################################################################################
# Constant
################################################################################
CURRENT_LIB_FILENAME = "crifanMultimedia"

################################################################################
# Global Variable
################################################################################
gVal = {
}

gConst = {
}

################################################################################
# Internal Function
################################################################################


################################################################################
# Python Multimedia Function
################################################################################

#----------------------------------------
# Audio/Video
#----------------------------------------

def formatFfmpegTimeStr(timeValue, seperatorHms=":", seperatorMs="."):
    """
        (1) format time to 00:00:03.110, for pass into ffmpeg to use:
            ffmpeg -i show_65586_video.mp4 -ss 00:00:03.110 -to 00:00:06.110 -b:a 128k extracted_audio_segment.mp3
        (2) also use format to 000003110, used for normal file name:
            audio_000003110_000006110.mp3

        Note:
            timeValue is class of datetime.time, NOT time
    """
    millisecond = int(timeValue.microsecond / 1000)
    ffmpegTimeStr = "%02d%s%02d%s%02d%s%03d" % (
        timeValue.hour, seperatorHms,
        timeValue.minute, seperatorHms,
        timeValue.second, seperatorMs,
        millisecond)
    return ffmpegTimeStr

def extractAudioFromVideo(
        videoFullPath,
        startTime=None,
        endTime= None,
        audioFullPath="",
        audioType="mp3",
        isOutputLog=False,
        isAskOverwrite=False,
    ):
    """
        extract specified time duration(startTime - endTime) auido (default mp3) file from video(.mp4) file
        Note:
            if startTime and endTime not specified, will ouput whole file audio
            internal using ffmpeg do convertion from mp4 to audio

        params:
        * `videoFullPath`: /video/path/video_name.mp4
        * `startTime`: start time of type datetime.time
        * `endTime`: end time of type datetime.time
        * `audioFullPath`:
            * `""`: -> /video/path/ + generated_audio_name.mp3
            * `"/audio/path/audio_name.mp3"`: /audio/path/audio_name.mp3
        * `isOutputLog`: ffmpeg show console log or not
            if not, will redirect to null device to omit it
        * `isAskOverwrite`: when existed file, whether ask overwrite or not
            default Not ask, that is force overwrite

        return: (bool, str, str)
                    True/False, audio path, error message string
    """
    extractIsOk = False
    extractedAudioPath = ""
    errMsg = "Unknown Error"

    if not audioFullPath:
        videoPath = os.path.dirname(videoFullPath)
        videoName = os.path.basename(videoFullPath)
        videoNameNoSuffix, videoSuffix = os.path.splitext(videoName) # 'show_14322648_video', '.mp4'

        timeDurationStr = ""
        if startTime and endTime:
            startTimeStrForName = formatFfmpegTimeStr(startTime, "", "")
            endTimeStrForName = formatFfmpegTimeStr(endTime, "", "")
            timeDurationStr = "_" + startTimeStrForName + "_" + endTimeStrForName

        audioFilename = videoNameNoSuffix + timeDurationStr + "." + audioType # 'show_14322648_video.mp3'
        audioFullPath = os.path.join(videoPath, audioFilename)

    timeDurationPara = ""
    if startTime and endTime:
        startTimeStrFfmpeg = formatFfmpegTimeStr(startTime)
        endTimeStrFfmpeg = formatFfmpegTimeStr(endTime)
        timeDurationPara = "-ss %s -to %s" % (startTimeStrFfmpeg, endTimeStrFfmpeg)

    extraPara = ""
    if not isAskOverwrite:
        extraPara += "-y"

    redirectOutputPara = ""
    if not isOutputLog:
        redirectOutputPara += "2> /dev/null"

    ffmpegCmd = "ffmpeg %s -i %s %s -b:a 128k %s %s" % (
        extraPara, videoFullPath, timeDurationPara, audioFullPath, redirectOutputPara)
    # print("ffmpegCmd=%s" % ffmpegCmd)

    # Example:
    # ffmpeg -y -i show_65586_video.mp4 -ss 00:00:03.110 -to 00:00:06.110 -b:a 128k show_65586_audio_000003110_000006110.mp3 2> /dev/null
    # ffmpeg -y -i /xxx/show_13304984_video.mp4 -ss 00:00:00.104 -to 00:00:04.566 -b:a 128k /xxx/user/5253/show/13304984/show_13304984_audio_000000104_000004566.mp3 2> /dev/null
    # ffmpeg -y -i show_65586_video.mp4 -b:a 128k show_65586_audio.mp3 2> /dev/null

    extractIsOk, errMsg = runCommand(ffmpegCmd)
    if extractIsOk:
        extractedAudioPath = audioFullPath

    return extractIsOk, extractedAudioPath, errMsg

#----------------------------------------
# Video
#----------------------------------------

def detectVideoDimension(videoFullPath):
    """
        detect video dimention(width x height) using ffprobe
    """
    # print("detectVideoDimension: videoFullPath=%s" % videoFullPath)
    videoWidth = 0
    videoHeight = 0

    ffprobeCmd = 'ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 %s' % videoFullPath
    # print("ffprobeCmd=%s" % ffprobeCmd)
    isRunCmdOk, consoleOutput = getCommandOutput(ffprobeCmd)
    # print("isRunCmdOk=%s, consoleOutput=%s" % (isRunCmdOk, consoleOutput))
    if isRunCmdOk:
        # extract width and height
        videoDimensionStr = consoleOutput # '640x360\n'
        foundDimension = re.search("(?P<videoWidth>\d+)x(?P<videoHeight>\d+)", videoDimensionStr)
        # print("foundDimension=%s" % foundDimension)
        if foundDimension:
            videoWidth = foundDimension.group("videoWidth")
            videoWidth = int(videoWidth)
            videoHeight = foundDimension.group("videoHeight")
            videoHeight = int(videoHeight)
            # print("videoWidth=%s, videoHeight=%s" % (videoWidth, videoHeight))

    return (videoWidth, videoHeight)

def removeVideoWatermark(inputVideoFullPath, outputVideoFullPath, watermarkPositionDict, isOverwrite=False, isVerbose=False):
    """
        remove video water mark using ffmpeg
    """
    # print("removeVideoWatermark: inputVideoFullPath=%s, outputVideoFullPath=%s, watermarkPositionDict=%s" % (inputVideoFullPath, outputVideoFullPath, watermarkPositionDict))
    # ffmpeg -i input_video.mp4 -vf "delogo=x=490:y=30:w=130:h=50" -c:a copy output_video.mp4
    # ffmpegCmd = 'ffmpeg -i %s -vf "delogo=x=490:y=30:w=130:h=50" -c:a copy %s' % (inputVideoFullPath, outputVideoFullPath)
    extraOptionList = []
    if isOverwrite:
        optionOverwrite = "-y"
        extraOptionList.append(optionOverwrite)
    if not isVerbose:
        optionLessOutput = "-hide_banner -loglevel error"
        extraOptionList.append(optionLessOutput)
    optionAvoidHang = "-nostdin"
    extraOptionList.append(optionAvoidHang)
    extraOptionStr = " ".join(extraOptionList)
    print("extraOptionStr=%s" % extraOptionStr)
    ffmpegCmd = 'ffmpeg %s -i %s -vf "delogo=x=%d:y=%d:w=%d:h=%d" -c:a copy %s' % \
        (extraOptionStr, inputVideoFullPath, watermarkPositionDict["x"], watermarkPositionDict["y"], watermarkPositionDict["w"], watermarkPositionDict["h"], outputVideoFullPath)
    print("ffmpegCmd=%s" % ffmpegCmd)
    # ffmpegCmd=ffmpeg -hide_banner -loglevel error -nostdin -i /xxx/video_normalWatermark_480w360h.mp4 -vf "delogo=x=324:y=28:w=140:h=53" -c:a copy /xxx/video_normalWatermark_480w360h_removedWatermark.mp4
    isRemovedWatermarkOk, errMsg = runCommand(ffmpegCmd)
    # print("isRemovedWatermarkOk=%s, errMsg=%s" % (isRemovedWatermarkOk, errMsg))
    return isRemovedWatermarkOk, errMsg

#----------------------------------------
# Audio
#----------------------------------------


def splitAudio(
        inputAudioFullPath,
        startTime,
        endTime,
        outputAudioFullPath="",
        isOutputLog=False,
        isAskOverwrite=False,
    ):
    """
        split specified time duration(startTime - endTime) auido (default mp3) file from input (whole) audio (normally .mp4) file
        Note:
            internal using ffmpeg, your system must installed ffmpeg

        params:
        * `inputAudioFullPath`: /whole/audio/path/input_audio_name.mp3
        * `startTime`: start time of type datetime.time
        * `endTime`: end time of type datetime.time
        * `outputAudioFullPath`:
            * `""`: -> /whole/audio/path/ + input_audio_name_{startTime}_{endTime}.mp3
            * `"/output/audio/path/output_audio_name.mp3"`: /output/audio/path/output_audio_name.mp3
        * `isOutputLog`: ffmpeg show console log or not
            if not, will redirect to null device to omit it
        * `isAskOverwrite`: when existed file, whether ask overwrite or not
            default Not ask, that is force overwrite

        return: (bool, str, str)
                    bool: extract OK or not
                    str: splitted audio full path
                    str: error message string
    """
    extractIsOk = False
    splittedAudioFullPath = ""
    errMsg = "Unknown Error"

    if not outputAudioFullPath:
        inputAudioPath = os.path.dirname(inputAudioFullPath)
        inputAudioName = os.path.basename(inputAudioFullPath)
        inputAudioNameNoSuffix, inputAudioSuffix = os.path.splitext(inputAudioName) # 'show_14322648_audio', '.mp3'

        startTimeStrForName = formatFfmpegTimeStr(startTime, "", "")
        endTimeStrForName = formatFfmpegTimeStr(endTime, "", "")
        timeDurationStr = "_" + startTimeStrForName + "_" + endTimeStrForName

        audioFilename = inputAudioNameNoSuffix + timeDurationStr + inputAudioSuffix # 'show_14322648_audio_000004237_000006336.mp3'
        outputAudioFullPath = os.path.join(inputAudioPath, audioFilename)

    startTimeStrFfmpeg = formatFfmpegTimeStr(startTime)
    endTimeStrFfmpeg = formatFfmpegTimeStr(endTime)
    timeDurationPara = "-ss %s -to %s" % (startTimeStrFfmpeg, endTimeStrFfmpeg) # '-ss 00:00:04.237 -to 00:00:06.336'

    extraPara = ""
    if not isAskOverwrite:
        extraPara += "-y"

    redirectOutputPara = ""
    if not isOutputLog:
        redirectOutputPara += "2> /dev/null"

    ffmpegCmd = "ffmpeg %s -i %s %s -b:a 128k %s %s" % (
        extraPara, inputAudioFullPath, timeDurationPara, outputAudioFullPath, redirectOutputPara)
    # print("ffmpegCmd=%s" % ffmpegCmd)

    # Example:
    # ffmpeg -y -i /xxx/show_14322648_audio.mp3 -ss 00:00:04.237 -to 00:00:06.336 -b:a 128k /xxx/show_14322648_audio_000004237_000006336.mp3 2> /dev/null

    extractIsOk, errMsg = runCommand(ffmpegCmd)
    if extractIsOk:
        splittedAudioFullPath = outputAudioFullPath

    return extractIsOk, splittedAudioFullPath, errMsg


def detectAudioMetaInfo(audioFullPath):
    """
        detect audio meta info: duration, channels, sampleRate
    """
    isOk = False
    errMsg = ""
    audioMetaInfo = {
        "duration": 0,
        "channels": 0,
        "sampleRate": 0,
    }

    try:
        with audioread.audio_open(audioFullPath) as audioFp:
            audioMetaInfo["duration"] = audioFp.duration
            audioMetaInfo["channels"] = audioFp.channels
            audioMetaInfo["sampleRate"] = audioFp.samplerate

            isOk = True
    except OSError as osErr:
        errMsg = "detect audio info error: %s" % str(osErr)
    except EOFError as eofErr:
        errMsg = "detect audio info error: %s" % str(eofErr)
    except audioread.DecodeError as decodeErr:
        errMsg = "detect audio info error: %s" % str(decodeErr)
    
    if isOk:
        return isOk, audioMetaInfo
    else:
        return isOk, errMsg

#----------------------------------------
# Image
#----------------------------------------

def resizeImage(inputImage,
                newSize,
                resample=cfgDefaultImageResample,
                outputFormat=None,
                outputImageFile=None
                ):
    """
        resize input image
        resize normally means become smaller, reduce size
    :param inputImage: image file object(fp) / filename / binary bytes
    :param newSize: (width, height)
    :param resample: PIL.Image.NEAREST, PIL.Image.BILINEAR, PIL.Image.BICUBIC, or PIL.Image.LANCZOS
        https://pillow.readthedocs.io/en/stable/reference/Image.html#PIL.Image.Image.thumbnail
    :param outputFormat: PNG/JPEG/BMP/GIF/TIFF/WebP/..., more refer:
        https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html
        if input image is filename with suffix, can omit this -> will infer from filename suffix
    :param outputImageFile: output image file filename
    :return:
        input image file filename: output resized image to outputImageFile
        input image binary bytes: resized image binary bytes
    """
    openableImage = None
    if isinstance(inputImage, str):
        openableImage = inputImage
    elif isFileObject(inputImage):
        openableImage = inputImage
    elif isinstance(inputImage, bytes):
        inputImageLen = len(inputImage)
        openableImage = io.BytesIO(inputImage)

    if openableImage:
        imageFile = Image.open(openableImage)
    elif isinstance(inputImage, Image.Image):
        imageFile = inputImage
    # <PIL.PngImagePlugin.PngImageFile image mode=RGBA size=3543x3543 at 0x1065F7A20>
    imageFile.thumbnail(newSize, resample)
    if outputImageFile:
        # save to file
        imageFile.save(outputImageFile)
        imageFile.close()
    else:
        # save and return binary byte
        imageOutput = io.BytesIO()
        # imageFile.save(imageOutput)
        outputImageFormat = None
        if outputFormat:
            outputImageFormat = outputFormat
        elif imageFile.format:
            outputImageFormat = imageFile.format
        imageFile.save(imageOutput, outputImageFormat)
        imageFile.close()
        compressedImageBytes = imageOutput.getvalue()
        compressedImageLen = len(compressedImageBytes)
        compressRatio = float(compressedImageLen)/float(inputImageLen)
        print("%s -> %s, resize ratio: %d%%" % (inputImageLen, compressedImageLen, int(compressRatio * 100)))
        return compressedImageBytes

def imageDrawRectangle(inputImgOrImgPath,
    rectLocation,
    outlineColor="green",
    outlineWidth=0,
    isShow=False,
    isAutoSave=True,
    isDrawClickedPosCircle=True,
    clickedPos=None,
):
    """Draw a rectangle for image (and a small circle), and show it,

    Args:
        inputImgOrImgPath (Image/str): a pillow(PIL) Image instance or image file path
        rectLocation (tuple/Rect): the rectangle location, (x, y, width, height)
        outlineColor (str): Color name
        outlineWidth (int): rectangle outline width
        isShow (bool): True to call image.show() for debug
        isAutoSave (bool): True to auto save the image file with drawed rectangle
        clickedPos (tuple): x,y of clicked postion; default None; if None, use the center point
        isDrawClickedPosCircle (bool): draw small circle in clicked point
    Returns:
        modified image
    Raises:
    """
    inputImg = inputImgOrImgPath
    if isinstance(inputImgOrImgPath, str):
        inputImg = Image.open(inputImgOrImgPath)
    draw = ImageDraw.Draw(inputImg)

    isRectObj = False
    hasX = hasattr(rectLocation, "x")
    hasY = hasattr(rectLocation, "y")
    hasWidth = hasattr(rectLocation, "width")
    hasHeight = hasattr(rectLocation, "height")
    isRectObj = hasX and hasY and hasWidth and hasHeight
    if isinstance(rectLocation, tuple):
        x, y, w, h = rectLocation
    elif isRectObj:
        x = rectLocation.x
        y = rectLocation.y
        w = rectLocation.width
        h = rectLocation.height

    x0 = x
    y0 = y
    x1 = x0 + w
    y1 = y0 + h
    draw.rectangle(
        [x0, y0, x1, y1],
        # fill="yellow",
        # outline="yellow",
        outline=outlineColor,
        width=outlineWidth,
    )

    if isDrawClickedPosCircle:
        # radius = 3
        # radius = 2
        radius = 4
        # circleOutline = "yellow"
        circleOutline = "red"
        circleLineWidthInt = 1
        # circleLineWidthInt = 3

        if clickedPos:
            clickedX, clickedY = clickedPos
        else:
            clickedX = x + w/2
            clickedY = y + h/2
        startPointInt = (int(clickedX - radius), int(clickedY - radius))
        endPointInt = (int(clickedX + radius), int(clickedY + radius))
        draw.ellipse([startPointInt, endPointInt], outline=circleOutline, width=circleLineWidthInt)

    if isShow:
        inputImg.show()

    if isAutoSave:
        intW = int(w)
        intH = int(h)
        drawRectStr = "_drawRect_%sx%s" % (intW, intH)

        inputImgPath = None
        if isinstance(inputImgOrImgPath, str):
            inputImgPath = str(inputImgOrImgPath)
        elif inputImg.filename:
            inputImgPath = str(inputImg.filename)

        if inputImgPath:
            imgFolderName, pointSuffix = os.path.splitext(inputImgPath)
            newImgFolderName = imgFolderName + drawRectStr
            newImgPath = newImgFolderName + pointSuffix
            newImgPath = findNextNumberFilename(newImgPath)
        else:
            curDatetimeStr = getCurDatetimeStr() # '20191219_143400'
            suffix = str(inputImg.format).lower() # 'jpeg'
            newImgFilename = "%s%s.%s" % (curDatetimeStr, drawRectStr, suffix)
            imgPathRoot = os.getcwd()
            newImgPath = os.path.join(imgPathRoot, newImgFilename)

        inputImg.save(newImgPath)

    return inputImg

################################################################################
# Test
################################################################################


if __name__ == '__main__':
    print("[crifanLib-%s] %s" % (CURRENT_LIB_FILENAME, __version__))