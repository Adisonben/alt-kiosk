/*************************************************************
 * File: match_template.cpp
 * Description: Match two fingerprint templates (Base64 input)
 * Usage: ./match_template <base64_template1> <base64_template2>
 * Returns: 1 (match) or 0 (no match) to stdout
 * Exit code: 0 on success, 1 on error
 * Based on SecuGen SDK example
 *************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sgfplib.h"

LPSGFPM sgfplib = NULL;

int main(int argc, char **argv)
{
    long err;
    BOOL matched;
    DWORD score;
    BYTE *templateBuffer1 = NULL;
    BYTE *templateBuffer2 = NULL;
    DWORD templateSize1, templateSize2;

    // Check command line arguments
    if (argc != 3)
    {
        fprintf(stderr, "Usage: %s <template_file1> <template_file2>\n", argv[0]);
        fprintf(stderr, "Returns: 1 (match) or 0 (no match) to stdout\n");
        return 1;
    }

    // Create SGFPM object
    err = CreateSGFPMObject(&sgfplib);
    if (!sgfplib)
    {
        fprintf(stderr, "ERROR: Unable to create SGFPM object.\n");
        return 1;
    }

    // Initialize with auto-detect device (required for matching algorithm)
    err = sgfplib->Init(SG_DEV_AUTO);
    if (err != SGFDX_ERROR_NONE)
    {
        fprintf(stderr, "ERROR: Unable to initialize. Error: %ld\n", err);
        DestroySGFPMObject(sgfplib);
        return 1;
    }

    // Set template format to SG400 (must match the format used for scanning)
    err = sgfplib->SetTemplateFormat(TEMPLATE_FORMAT_SG400);
    if (err != SGFDX_ERROR_NONE)
    {
        fprintf(stderr, "ERROR: Failed to set template format. Error: %ld\n", err);
        DestroySGFPMObject(sgfplib);
        return 1;
    }

    // Get max template size for buffer allocation
    DWORD templateSizeMax;
    err = sgfplib->GetMaxTemplateSize(&templateSizeMax);
    if (err != SGFDX_ERROR_NONE)
    {
        fprintf(stderr, "ERROR: Failed to get max template size. Error: %ld\n", err);
        DestroySGFPMObject(sgfplib);
        return 1;
    }

    // Allocate buffers for templates
    templateBuffer1 = (BYTE*)malloc(templateSizeMax);
    templateBuffer2 = (BYTE*)malloc(templateSizeMax);
    if (!templateBuffer1 || !templateBuffer2)
    {
        fprintf(stderr, "ERROR: Memory allocation failed.\n");
        if (templateBuffer1) free(templateBuffer1);
        if (templateBuffer2) free(templateBuffer2);
        DestroySGFPMObject(sgfplib);
        return 1;
    }

    // Load Template 1 from file
    FILE *fp1 = fopen(argv[1], "rb");
    if (!fp1)
    {
        fprintf(stderr, "ERROR: Unable to open template file 1: %s\n", argv[1]);
        free(templateBuffer1);
        free(templateBuffer2);
        DestroySGFPMObject(sgfplib);
        return 1;
    }
    templateSize1 = fread(templateBuffer1, 1, templateSizeMax, fp1);
    fclose(fp1);
    if (templateSize1 == 0)
    {
        fprintf(stderr, "ERROR: Failed to read template 1 from %s\n", argv[1]);
        free(templateBuffer1);
        free(templateBuffer2);
        DestroySGFPMObject(sgfplib);
        return 1;
    }
    fprintf(stderr, "Loaded %ld bytes from %s\n", templateSize1, argv[1]);

    // Load Template 2 from file
    FILE *fp2 = fopen(argv[2], "rb");
    if (!fp2)
    {
        fprintf(stderr, "ERROR: Unable to open template file 2: %s\n", argv[2]);
        free(templateBuffer1);
        free(templateBuffer2);
        DestroySGFPMObject(sgfplib);
        return 1;
    }
    templateSize2 = fread(templateBuffer2, 1, templateSizeMax, fp2);
    fclose(fp2);
    if (templateSize2 == 0)
    {
        fprintf(stderr, "ERROR: Failed to read template 2 from %s\n", argv[2]);
        free(templateBuffer1);
        free(templateBuffer2);
        DestroySGFPMObject(sgfplib);
        return 1;
    }
    fprintf(stderr, "Loaded %ld bytes from %s\n", templateSize2, argv[2]);

    // Match templates using NORMAL security level
    err = sgfplib->MatchTemplate(templateBuffer1, templateBuffer2, SL_NORMAL, &matched);
    if (err != SGFDX_ERROR_NONE)
    {
        fprintf(stderr, "ERROR: Failed to match templates. Error: %ld\n", err);
        free(templateBuffer1);
        free(templateBuffer2);
        DestroySGFPMObject(sgfplib);
        return 1;
    }

    // Get matching score for debug info
    err = sgfplib->GetMatchingScore(templateBuffer1, templateBuffer2, &score);
    if (err == SGFDX_ERROR_NONE)
    {
        fprintf(stderr, "Matching score: %ld\n", score);
    }

    // Output result: 1 for match, 0 for no match
    if (matched)
    {
        printf("1\n");
        fprintf(stderr, "Result: MATCH\n");
    }
    else
    {
        printf("0\n");
        fprintf(stderr, "Result: NO MATCH\n");
    }

    // Cleanup
    free(templateBuffer1);
    free(templateBuffer2);
    DestroySGFPMObject(sgfplib);

    return 0;
}
