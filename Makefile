SHELL = /bin/bash

###############################
# Docker Build (no .env dependency)
###############################

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
	cd build-context && docker build -t keys_dse_ingress:latest .

.PHONY: test-integration
test-integration:
	@echo "Checking if ingress Docker image exists..."
	@if docker image inspect keys_dse_ingress:latest >/dev/null 2>&1; then \
		echo "Image keys_dse_ingress:latest already exists, proceeding with test"; \
	else \
		echo "Image keys_dse_ingress:latest not found, building..."; \
		$(MAKE) docker-build; \
	fi
	@echo "Starting ingress container for testing..."
	@docker rm -f keys-dse-ingress >/dev/null 2>&1 || true
	@docker run -d --name keys-dse-ingress -p 443:443 keys_dse_ingress:latest --app_port 443 --routes "default/localhost:8080"
	@echo "Running integration tests..."
	@python3 build/test_integration.py --ingress-host localhost
	@echo "Stopping test container..."
	@docker rm -f keys-dse-ingress >/dev/null 2>&1 || true
	@echo "Integration test complete."
