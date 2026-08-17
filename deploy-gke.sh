#!/bin/bash
set -euo pipefail

# ============================================================
# AutoRun GKE Deployment Script
# ============================================================
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - Docker installed and running
#   - kubectl configured
#
# Usage:
#   ./deploy-gke.sh [OPTIONS]
#
# Options:
#   --project <id>       GCP project ID (required)
#   --region <region>    GCP region (default: us-central1)
#   --cluster <name>     GKE cluster name (default: autorun-cluster)
#   --image <tag>        Docker image tag (default: ogc16/autorun:latest)
#   --domain <domain>    Domain for ingress (default: autorun.example.com)
#   --skip-cluster       Skip cluster creation
#   --skip-build         Skip Docker build
#   --dry-run            Print commands without executing
# ============================================================

# --- Defaults ---
PROJECT=""
REGION="us-central1"
ZONE="${REGION}-a"
CLUSTER="autorun-cluster"
IMAGE="ogc16/autorun:latest"
DOMAIN="autorun.example.com"
SKIP_CLUSTER=false
SKIP_BUILD=false
DRY_RUN=false
NAMESPACE="autorun"

# --- Parse args ---
while [[ $# -gt 0 ]]; do
  case $1 in
    --project)    PROJECT="$2"; shift 2 ;;
    --region)     REGION="$2"; ZONE="${REGION}-a"; shift 2 ;;
    --cluster)    CLUSTER="$2"; shift 2 ;;
    --image)      IMAGE="$2"; shift 2 ;;
    --domain)     DOMAIN="$2"; shift 2 ;;
    --skip-cluster) SKIP_CLUSTER=true; shift ;;
    --skip-build)   SKIP_BUILD=true; shift ;;
    --dry-run)      DRY_RUN=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -z "$PROJECT" ]]; then
  echo "ERROR: --project is required"
  echo "Usage: $0 --project <gcp-project-id> [--region <region>] [--cluster <name>]"
  exit 1
fi

run() {
  if [[ "$DRY_RUN" == true ]]; then
    echo "[DRY RUN] $*"
  else
    echo ">>> $*"
    "$@"
  fi
}

echo "============================================"
echo " AutoRun GKE Deployment"
echo "============================================"
echo " Project:  $PROJECT"
echo " Region:   $REGION"
echo " Cluster:  $CLUSTER"
echo " Image:    $IMAGE"
echo " Domain:   $DOMAIN"
echo "============================================"

# --- Step 1: Configure gcloud ---
echo ""
echo "[1/8] Configuring gcloud..."
run gcloud config set project "$PROJECT"
run gcloud config set compute/region "$REGION"
run gcloud config set compute/zone "$ZONE"

# --- Step 2: Enable required APIs ---
echo ""
echo "[2/8] Enabling required GCP APIs..."
run gcloud services enable \
  container.googleapis.com \
  compute.googleapis.com \
  sqladmin.googleapis.com \
  certificatemanager.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com

# --- Step 3: Create GKE cluster ---
if [[ "$SKIP_CLUSTER" == false ]]; then
  echo ""
  echo "[3/8] Creating GKE cluster..."
  run gcloud container clusters create "$CLUSTER" \
    --region "$REGION" \
    --num-nodes 2 \
    --machine-type e2-standard-2 \
    --enable-autoscaling --min-nodes 1 --max-nodes 5 \
    --enable-autorepair --enable-autoupgrade \
    --release-channel regular \
    --enable-ip-alias \
    --enable-private-nodes \
    --master-ipv4-cidr 172.16.0.0/28 \
    --workload-pool "${PROJECT}.svc.id.goog" \
    --logging=SYSTEM,WORKLOAD \
    --monitoring=SYSTEM

  echo ""
  echo "[3/8] Getting cluster credentials..."
  run gcloud container clusters get-credentials "$CLUSTER" --region "$REGION"
else
  echo ""
  echo "[3/8] Skipping cluster creation (--skip-cluster)"
  run gcloud container clusters get-credentials "$CLUSTER" --region "$REGION"
fi

# --- Step 4: Create static IP ---
echo ""
echo "[4/8] Reserving static IP address..."
run gcloud compute addresses create autorun-ip \
  --global \
  --project "$PROJECT" || echo "  (IP may already exist)"

IP_ADDRESS=$(gcloud compute addresses describe autorun-ip --global --format="value(address)" 2>/dev/null || echo "pending")
echo "  Static IP: $IP_ADDRESS"

# --- Step 5: Build and push Docker image ---
if [[ "$SKIP_BUILD" == false ]]; then
  echo ""
  echo "[5/8] Building Docker image..."
  run docker build -t "$IMAGE" .

  echo ""
  echo "[5/8] Pushing Docker image..."
  run docker push "$IMAGE"
else
  echo ""
  echo "[5/8] Skipping Docker build (--skip-build)"
fi

# --- Step 6: Update manifests ---
echo ""
echo "[6/8] Updating Kubernetes manifests..."

# Update domain in ManagedCertificate
sed -i "s/autorun.example.com/$DOMAIN/g" k8s/managed-cert.yml

# --- Step 7: Apply Kubernetes manifests ---
echo ""
echo "[7/8] Applying Kubernetes manifests..."
run kubectl apply -f k8s/namespace.yml
run kubectl apply -f k8s/serviceaccount.yml
run kubectl apply -f k8s/configmap.yml
run kubectl apply -f k8s/secret.yml
run kubectl apply -f k8s/pvc.yml
run kubectl apply -f k8s/deployment.yml
run kubectl apply -f k8s/service.yml
run kubectl apply -f k8s/hpa.yml
run kubectl apply -f k8s/pdb.yml
run kubectl apply -f k8s/managed-cert.yml
run kubectl apply -f k8s/ingress.yml

# --- Step 8: Verify deployment ---
echo ""
echo "[8/8] Verifying deployment..."
run kubectl -n "$NAMESPACE" rollout status deployment/autorun --timeout=300s

echo ""
echo "============================================"
echo " Deployment Complete!"
echo "============================================"
echo ""
echo " Cluster:   $CLUSTER"
echo " Namespace: $NAMESPACE"
echo " Static IP: $IP_ADDRESS"
echo " Domain:    $DOMAIN"
echo ""
echo " Useful commands:"
echo "   kubectl -n $NAMESPACE get pods"
echo "   kubectl -n $NAMESPACE get svc"
echo "   kubectl -n $NAMESPACE get ingress"
echo "   kubectl -n $NAMESPACE logs -f deployment/autorun"
echo "   kubectl -n $NAMESPACE describe hpa/autorun"
echo ""
echo " NOTE: Update DNS for $DOMAIN -> $IP_ADDRESS"
echo "       Certificate will provision automatically via GKE Managed Cert"
echo "============================================"
