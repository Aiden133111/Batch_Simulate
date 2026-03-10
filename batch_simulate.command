#!/bin/zsh

# 1. Pop up a Finder window to select a folder

# Display the popup and capture the button clicked
CHOICE=$(osascript -e 'display dialog "Simulate a single protocol or a batch" buttons {"Batch", "Single"} default button "Single" with icon note' -e 'button returned of result')

if [[ "$CHOICE" == "Single" ]]; then
    SELECTED_DIR=$(osascript -e 'POSIX path of (choose file with prompt "Select a .py protocol to proceed:")' 2>/dev/null)
else
    SELECTED_DIR=$(osascript -e 'POSIX path of (choose folder with prompt "Select a directory of .py protocols to proceed:")' 2>/dev/null)
fi


LABWARE_DIR=$(osascript -e 'POSIX path of (choose folder with prompt "Please select the directory containing your labware definitions or cancel:")' 2>/dev/null)
SELF_DIR=${0:a:h}

# 2. Check if the user cancelled
if [ -z "$SELECTED_DIR" ]; then
    echo "No folder selected. Exiting."
    exit 1
fi


echo "Running Randomize RTP on selected directory and subdirectories..."
#/Users/aidenmcfadden/Desktop/CLI-Audit/Randomized_RTP.py
#
python3 "$SELF_DIR/Randomized_RTP.py" --file "$SELECTED_DIR" --assume_yes

if [ $? -eq 0 ]; then
    echo "Randomization completed successfully."
else
    echo "Randomization failed. Please check the error messages above."
    exit 1
fi

echo "Running Mass Simulation on selected directory and subdirectories..."
if [ -z "$LABWARE_DIR" ]; then
    python3 "$SELF_DIR/Mass_Simulation.py" --silent --assume_yes
else
    python3 "$SELF_DIR/Mass_Simulation.py" --silent --labware "$LABWARE_DIR" --assume_yes
fi

exit 0