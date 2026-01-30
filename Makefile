SHELL = /bin/bash

###############################
# Docker Build (no .env dependency)
###############################

IMAGE_NAME = $(or $(INGRESS_DOCKER_IMAGE),keys_dse_ingress:latest)

.PHONY: docker-build
docker-build:
	@echo "Extracting ingress artifacts..."
	rm -rf build-context
	mkdir -p build-context
	tar -xzf build/ingress_artifacts.tar.gz -C build-context
	if [ -d build-context/ingress_artifacts ]; then \
		mv build-context/ingress_artifacts/* build-context/; \
		rmdir build-context/ingress_artifacts; \
	fi
	@echo "Building ingress Docker image..."
	cd build-context && docker build -t $(IMAGE_NAME) .

.PHONY: test-integration
test-integration:
	@echo "Checking if ingress Docker image exists..."
	@if docker image inspect $(IMAGE_NAME) >/dev/null 2>&1; then \
		echo "Image $(IMAGE_NAME) already exists, proceeding with test"; \
	else \
		echo "Image $(IMAGE_NAME) not found, building..."; \
		$(MAKE) docker-build; \
	fi
	@echo "Starting ingress container for testing..."
	@docker rm -f keys-dse-ingress >/dev/null 2>&1 || true
	@docker run -d --name keys-dse-ingress -p 8080:443 $(IMAGE_NAME) --app_port 443 --routes "default/localhost:8080"
	@echo "Waiting for container to fully start..."
	@sleep 3
	@echo "Running integration tests..."
	@python3 build/test_integration.py --ingress-host localhost --ingress-port 8080
	@echo "Stopping test container..."
	@docker rm -f keys-dse-ingress >/dev/null 2>&1 || true
	@echo "Integration test complete."
