# A small module-style script for validating PowerShell support in Red.
param(
    [Parameter(Mandatory)]
    [string]$Name = "Red"
)

function Get-Greeting {
    param([string]$Recipient)
    return "Hello, $Recipient!"
}

Write-Output (Get-Greeting -Recipient $Name)
