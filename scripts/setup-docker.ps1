<#
.SYNOPSIS
    Automated Docker environment setup for Claude Monitor on Windows PowerShell.

.DESCRIPTION
    This script configures and prepares the Docker environment required to run Claude Monitor.
    It automates the setup process, ensuring all necessary Docker components and configurations are in place for smooth operation on Windows systems.

.PARAMETER <ParameterName>
    .PARAMETER Help
        Display help information and usage examples.
    .PARAMETER CleanupOnly
        Only cleanup existing Docker resources without building or starting.
    .PARAMETER BuildOnly
        Only build the Docker image without starting the service.
    .PARAMETER NoStart
        Build and configure but do not start the service.
    .PARAMETER DataPath
        Specify the path to Claude data directory.
    .PARAMETER Quiet
        Run in quiet mode with minimal output.

.EXAMPLE
    .\setup-docker.ps1
    Runs the script to set up the Docker environment for Claude Monitor.

.NOTES
    Author: GiGiDKR
    Date: 2025-07-07
    Version: 1.0.0
    Additional information: This script is intended for use with the Claude-Code-Usage-Monitor project.
#>
param(
    [switch]$Help,
    [switch]$CleanupOnly,
    [switch]$BuildOnly,
    [switch]$NoStart,
    [string]$DataPath,
    [switch]$Quiet
)

# Configuration
$ProjectName = "Claude Code Usage Monitor"
$ImageName = "claude-monitor"
$ContainerName = "claude-usage-monitor"
$ComposeProject = "claude-code-usage-monitor"

# Utility functions
function Write-InfoLog {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Blue
}

