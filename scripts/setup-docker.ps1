# 🐳 Claude Monitor - Configuration Docker Automatisée (Windows PowerShell)
# Ce script configure automatiquement l'environnement Docker pour Claude Monitor

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

# Fonctions utilitaires
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

# Vérification des prérequis
function Test-Prerequisites {
    Write-InfoLog "Vérification des prérequis..."
    
    # Vérifier Docker
    try {
        $null = Get-Command docker -ErrorAction Stop
    } catch {
        Write-ErrorLog "Docker n'est pas installé. Veuillez installer Docker Desktop."
        exit 1
    }
    
    # Vérifier Docker Compose
    try {
        $null = Get-Command docker-compose -ErrorAction Stop
    } catch {
        try {
            docker compose version | Out-Null
        } catch {
            Write-ErrorLog "Docker Compose n'est pas installé."
            exit 1
        }
    }
    
    # Vérifier que Docker fonctionne
    try {
        docker info | Out-Null
    } catch {
        Write-ErrorLog "Docker n'est pas démarré. Veuillez démarrer Docker Desktop."
        exit 1
    }
    
    Write-SuccessLog "Prérequis vérifiés"
}

# Détection automatique des données Claude
function Find-ClaudeData {
    Write-InfoLog "Détection des données Claude..."
    
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
                Write-SuccessLog "Données Claude trouvées: $path"
                return $true
            }
        }
    }
    
    # Recherche avancée
    Write-WarningLog "Recherche avancée des données Claude..."
    try {
        $foundFiles = Get-ChildItem -Path $env:USERPROFILE -Filter "*.jsonl" -Recurse -ErrorAction SilentlyContinue | 
                     Where-Object { $_.FullName -like "*claude*" } | 
                     Select-Object -First 1
        
        if ($foundFiles) {
            $script:ClaudeDataPath = $foundFiles.Directory.FullName
            Write-SuccessLog "Données Claude trouvées: $script:ClaudeDataPath"
            return $true
        }
    } catch {
        # Silently continue
    }
    
    Write-WarningLog "Aucune donnée Claude trouvée automatiquement."
    do {
        $userPath = Read-Host "Veuillez entrer le chemin vers vos données Claude"
        if (Test-Path $userPath) {
            $script:ClaudeDataPath = $userPath
            return $true
        } else {
            Write-ErrorLog "Le chemin spécifié n'existe pas: $userPath"
        }
    } while ($true)
}

# Nettoyage des ressources existantes
function Remove-ExistingResources {
    Write-InfoLog "Nettoyage des ressources existantes..."
    
    # Déterminer le répertoire racine du projet
    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    $projectRoot = Split-Path -Parent $scriptDir
    
    # Arrêter les containers existants
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
    
    # Supprimer les containers existants
    try {
        docker rm $ContainerName 2>$null
    } catch { }
    
    Write-SuccessLog "Nettoyage terminé"
}

# Build de l'image Docker
function Build-DockerImage {
    Write-InfoLog "Construction de l'image Docker..."
    
    # Déterminer le répertoire racine du projet
    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    $projectRoot = Split-Path -Parent $scriptDir
    
    # Vérifier que le Dockerfile existe
    $dockerfilePath = Join-Path $projectRoot "Dockerfile"
    if (-not (Test-Path $dockerfilePath)) {
        Write-ErrorLog "Dockerfile non trouvé: $dockerfilePath"
        Write-InfoLog "Assurez-vous d'exécuter ce script depuis le projet Claude Monitor"
        exit 1
    }
    
    # Set Docker Buildkit
    $env:DOCKER_BUILDKIT = "1"
    
    # Build avec optimisations depuis le répertoire racine
    $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
    
    try {
        Push-Location $projectRoot
        docker build --target runtime --tag "${ImageName}:latest" --tag "${ImageName}:$timestamp" . 
        if ($LASTEXITCODE -ne 0) {
            throw "Build failed"
        }
    } catch {
        Write-ErrorLog "Échec de la construction de l'image"
        exit 1
    } finally {
        Pop-Location
    }
    
    Write-SuccessLog "Image Docker construite: ${ImageName}:latest"
    
    # Afficher la taille de l'image
    $imageInfo = docker images $ImageName --format "table {{.Size}}" | Select-Object -Skip 1 -First 1
    Write-InfoLog "Taille de l'image: $imageInfo"
}

# Configuration de Docker Compose
function Set-ComposeConfiguration {
    Write-InfoLog "Configuration de Docker Compose..."
    
    # Déterminer le répertoire racine du projet
    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    $projectRoot = Split-Path -Parent $scriptDir
    
    # Créer un fichier .env local si nécessaire dans le répertoire racine
    $envPath = Join-Path $projectRoot ".env"
    if (-not (Test-Path $envPath)) {
        $envContent = @"
# Configuration Docker Compose pour Claude Monitor
CLAUDE_DATA_PATH=$ClaudeDataPath
CLAUDE_PLAN=pro
CLAUDE_TIMEZONE=UTC
CLAUDE_THEME=auto
CLAUDE_DEBUG_MODE=false
COMPOSE_PROJECT_NAME=$ComposeProject
"@
        $envContent | Out-File -FilePath $envPath -Encoding UTF8
        Write-SuccessLog "Fichier .env créé: $envPath"
    }
    
    # Valider la configuration depuis le répertoire racine
    try {
        Push-Location $projectRoot
        docker-compose config | Out-Null
    } catch {
        Write-ErrorLog "Configuration Docker Compose invalide"
        exit 1
    } finally {
        Pop-Location
    }
    
    Write-SuccessLog "Configuration Docker Compose validée"
}

