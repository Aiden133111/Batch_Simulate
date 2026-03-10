
# batch_simulate.ps1
# PowerShell script for Windows

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

function Show-Dialog {
    param(
        [string]$message,
        [string[]]$buttons
    )
    $form = New-Object Windows.Forms.Form
    $form.Text = "Select Option"
    $form.Size = New-Object Drawing.Size(350,150)
    $form.StartPosition = "CenterScreen"
    $label = New-Object Windows.Forms.Label
    $label.Text = $message
    $label.AutoSize = $true
    $label.Location = New-Object Drawing.Point(10,10)
    $form.Controls.Add($label)
    $result = $null
    $x = 10
    foreach ($btn in $buttons) {
        $button = New-Object Windows.Forms.Button
        $button.Text = $btn
        $button.Location = New-Object Drawing.Point($x,50)
        $button.Add_Click({ $result = $button.Text; $form.Close() })
        $form.Controls.Add($button)
        $x += 100
    }
    $form.ShowDialog() | Out-Null
    return $result
}

# 1. Choose Single or Batch
$CHOICE = Show-Dialog "Simulate a single protocol or a batch" @("Batch", "Single")

# 2. Select file or folder
if ($CHOICE -eq "Single") {
    $FileDialog = New-Object Windows.Forms.OpenFileDialog
    $FileDialog.Filter = "Python files (*.py)|*.py"
    $FileDialog.Title = "Select a .py protocol to proceed:"
    if ($FileDialog.ShowDialog() -eq "OK") {
        $SELECTED_DIR = $FileDialog.FileName
    } else {
        Write-Host "No file selected. Exiting."
        exit 1
    }
} else {
    $FolderDialog = New-Object Windows.Forms.FolderBrowserDialog
    $FolderDialog.Description = "Select a directory of .py protocols to proceed:"
    if ($FolderDialog.ShowDialog() -eq "OK") {
        $SELECTED_DIR = $FolderDialog.SelectedPath
    } else {
        Write-Host "No folder selected. Exiting."
        exit 1
    }
}

# 3. Select labware directory
$LabwareDialog = New-Object Windows.Forms.FolderBrowserDialog
$LabwareDialog.Description = "Please select the directory containing your labware definitions or cancel:"
if ($LabwareDialog.ShowDialog() -eq "OK") {
    $LABWARE_DIR = $LabwareDialog.SelectedPath
} else {
    $LABWARE_DIR = $null
}

$SELF_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition

Write-Host "Running Randomize RTP on selected directory and subdirectories..."
python "$SELF_DIR\Resources\Randomized_RTP.py" --file "$SELECTED_DIR" --assume_yes
if ($LASTEXITCODE -eq 0) {
    Write-Host "Randomization completed successfully."
} else {
    Write-Host "Randomization failed. Please check the error messages above."
    exit 1
}

Write-Host "Running Mass Simulation on selected directory and subdirectories..."
if ($LABWARE_DIR) {
    python "$SELF_DIR\Resources\Mass_Simulation.py" --silent --labware "$LABWARE_DIR" --assume_yes --cleanup-generated
} else {
    python "$SELF_DIR\Resources\Mass_Simulation.py" --silent --assume_yes --cleanup-generated
}

exit 0
