param([string]$Module,[string]$Request,[string]$Feed,[string]$History)
$ErrorActionPreference='Stop'
Import-Module $Module -Force
$decision=Get-PublisherDecision ([IO.File]::ReadAllText($Request)) ([IO.File]::ReadAllText($Feed)) $History
if($decision.State -ne 'ready'){throw 'Request not ready'}
if($decision.Request.Payload.Document.catalog.appVersion -ne '0.1.30'){throw 'Version'}
if($decision.Request.Payload.Document.sequence -ne 13){throw 'Sequence'}
if($decision.Request.Payload.Document.expiresAt -ne '2099-12-31T23:59:59.0000000+00:00'){throw 'Expiry'}
if(@($decision.Request.Payload.Document.catalog.profiles).Count -ne 1 -or $decision.Request.Payload.Document.catalog.profiles[0] -ne 'master'){throw 'Profile'}
if($decision.Request.Payload.Document.catalog.packages[0].sha256 -ne 'e9fd4ef13b444dc8333150511df750f9682d08a4e80350a2ad0746238c3d55ff'){throw 'Reviewed bytes'}
if($decision.Request.Notes[1] -notmatch '0.1.27' -or $decision.Request.Notes[1] -notmatch '0.1.30'){throw 'Transition disclosure'}
Write-Output 'HELPER_CHECKS=7'