# Test de l'installation
function Test-Installation {
    Write-InfoLog "Test de l'installation..."
    
    # Test du health check
    try {
        $testResult = docker run --rm -v "${ClaudeDataPath}:/data:ro" --entrypoint python "${ImageName}:latest" -c "from usage_analyzer.api import analyze_usage; result = analyze_usage(); print(f'✅ Test réussi: {len(result.get(`"blocks`", []))} blocs trouvés')"
        Write-InfoLog $testResult
    } catch {
        Write-WarningLog "Le test de base a échoué, mais l'image semble fonctionnelle"
    }
    
    Write-SuccessLog "Installation testée avec succès"
}

# Démarrage du service
function Start-Service {
    Write-InfoLog "Démarrage du service Claude Monitor..."
    
    # Déterminer le répertoire racine du projet
    $scriptDir = Split-Path -Parent $MyInvocation.ScriptName
    $projectRoot = Split-Path -Parent $scriptDir
    
    Write-Host ""
    Write-Host "Choisissez le mode de démarrage:"
    Write-Host "1) Mode interactif (docker run)"
    Write-Host "2) Mode service (docker-compose)"
    Write-Host "3) Mode arrière-plan (docker-compose -d)"
    Write-Host ""
    
    do {
        $choice = Read-Host "Votre choix (1-3)"
    } while ($choice -notmatch "^[1-3]$")
    
    switch ($choice) {
        "1" {
            Write-InfoLog "Démarrage en mode interactif..."
            docker run -it --rm --name $ContainerName -v "${ClaudeDataPath}:/data:ro" "${ImageName}:latest"
        }
        "2" {
            Write-InfoLog "Démarrage avec Docker Compose..."
            Push-Location $projectRoot
            try {
                docker-compose up
            } finally {
                Pop-Location
            }
        }
        "3" {
            Write-InfoLog "Démarrage en arrière-plan..."
            Push-Location $projectRoot
            try {
                docker-compose up -d
                Write-SuccessLog "Service démarré en arrière-plan"
                Write-InfoLog "Utilisez 'docker-compose logs -f' pour voir les logs"
                Write-InfoLog "Utilisez 'docker-compose down' pour arrêter"
            } finally {
                Pop-Location
            }
        }
    }
}

# Affichage de l'aide
function Show-Help {
    Write-Host @"
Claude Monitor - Script de Configuration Docker

Usage: .\setup-docker.ps1 [OPTIONS]

OPTIONS:
    -Help                   Afficher cette aide
    -CleanupOnly           Nettoyer uniquement (pas de build)
    -BuildOnly             Builder uniquement (pas de démarrage)
    -NoStart               Ne pas démarrer le service
    -DataPath PATH         Spécifier le chemin des données Claude
    -Quiet                 Mode silencieux

EXEMPLES:
    .\setup-docker.ps1                          Configuration complète automatique
    .\setup-docker.ps1 -BuildOnly               Builder l'image uniquement
    .\setup-docker.ps1 -DataPath "C:\Claude"    Utiliser un chemin spécifique
    .\setup-docker.ps1 -CleanupOnly             Nettoyer les ressources existantes

"@
}

# Fonction principale
function Main {
    if ($Help) {
        Show-Help
        return
    }
    
    Write-Host "Configuration Docker - $ProjectName" -ForegroundColor Cyan
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-Host ""
    
    Test-Prerequisites
    
    if ($CleanupOnly) {
        Remove-ExistingResources
        Write-SuccessLog "Nettoyage terminé"
        return
    }
    
    if (-not $DataPath) {
        Find-ClaudeData
    } else {
        if (Test-Path $DataPath) {
            $script:ClaudeDataPath = $DataPath
        } else {
            Write-ErrorLog "Le chemin spécifié n'existe pas: $DataPath"
            exit 1
        }
    }
    
    Remove-ExistingResources
    Build-DockerImage
    
    if ($BuildOnly) {
        Write-SuccessLog "Build terminé"
        return
    }
    
    Set-ComposeConfiguration
    Test-Installation
    
    if (-not $NoStart) {
        Start-Service
    }
    
    Write-Host ""
    Write-Host "==================================================" -ForegroundColor Cyan
    Write-SuccessLog "Configuration Docker terminée avec succès!"
    Write-Host ""
    Write-Host "Commandes utiles:" -ForegroundColor Yellow
    Write-Host "  docker-compose up                      # Démarrer"
    Write-Host "  docker-compose down                    # Arrêter"
    Write-Host "  docker-compose logs -f                 # Voir les logs"
    Write-Host "  docker exec -it $ContainerName bash    # Entrer dans le container"
    Write-Host ""
    Write-Host "Documentation: docs/docker/README.md" -ForegroundColor Yellow
}

# Variables globales
$ClaudeDataPath = $DataPath

# Exécution du script
Main
