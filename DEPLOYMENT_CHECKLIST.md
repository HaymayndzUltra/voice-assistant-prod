# Deployment Checklist - Phase 4 Services

## Pre-Deployment Verification
- [ ] Confirm branch: `cursor/build-and-deploy-ai-system-services-0e14`
- [ ] Latest commit: `d5f87f99`
- [ ] Token ready: `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`

## Step 1: Build & Push (Branch Environment)
```bash
# 1.1 Get latest code
git pull origin cursor/build-and-deploy-ai-system-services-0e14

# 1.2 Set environment
export ORG=haymayndzultra
export GHCR_PAT=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

# 1.3 Run build script
bash BUILD_AND_PUSH_WITH_VERIFY.sh

# 1.4 Note the TAG output (format: YYYYMMDD-XXXXXXX)
export TAG=_____________  # Fill this in!
```

## Step 2: Verify Registry Sync
```bash
# 2.1 Check for digest mismatches
GH_USERNAME=$ORG GH_TOKEN=$GHCR_PAT python3 scripts/sync_inventory.py --dry-run

# 2.2 If zero mismatches, push missing
GH_USERNAME=$ORG GH_TOKEN=$GHCR_PAT python3 scripts/sync_inventory.py --push-missing

# 2.3 Record the DATE-SHA tag
echo "TAG used: $TAG"
```

## Step 3: Deploy on MainPC
```bash
# 3.1 SSH to MainPC
ssh haymayndz@mainpc

# 3.2 Set deployment tag
export ORG=haymayndzultra
export TAG=YYYYMMDD-XXXXXXX  # Use TAG from Step 1.4
export FORCE_IMAGE_TAG=$TAG

# 3.3 Reload supervisor
sudo systemctl reload supervisor

# 3.4 Wait 60 seconds for services to start
sleep 60
```

## Step 4: Health Verification
```bash
# 4.1 Check all health endpoints
echo "=== Health Check Results ==="
echo -n "MOCO (8212): "; curl -sf localhost:8212/health && echo " ✅" || echo " ❌"
echo -n "RTAP (6557): "; curl -sf localhost:6557/health && echo " ✅" || echo " ❌"
echo -n "APC  (6560): "; curl -sf localhost:6560/health && echo " ✅" || echo " ❌"
echo -n "UOC  (9110): "; curl -sf localhost:9110/health && echo " ✅" || echo " ❌"
echo -n "CEB  (8150): "; curl -sf localhost:8150/health && echo " ✅" || echo " ❌"
echo -n "SHS  (9008): "; curl -sf localhost:9008/health && echo " ✅" || echo " ❌"
```

## Step 5: Deploy on PC2 (if needed)
```bash
# 5.1 SSH to PC2
ssh haymayndz@pc2

# 5.2 Repeat steps 3.2-3.4
export ORG=haymayndzultra
export TAG=YYYYMMDD-XXXXXXX  # Same TAG
export FORCE_IMAGE_TAG=$TAG
sudo systemctl reload supervisor

# 5.3 Check PC2-specific services
echo -n "CEB (8150): "; curl -sf localhost:8150/health && echo " ✅" || echo " ❌"
```

## Step 6: Post-Deployment (Optional)
```bash
# 6.1 Registry cleanup (keep last 5 tags)
# List packages first
gh api /users/$ORG/packages?package_type=container

# Delete old versions (>30 days, untagged)
# gh api -X DELETE /users/$ORG/packages/container/<pkg>/versions/<id>
```

## Success Criteria
- [ ] All 6 health checks return `{"status":"ok"}`
- [ ] No errors in supervisor logs
- [ ] Services accessible on correct ports
- [ ] No digest drift in sync_inventory

## Rollback Plan
```bash
# If issues occur:
export FORCE_IMAGE_TAG=20250810-9c99cc9  # Previous stable tag
sudo systemctl reload supervisor
```

## Notes
- Current compliance: ~80% with plan.md
- Missing: --require-hashes, CI/CD automation
- All ports verified correct
- All services use appuser (10001:10001)
- Torch version: 2.2.2+cu121