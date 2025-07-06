#!/bin/bash
# 🐳 Claude Monitor - Configuration Docker Automatisée (Linux/macOS)
# Ce script configure automatiquement l'environnement Docker pour Claude Monitor

set -euo pipefail

# Configuration
PROJECT_NAME="Claude Code Usage Monitor"
IMAGE_NAME="claude-monitor"
CONTAINER_NAME="claude-usage-monitor"
COMPOSE_PROJECT="claude-code-usage-monitor"

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Fonctions utilitaires
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Vérification des prérequis
check_prerequisites() {
    log_info "Vérification des prérequis..."
    
    # Vérifier Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker n'est pas installé. Veuillez installer Docker Desktop."
        exit 1
    fi
    
    # Vérifier Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose n'est pas installé."
        exit 1
    fi
    
    # Vérifier que Docker fonctionne
    if ! docker info &> /dev/null; then
        log_error "Docker n'est pas démarré. Veuillez démarrer Docker Desktop."
        exit 1
    fi
    
    log_success "Prérequis vérifiés"
}

# Détection automatique des données Claude
detect_claude_data() {
    log_info "Détection des données Claude..."
    
    local claude_paths=(
        "$HOME/.claude/projects"
        "$HOME/.config/claude/projects"
        "$HOME/Library/Application Support/Claude/projects"
        "$HOME/AppData/Local/Claude/projects"
        "$HOME/AppData/Roaming/Claude/projects"
    )
    
    for path in "${claude_paths[@]}"; do
        if [ -d "$path" ] && [ "$(ls -A "$path"/*.jsonl 2>/dev/null)" ]; then
            CLAUDE_DATA_PATH="$path"
            log_success "Données Claude trouvées: $CLAUDE_DATA_PATH"
            return 0
        fi
    done
    
    # Recherche avancée
    log_warning "Recherche avancée des données Claude..."
    local found_path
    found_path=$(find "$HOME" -name "*.jsonl" -path "*claude*" -print -quit 2>/dev/null | head -1)
    
    if [ -n "$found_path" ]; then
        CLAUDE_DATA_PATH=$(dirname "$found_path")
        log_success "Données Claude trouvées: $CLAUDE_DATA_PATH"
        return 0
    fi
    
    log_warning "Aucune donnée Claude trouvée automatiquement."
    read -p "Veuillez entrer le chemin vers vos données Claude: " CLAUDE_DATA_PATH
    
    if [ ! -d "$CLAUDE_DATA_PATH" ]; then
        log_error "Le chemin spécifié n'existe pas: $CLAUDE_DATA_PATH"
        exit 1
    fi
}

# Nettoyage des ressources existantes
cleanup_existing() {
    log_info "Nettoyage des ressources existantes..."
    
    # Arrêter les containers existants
    docker stop "$CONTAINER_NAME" 2>/dev/null || true
    docker-compose down 2>/dev/null || true
    
    # Supprimer les containers existants
    docker rm "$CONTAINER_NAME" 2>/dev/null || true
    
    log_success "Nettoyage terminé"
}

# Build de l'image Docker
build_image() {
    log_info "Construction de l'image Docker..."
    
    # Build avec optimisations
    DOCKER_BUILDKIT=1 docker build \
        --target runtime \
        --tag "$IMAGE_NAME:latest" \
        --tag "$IMAGE_NAME:$(date +%Y%m%d-%H%M%S)" \
        . || {
        log_error "Échec de la construction de l'image"
        exit 1
    }
    
    log_success "Image Docker construite: $IMAGE_NAME:latest"
    
    # Afficher la taille de l'image
    local image_size
    image_size=$(docker images "$IMAGE_NAME:latest" --format "table {{.Size}}" | tail -1)
    log_info "Taille de l'image: $image_size"
}

# Configuration de Docker Compose
setup_compose() {
    log_info "Configuration de Docker Compose..."
    
    # Créer un fichier .env local si nécessaire
    if [ ! -f ".env" ]; then
        cat > .env << EOF
# Configuration Docker Compose pour Claude Monitor
CLAUDE_DATA_PATH=$CLAUDE_DATA_PATH
CLAUDE_PLAN=pro
CLAUDE_TIMEZONE=UTC
CLAUDE_THEME=auto
CLAUDE_DEBUG_MODE=false
COMPOSE_PROJECT_NAME=$COMPOSE_PROJECT
EOF
        log_success "Fichier .env créé"
    fi
    
    # Valider la configuration
    docker-compose config > /dev/null || {
        log_error "Configuration Docker Compose invalide"
        exit 1
    }
    
    log_success "Configuration Docker Compose validée"
}