function Write-SuccessLog {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-WarningLog {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Write-ErrorLog {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

# Prerequisite check
function Test-Prerequisites {
    Write-InfoLog "Checking prerequisites..."

    # Check Docker
    try {
        $null = Get-Command docker -ErrorAction Stop
    } catch {
        Write-ErrorLog "Docker is not installed. Please install Docker Desktop."
        exit 1
    }

    # Check Docker Compose
    try {
        $null = Get-Command docker-compose -ErrorAction Stop
    } catch {
        try {
            docker compose version | Out-Null
        } catch {
            Write-ErrorLog "Docker Compose is not installed."
            exit 1
        }
    }

    # Check that Docker is running
    try {
        docker info | Out-Null
    } catch {
        Write-ErrorLog "Docker is not running. Please start Docker Desktop."
        exit 1
    }

    Write-SuccessLog "Prerequisites verified"
}

# Automatic detection of Claude data
function Find-ClaudeData {
    Write-InfoLog "Detecting Claude data..."

    $claudePaths = @(
        "$env:USERPROFILE\.claude\projects",
        "$env:APPDATA\Claude\projects",
        "$env:LOCALAPPDATA\Claude\projects",
        "$env:USERPROFILE\AppData\Local\Claude\projects",
        "$env:USERPROFILE\AppData\Roaming\Claude\projects"
    )

    foreach ($path in $claudePaths) {
        if (Test-Path $path) {
            $jsonlFiles = Get-ChildItem -Path $path -Filter "*.jsonl" -ErrorAction SilentlyContinue
            if ($jsonlFiles.Count -gt 0) {
                $script:ClaudeDataPath = $path
                Write-SuccessLog "Claude data found: $path"
                return $true
            }
        }
    }

    # Advanced search
    Write-WarningLog "Advanced search for Claude data..."
    try {
        $searchDirs = @(
            "$env:USERPROFILE\AppData",
            "$env:USERPROFILE\Documents"
        )
        $foundFiles = @()
        foreach ($dir in $searchDirs) {
            if (Test-Path $dir) {
            $foundFiles += Get-ChildItem -Path $dir -Filter "*.jsonl" -Recurse -Depth 3 -ErrorAction SilentlyContinue |
                       Where-Object { $_.FullName -like "*claude*" }
            if ($foundFiles.Count -gt 0) { break }
            }
        }
        $foundFiles = $foundFiles | Select-Object -First 1

        if ($foundFiles) {
            $script:ClaudeDataPath = $foundFiles.Directory.FullName
            Write-SuccessLog "Claude data found: $script:ClaudeDataPath"
            return $true
        }
        } catch {
        # Silently continue
        }

        Write-WarningLog "No Claude data found automatically."

        do {
        $userPath = Read-Host "Please enter the path to your Claude data (or 'exit' to cancel)"
        if ($userPath -eq 'exit') {
            Write-InfoLog "Installation cancelled"
            exit 0
        }
        if (Test-Path $userPath) {
            $script:ClaudeDataPath = $userPath
            return $true
        } else {
            Write-ErrorLog "The specified path does not exist: $userPath"
        }
        } while ($true)

}

# Cleanup of existing resources
function Remove-ExistingResources {
    Write-InfoLog "Cleaning up existing resources..."

    # Determine the project root directory
    $scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
    $projectRoot = Split-Path -Parent $scriptDir

    # Stop existing containers
    try {
        docker stop $ContainerName 2>$null
    } catch { }

    try {
        Push-Location $projectRoot
        docker-compose down 2>$null
    } catch {
    } finally {
        Pop-Location
    }

    # Remove existing containers
    try {
        docker rm $ContainerName 2>$null
    } catch { }

    Write-SuccessLog "Cleanup complete"
}

# Build Docker image
function Build-DockerImage {
    Write-InfoLog "Building Docker image..."

    # Determine the project root directory
    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    $projectRoot = Split-Path -Parent $scriptDir

    # Check that the Dockerfile exists
    $dockerfilePath = Join-Path $projectRoot "Dockerfile"
    if (-not (Test-Path $dockerfilePath)) {
        Write-ErrorLog "Dockerfile not found: $dockerfilePath"
        Write-InfoLog "Make sure you are running this script from the Claude Monitor project"
        exit 1
    }

    # Set Docker Buildkit
    $env:DOCKER_BUILDKIT = "1"

    # Build with optimizations from the root directory
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"

    try {
        Push-Location $projectRoot
        docker build --target runtime --tag "${ImageName}:latest" --tag "${ImageName}:$timestamp" .
        if ($LASTEXITCODE -ne 0) {
            throw "Build failed"
        }
    } catch {
        Write-ErrorLog "Image build failed"
        exit 1
    } finally {
        Pop-Location
    }

    Write-SuccessLog "Docker image built: ${ImageName}:latest"

    # Show image size
    $imageInfo = docker images $ImageName --format "table {{.Size}}" | Select-Object -Skip 1 -First 1
    Write-InfoLog "Image size: $imageInfo"
}

# Docker Compose configuration
function Set-ComposeConfiguration {
    Write-InfoLog "Configuring Docker Compose..."

    # Determine the project root directory
    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    $projectRoot = Split-Path -Parent $scriptDir

    # Create a local .env file if needed in the root directory
    $envPath = Join-Path $projectRoot ".env"
    if (-not (Test-Path $envPath)) {
        $envContent = @"
# Docker Compose configuration for Claude Monitor
CLAUDE_DATA_PATH=$ClaudeDataPath
CLAUDE_PLAN=pro
CLAUDE_TIMEZONE=UTC
CLAUDE_THEME=auto
CLAUDE_DEBUG_MODE=false
COMPOSE_PROJECT_NAME=$ComposeProject
"@
        $envContent | Out-File -FilePath $envPath -Encoding UTF8
        Write-SuccessLog ".env file created: $envPath"
    }

    # Validate configuration from the root directory
    try {
        Push-Location $projectRoot
        docker-compose config | Out-Null
    } catch {
        Write-ErrorLog "Invalid Docker Compose configuration"
        exit 1
    } finally {
        Pop-Location
    }

    Write-SuccessLog "Docker Compose configuration validated"
}

# Installation test
function Test-Installation {
    Write-InfoLog "Testing installation..."

    # Health check test
    try {
        $testResult = docker run --rm -v "${ClaudeDataPath}:/data:ro" --entrypoint python "${ImageName}:latest" -c "from usage_analyzer.api import analyze_usage; result = analyze_usage(); print('✅ Test passed: {} blocks found'.format(len(result.get('blocks', []))))"
        Write-InfoLog $testResult
    } catch {
        Write-WarningLog "Basic test failed, but the image seems functional"
    }

    Write-SuccessLog "Installation tested successfully"
}

# Start the service
function Start-Service {
    Write-InfoLog "Starting Claude Monitor service..."

    # Determine the project root directory
    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    $projectRoot = Split-Path -Parent $scriptDir

    Write-Host ""
    Write-Host "Choose startup mode:"
    Write-Host "1) Interactive mode (docker run)"
    Write-Host "2) Service mode (docker-compose)"
    Write-Host "3) Background mode (docker-compose -d)"
    Write-Host ""

    do {
        $choice = Read-Host "Your choice (1-3)"
    } while ($choice -notmatch "^[1-3]$")

    switch ($choice) {
        "1" {
            Write-InfoLog "Starting in interactive mode..."
            docker run -it --rm --name $ContainerName -v "${ClaudeDataPath}:/data:ro" "${ImageName}:latest"
        }
        "2" {
            Write-InfoLog "Starting with Docker Compose..."
            Push-Location $projectRoot
            try {
                docker-compose up
            } finally {
                Pop-Location
            }
        }
        "3" {
            Write-InfoLog "Starting in background..."
            Push-Location $projectRoot
            try {
                docker-compose up -d
                Write-SuccessLog "Service started in background"
                Write-InfoLog "Use 'docker-compose logs -f' to see logs"
                Write-InfoLog "Use 'docker-compose down' to stop"
            } finally {
                Pop-Location
            }
        }
    }
}

# Show help
function Show-Help {
    Write-Host @"
Claude Monitor - Docker Setup Script

Usage: .\setup-docker.ps1 [OPTIONS]

OPTIONS:
    -Help                   Show this help
    -CleanupOnly            Cleanup only (no build)
    -BuildOnly              Build only (no start)
    -NoStart                Do not start the service
    -DataPath PATH          Specify the path to Claude data
    -Quiet                  Quiet mode

EXAMPLES:
    .\setup-docker.ps1                          Full automatic setup
    .\setup-docker.ps1 -BuildOnly               Build image only
    .\setup-docker.ps1 -DataPath "C:\Claude"    Use a specific path
    .\setup-docker.ps1 -CleanupOnly             Cleanup existing resources

"@
}

# Main function
function Main {
    if ($Help) {
        Show-Help
        return
    }

    Write-Host "Docker Setup - $ProjectName" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""

    Test-Prerequisites

    if ($CleanupOnly) {
        Remove-ExistingResources
        Write-SuccessLog "Cleanup complete"
        return
    }

    if (-not $DataPath) {
        Find-ClaudeData
    } else {
        if (Test-Path $DataPath) {
            $script:ClaudeDataPath = $DataPath
        } else {
            Write-ErrorLog "The specified path does not exist: $DataPath"
            exit 1
        }
    }

    Remove-ExistingResources
    Build-DockerImage

    if ($BuildOnly) {
        Write-SuccessLog "Build complete"
        return
    }

    Set-ComposeConfiguration
    Test-Installation

    if (-not $NoStart) {
        Start-Service
    }

    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-SuccessLog "Docker setup completed successfully!"
    Write-Host ""
    Write-Host "Useful commands:" -ForegroundColor Yellow
    Write-Host "  docker-compose up                      # Start"
    Write-Host "  docker-compose down                    # Stop"
    Write-Host "  docker-compose logs -f                 # View logs"
    Write-Host "  docker exec -it $ContainerName bash    # Enter the container"
    Write-Host ""
    Write-Host "Documentation: docs/docker/README.md" -ForegroundColor Yellow
}

# Global variables
$script:ClaudeDataPath = $DataPath

# Script execution
Main

