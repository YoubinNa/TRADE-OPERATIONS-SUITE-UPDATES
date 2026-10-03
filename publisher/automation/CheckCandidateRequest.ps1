param([string]$Module,[string]$Request,[string]$Feed,[string]$History,[string]$Version,[int]$Sequence,[string]$PackageHash)
$ErrorActionPreference='Stop'
Import-Module $Module -Force
$decision=Get-PublisherDecision ([IO.File]::ReadAllText($Request)) ([IO.File]::ReadAllText($Feed)) $History
if($decision.State -ne 'ready'){throw 'Request not ready'}
if($decision.Request.Payload.Document.catalog.appVersion -ne $Version){throw 'Version'}
if($decision.Request.Payload.Document.sequence -ne $Sequence){throw 'Sequence'}
if($decision.Request.Payload.Document.expiresAt -ne '2099-12-31T23:59:59.0000000+00:00'){throw 'Expiry'}
if(@($decision.Request.Payload.Document.catalog.profiles).Count -ne 1 -or $decision.Request.Payload.Document.catalog.profiles[0] -ne 'master'){throw 'Profile'}
if($decision.Request.Payload.Document.catalog.packages[0].sha256 -ne $PackageHash){throw 'Reviewed bytes'}
if(@($decision.Request.Notes).Count -eq 0){throw 'Changes missing'}
Write-Output 'HELPER_CHECKS=7'
