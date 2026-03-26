## Description
The aim of this is to read UFT text script files and re-structure to a JSON file. The JSON should have the following information:

Version:  0 is the default
Product: SOLIDWORKS is the default
COURSE: Specified by user before each run. 
Lesson and Topic: Comes from the name of the text file. The lats two digits before and after the the underscore (e.g. 24SWAdvSketch02_02.txt  means Lesson 2, topic 2)
Langauge: detect
Number of words: detect
Topic: Detected by AI. Main topic of the script


Actions:  Mouse actions. These are click guidance for the user. These should be detected by AI. 

If there are narratives between actions, let's separate them by blocks. So I want to see Action_blocks vs Narrative block. There could be several of each block in a script. 

Body: The entire body text of the script

## Process
## Phase 1
I have put a bunch of sample script files in the "INPUT" folder here. Go through them and learn about detecting "Action items" and ask clarifying questions on how to detect and categorize. Once completed, add the rules we learned back here in Claude.md file. This will inform our development later. 

## Phase 0 (introduction)
Our scripts are structred poorly for automation. Action items are not separately properly and actions and narrations are often tangled. As a precursor to structuring them, I need to show my team the issues. Propose a JSON file and create "Critique Reports" for 10 random script files from the input folder.  categorieze segments or sentenevs as vaghue, mixed, unclear,etc. For each script file, create a NEW json file with suggested structure, clearly separating Narration blocks from Action Blocks. Ask for clarity if needed. 

## StreamLit
I want an elegant way to display the information in the Critique report in an interface. A streamlit online page that allows me to drop a JSON file and it displays the information. Meta data can be all displayed in one box and Issues/Issue notes clearly highlighted or shown. Create a new python file for this part as this might be temporary. 
