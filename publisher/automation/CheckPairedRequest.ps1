param([string]$Module,[string]$Request,[string]$Feed,[string]$History,[string]$Version,[int]$Sequence,[string]$MasterHash,[string]$UserHash,[int]$InstallerCount=2)
$ErrorActionPreference='Stop'
Import-Module $Module -Force
$decision=Get-PublisherDecision ([IO.File]::ReadAllText($Request)) ([IO.File]::ReadAllText($Feed)) $History
if($decision.State -ne 'ready'){throw 'Request not ready'}
$p=$decision.Request.Payload.Document
if($p.catalog.appVersion -ne $Version -or $p.sequence -ne $Sequence){throw 'Version/sequence'}
if($p.expiresAt -ne '2099-12-31T23:59:59.0000000+00:00'){throw 'Expiry'}
if((@($p.catalog.profiles) -join ',') -ne 'master,user'){throw 'Both profiles required'}
if(@($p.catalog.packages).Count -ne 2){throw 'Two packages required'}
if($p.catalog.packages[0].sha256 -ne $MasterHash -or $p.catalog.packages[1].sha256 -ne $UserHash){throw 'Exact paired bytes'}
if(@($decision.Request.Notes).Count -eq 0){throw 'Changes missing'}
if($InstallerCount -lt 0 -or $InstallerCount -gt 2 -or @($p.catalog.installers).Count -ne $InstallerCount){throw 'Requested installer scope differs'}
Write-Output 'HELPER_CHECKS=8'
