## Project Description ##
We want to read text files (scripts) from a folder and do the following:

1. If there are any units in inches or feet, convert to metric with friendly format. 

Use a Python library to search the text for instances of:
digits followed by inches, IN.ft. 
Also look for the rare cases of spelled out units (e.g. five inches). Whenever there is a spelled out dimension, convert it to numeric (five inches=127 millimeters)

2. Remove all double quotes. 
-Change the units to milimeter using the following logic
< 100 mm → round to nearest 1 mm
≥ 100 mm → round to nearest 10 mm

## Development
-Go through all .txt files in the target folder.
-Create a log of any changes made:
    File Name | Dimension Found | Raw Conversion result | Final Conversion. 
-Save the resulting files under the same name in the Output folder

## Unit SYNC
This phase is to ensure that we change units in the English scripts from inches to milimeters. Develop a separate script to do the following:
- For every script file specified in UnitChange\UnitDetect\detectedunits.csv, find and open the equivalent German script from the user-specified directory. The matching pattern is that for 24SWAdvSketch02_07.txt the German script would be 02_07 - Gl-gest. Kurven_V01.txt. So, the last numeric *xx_xx.txt would be the begining of the German script xx_xx*.txt.
-The typical conversion is to multiply the dimension in inch to 25 (or 25.4) to get the milimeters. Find the German unit that is likely the converted value and log it. 
-As an output, I want a CSV (saved in this directory) similar to detectedunits.csv that lists German script name, English Script name dimention in inches and dimension in milimiaters if a direct conversion detected. If not, I want to just indicate that the specific dimension was not found. 

## Unit Update
Now based on the output in unit_sync_results.csv, open the corresponding English script and replace the dimension in inches to the equivalent in milimeter (as found in the German script). The format should be xx milimeters. 




