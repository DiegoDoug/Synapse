#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# scripts/generate-self-signed-cert.sh — local/staging TLS fallback (Stage 8).
#
# Generates a self-signed certificate into nginx/certs/ so the reverse proxy can
# serve HTTPS without Let's Encrypt (local bring-up, air-gapped staging). In
# production, replace these with real Let's Encrypt certs (see DEPLOYMENT.md).
#
# Usage:
#   ./scripts/generate-self-signed-cert.sh [domain]   # default: localhost
# -----------------------------------------------------------------------------
set -euo pipefail

DOMAIN="${1:-localhost}"
CERT_DIR="${CERT_DIR:-nginx/certs}"
DAYS="${DAYS:-365}"

mkdir -p "$CERT_DIR"

if [[ -f "$CERT_DIR/fullchain.pem" && -f "$CERT_DIR/privkey.pem" ]]; then
  echo "[cert] Existing certs found in ${CERT_DIR}; leaving them in place."
  echo "[cert] Delete them first to regenerate."
  exit 0
fi

echo "[cert] Generating self-signed certificate for '${DOMAIN}' (${DAYS} days)..."
openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout "$CERT_DIR/privkey.pem" \
  -out "$CERT_DIR/fullchain.pem" \
  -days "$DAYS" \
  -subj "/CN=${DOMAIN}/O=Synapse/OU=PersonalOS" \
  -addext "subjectAltName=DNS:${DOMAIN},DNS:localhost,IP:127.0.0.1"

chmod 600 "$CERT_DIR/privkey.pem"
echo "[cert] Wrote ${CERT_DIR}/fullchain.pem and ${CERT_DIR}/privkey.pem"
echo "[cert] NOTE: browsers will warn on self-signed certs — expected for local use."
