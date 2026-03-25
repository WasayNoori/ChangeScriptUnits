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




