# 1) Buildx setup
docker buildx create --use || true
docker buildx inspect --bootstrap

# 2) Vars
export TAG=20250812-latest REG=ghcr.io ORG=haymayndzultra

# 3) Login once (needs GHCR_TOKEN + GHCR_USER or fixed username)
echo "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USER" --password-stdin
# or: echo "$GHCR_TOKEN" | docker login ghcr.io -u haymayndzultra --password-stdin

# 4) BASE (sequential)
docker buildx build -f docker/base-images/base-python/Dockerfile     -t $REG/$ORG/base-python:$TAG     --push .
docker buildx build -f docker/base-images/base-utils/Dockerfile      -t $REG/$ORG/base-utils:$TAG      --push .
docker buildx build -f docker/base-images/base-cpu-pydeps/Dockerfile -t $REG/$ORG/base-cpu-pydeps:$TAG --push .
docker buildx build -f docker/base-images/base-gpu-cu121/Dockerfile  -t $REG/$ORG/base-gpu-cu121:$TAG  --push .

# 5) FAMILY (parallel for independents: web, vision, torch)
export TAG REG ORG
printf '%s\n' \
  "docker/base-images/family-web/Dockerfile        family-web" \
  "docker/base-images/family-vision-cu121/Dockerfile family-vision-cu121" \
  "docker/base-images/family-torch-cu121/Dockerfile  family-torch-cu121" \
| xargs -L1 -P3 bash -lc 'read -r df name <<<"$0"; docker buildx build -f "$df" -t "$REG/$ORG/$name:$TAG" --push .'

# 6) Dependent last (llm depends on torch)
docker buildx build -f docker/base-images/family-llm-cu121/Dockerfile -t $REG/$ORG/family-llm-cu121:$TAG --push .
