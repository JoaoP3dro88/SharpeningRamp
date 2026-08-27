; Inno Setup Script
[Setup]
AppName=Sharpening Scheduler
AppVersion=1.0.0
DefaultDirName={pf}\TitanSharpening
DefaultGroupName=Titan Production Tools
OutputDir=.\installer_output
OutputBaseFilename=SharpeningSchedulerSetup
Compression=lzma2
SolidCompression=yes

[Files]
Source: "dist\SharpeningScheduler\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Sharpening Scheduler"; Filename: "{app}\SharpeningScheduler.exe"
Name: "{commondesktop}\Sharpening Scheduler"; Filename: "{app}\SharpeningScheduler.exe"