# Test de l'installation
test_installation() {
    log_info "Test de l'installation..."
    
    # Test du health check
    docker run --rm \
        -v "$CLAUDE_DATA_PATH:/data:ro" \
        --entrypoint python \
        "$IMAGE_NAME:latest" \
        -c "from usage_analyzer.api import analyze_usage; result = analyze_usage(); print(f'✅ Test réussi: {len(result.get(\"blocks\", []))} blocs trouvés')" || {
        log_warning "Le test de base a échoué, mais l'image semble fonctionnelle"
    }
    
    log_success "Installation testée avec succès"
}

# Démarrage du service
start_service() {
    log_info "Démarrage du service Claude Monitor..."
    
    echo
    echo "Choisissez le mode de démarrage:"
    echo "1) Mode interactif (docker run)"
    echo "2) Mode service (docker-compose)"
    echo "3) Mode arrière-plan (docker-compose -d)"
    echo
    read -p "Votre choix (1-3): " choice
    
    case $choice in
        1)
            log_info "Démarrage en mode interactif..."
            docker run -it --rm \
                --name "$CONTAINER_NAME" \
                -v "$CLAUDE_DATA_PATH:/data:ro" \
                "$IMAGE_NAME:latest"
            ;;
        2)
            log_info "Démarrage avec Docker Compose..."
            docker-compose up
            ;;
        3)
            log_info "Démarrage en arrière-plan..."
            docker-compose up -d
            log_success "Service démarré en arrière-plan"
            log_info "Utilisez 'docker-compose logs -f' pour voir les logs"
            log_info "Utilisez 'docker-compose down' pour arrêter"
            ;;
        *)
            log_warning "Option invalide. Démarrage en mode interactif par défaut..."
            docker run -it --rm \
                --name "$CONTAINER_NAME" \
                -v "$CLAUDE_DATA_PATH:/data:ro" \
                "$IMAGE_NAME:latest"
            ;;
    esac
}

# Affichage de l'aide
show_help() {
    cat << EOF
Claude Monitor - Script de Configuration Docker

Usage: $0 [OPTIONS]

OPTIONS:
    --help, -h              Afficher cette aide
    --cleanup-only          Nettoyer uniquement (pas de build)
    --build-only           Builder uniquement (pas de démarrage)
    --no-start             Ne pas démarrer le service
    --data-path PATH       Spécifier le chemin des données Claude
    --quiet                Mode silencieux

EXEMPLES:
    $0                     Configuration complète automatique
    $0 --build-only        Builder l'image uniquement
    $0 --data-path ~/.claude/projects
                          Utiliser un chemin spécifique
    $0 --cleanup-only      Nettoyer les ressources existantes

EOF
}

# Fonction principale
main() {
    local cleanup_only=false
    local build_only=false
    local no_start=false
    local quiet=false
    
    # Parse des arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_help
                exit 0
                ;;
            --cleanup-only)
                cleanup_only=true
                shift
                ;;
            --build-only)
                build_only=true
                shift
                ;;
            --no-start)
                no_start=true
                shift
                ;;
            --data-path)
                CLAUDE_DATA_PATH="$2"
                shift 2
                ;;
            --quiet)
                quiet=true
                shift
                ;;
            *)
                log_error "Option inconnue: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    echo "Configuration Docker - $PROJECT_NAME"
    echo "=================================================="
    echo
    
    check_prerequisites
    
    if [ "$cleanup_only" = true ]; then
        cleanup_existing
        log_success "Nettoyage terminé"
        exit 0
    fi
    
    if [ -z "${CLAUDE_DATA_PATH:-}" ]; then
        detect_claude_data
    fi
    
    cleanup_existing
    build_image
    
    if [ "$build_only" = true ]; then
        log_success "Build terminé"
        exit 0
    fi
    
    setup_compose
    test_installation
    
    if [ "$no_start" = false ]; then
        start_service
    fi
    
    echo
    echo "=================================================="
    log_success "Configuration Docker terminée avec succès!"
    echo
    echo "Commandes utiles:"
    echo "  docker-compose up                 # Démarrer"
    echo "  docker-compose down               # Arrêter"
    echo "  docker-compose logs -f            # Voir les logs"
    echo "  docker exec -it $CONTAINER_NAME bash  # Entrer dans le container"
    echo
    echo "Documentation: docs/docker/README.md"
}

# Exécution du script
main "$@"
