/*************************************************************
 * File: finger_scan.cpp
 * Description: Fingerprint scan and output raw template
 * Usage: ./finger_scan [timeout_ms]
 * Based on SecuGen SDK example
 *************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sgfplib.h"

LPSGFPM sgfplib = NULL;

int getPIVQuality(int quality)
{
    if (quality <= 20) return 20;
    if (quality <= 40) return 40;
    if (quality <= 60) return 60;
    if (quality <= 80) return 80;
    return 100;
}

int main(int argc, char **argv)
{
    long err;
    DWORD templateSize, templateSizeMax;
    DWORD quality;
    BYTE *imageBuffer;
    BYTE *templateBuffer;
    SGDeviceInfoParam deviceInfo;
    SGFingerInfo fingerInfo;

    // Parse timeout argument (default: 10000ms)
    DWORD timeout = 10000;
    if (argc > 1)
        timeout = (DWORD)atol(argv[1]);

    err = CreateSGFPMObject(&sgfplib);
    if (!sgfplib)
        return 1;

    err = sgfplib->Init(SG_DEV_AUTO);
    if (err != SGFDX_ERROR_NONE)
    {
        DestroySGFPMObject(sgfplib);
        return 1;
    }

    err = sgfplib->OpenDevice(0);
    if (err != SGFDX_ERROR_NONE)
    {
        DestroySGFPMObject(sgfplib);
        return 1;
    }

    sgfplib->SetLedOn(true);

    deviceInfo.DeviceID = 0;
    err = sgfplib->GetDeviceInfo(&deviceInfo);
    if (err != SGFDX_ERROR_NONE)
    {
        sgfplib->CloseDevice();
        DestroySGFPMObject(sgfplib);
        return 1;
    }

    imageBuffer = (BYTE*)malloc(deviceInfo.ImageHeight * deviceInfo.ImageWidth);
    if (!imageBuffer)
    {
        sgfplib->CloseDevice();
        DestroySGFPMObject(sgfplib);
        return 1;
    }

    DWORD minQuality = 50;
    err = sgfplib->GetImageEx(imageBuffer, timeout, NULL, minQuality);

    sgfplib->SetLedOn(false);

    if (err != SGFDX_ERROR_NONE)
    {
        free(imageBuffer);
        sgfplib->CloseDevice();
        DestroySGFPMObject(sgfplib);
        return 1;
    }

    err = sgfplib->GetImageQuality(deviceInfo.ImageWidth, deviceInfo.ImageHeight, imageBuffer, &quality);
    if (err != SGFDX_ERROR_NONE)
        quality = 50;

    err = sgfplib->SetTemplateFormat(TEMPLATE_FORMAT_SG400);
    if (err != SGFDX_ERROR_NONE)
    {
        free(imageBuffer);
        sgfplib->CloseDevice();
        DestroySGFPMObject(sgfplib);
        return 1;
    }

    err = sgfplib->GetMaxTemplateSize(&templateSizeMax);
    if (err != SGFDX_ERROR_NONE)
    {
        free(imageBuffer);
        sgfplib->CloseDevice();
        DestroySGFPMObject(sgfplib);
        return 1;
    }

    templateBuffer = (BYTE*)malloc(templateSizeMax);
    if (!templateBuffer)
    {
        free(imageBuffer);
        sgfplib->CloseDevice();
        DestroySGFPMObject(sgfplib);
        return 1;
    }

    fingerInfo.FingerNumber = SG_FINGPOS_UK;
    fingerInfo.ViewNumber = 0;
    fingerInfo.ImpressionType = SG_IMPTYPE_LP;
    fingerInfo.ImageQuality = getPIVQuality(quality);

    err = sgfplib->CreateTemplate(&fingerInfo, imageBuffer, templateBuffer);
    if (err != SGFDX_ERROR_NONE)
    {
        free(templateBuffer);
        free(imageBuffer);
        sgfplib->CloseDevice();
        DestroySGFPMObject(sgfplib);
        return 1;
    }

    err = sgfplib->GetTemplateSize(templateBuffer, &templateSize);
    if (err != SGFDX_ERROR_NONE)
    {
        free(templateBuffer);
        free(imageBuffer);
        sgfplib->CloseDevice();
        DestroySGFPMObject(sgfplib);
        return 1;
    }

    fwrite(templateBuffer, 1, templateSize, stdout);

    free(templateBuffer);
    free(imageBuffer);
    sgfplib->CloseDevice();
    DestroySGFPMObject(sgfplib);

    return 0;
}
