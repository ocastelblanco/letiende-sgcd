#!/bin/bash
COMPARTMENT_ID="ocid1.tenancy.oc1..aaaaaaaaq5rc3ylw6jiqywzgp57cn2tcsfjjlyldh6c5xin6aosfx7y7ljnq"
SUBNET_ID="ocid1.subnet.oc1.iad.aaaaaaaao3dddnk3a4lyjwt56zdrcbudwdlywdiosgl54a2kwwpfn7unzcdq"
IMAGE_ID="ocid1.image.oc1.iad.aaaaaaaaccnswiekwi4w3pkmygjvfk24epduwj7uvq2smjmznu4kq6dcs27a"
SSH_KEY_FILE="/tmp/letiende_ssh_key.pub"
ADS=("gaAa:US-ASHBURN-AD-1" "gaAa:US-ASHBURN-AD-2" "gaAa:US-ASHBURN-AD-3")
INTERVAL=300
ATTEMPT=0

echo "🚀 Iniciando retry loop para VM.Standard.A1.Flex"
echo "   Rotando entre AD-1, AD-2 y AD-3 cada ${INTERVAL}s"
echo ""

while true; do
  ATTEMPT=$((ATTEMPT + 1))
  AD=${ADS[$(( (ATTEMPT - 1) % 3 ))]}
  TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

  echo "[${TIMESTAMP}] Intento #${ATTEMPT} — ${AD}"

  RESULT=$(oci compute instance launch \
    --availability-domain "${AD}" \
    --compartment-id "${COMPARTMENT_ID}" \
    --shape "VM.Standard.A1.Flex" \
    --shape-config '{"ocpus": 4, "memoryInGBs": 24}' \
    --image-id "${IMAGE_ID}" \
    --subnet-id "${SUBNET_ID}" \
    --assign-public-ip true \
    --display-name "letiende-n8n" \
    --hostname-label "letiende-n8n" \
    --ssh-authorized-keys-file "${SSH_KEY_FILE}" \
    2>&1)

  if echo "${RESULT}" | grep -q '"lifecycle-state"'; then
    echo "[${TIMESTAMP}] ✅ ¡INSTANCIA CREADA EN ${AD}!"
    PUBLIC_IP=$(echo "${RESULT}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('data',{}).get('public-ip','ver-consola'))" 2>/dev/null)
    echo "[${TIMESTAMP}] 🌐 IP Pública: ${PUBLIC_IP}"
    echo "[${TIMESTAMP}] SSH: ssh -i ~/.oci/letiende_api_key.pem ubuntu@${PUBLIC_IP}"
    CREDS="/Users/ocastelblanco/Documents/LeTiende/letiende.co/flujo-n8n/credentials.env"
    if [ -f "${CREDS}" ]; then
      sed -i '' "s|ORACLE_VM_IP=.*|ORACLE_VM_IP=${PUBLIC_IP}|" "${CREDS}"
      echo "[${TIMESTAMP}] ✅ ORACLE_VM_IP actualizado en credentials.env"
    fi
    exit 0
  else
    ERROR=$(echo "${RESULT}" | grep -i '"message"' | head -1 | sed 's/.*"message": *"//' | sed 's/".*//')
    echo "[${TIMESTAMP}] ⏳ ${AD}: ${ERROR}"
    echo "[${TIMESTAMP}] Próximo intento en ${INTERVAL}s..."
  fi

  sleep ${INTERVAL}
done
