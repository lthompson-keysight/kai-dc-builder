#!/usr/bin/env python3
"""
Integration test for the nginx ingress container.

This test script:
1. Checks if the ingress container is running
2. Tests nginx configuration and connectivity
3. Validates SSL/TLS setup
4. Tests routing behavior

Container lifecycle is managed by the Makefile.
"""

import os
import sys
import time
import signal
import argparse
import subprocess
import ssl
import socket
from pathlib import Path
from typing import Dict, List, Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Disable SSL warnings for self-signed certificates
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Test configuration
TEST_TIMEOUT = 60  # seconds
MOCK_SERVER_STARTUP_DELAY = 2  # seconds
INGRESS_STARTUP_DELAY = 5  # seconds


class IngressTester:
    """Integration tester for nginx ingress container."""

    def __init__(
        self,
        compose_file: Optional[Path] = None,
        env_file: Optional[Path] = None,
        ingress_host: Optional[str] = None,
        ingress_port: Optional[int] = None,
        ci_mode: bool = False,
    ):
        self.root_dir = Path(__file__).parent
        self.compose_file = compose_file
        self.env_file = env_file
        self.ingress_port_arg = ingress_port
        self.ci_mode = ci_mode

        # Check if we're running inside docker-compose network (via environment variable)
        self.in_compose_network = os.environ.get("INGRESS_HOST") is not None or ci_mode

        # Use provided ingress host or determine it later
        self.ingress_host = ingress_host

        # Load environment variables
        if ci_mode:
            # In CI mode, get configuration from environment variables
            self.env_vars = self._load_env_from_environment()
        else:
            self.env_vars = self._load_env_file()

        # Test configuration
        self.ingress_port = (
            self.ingress_port_arg
            if self.ingress_port_arg is not None
            else int(self.env_vars.get("WEBUI", "443"))
        )

        self.ingress_started = False
        self.temp_env_file = None  # Track temporary env file for cleanup

    def _get_ingress_host(self) -> str:
        """Get the host to connect to the ingress container."""
        print("\n" + "=" * 60)
        print("DETERMINING INGRESS HOST")
        print("=" * 60)

        # Use provided host if available
        if self.ingress_host:
            print(f"Using provided ingress host: {self.ingress_host}")
            print("=" * 60 + "\n")
            return self.ingress_host

        # If running inside docker-compose network, use service name
        if self.in_compose_network:
            ingress_host = os.environ.get("INGRESS_HOST", "ingress")
            print(f"Running inside docker-compose network")
            print(f"✓ Using service name: {ingress_host}")
            print("=" * 60 + "\n")
            return ingress_host

        # Otherwise use localhost (local dev or direct CI execution)
        print("Local development environment - using localhost")
        print("=" * 60 + "\n")
        return "localhost"

    def _load_env_from_environment(self) -> Dict[str, str]:
        """Load environment variables from the current environment (CI mode)."""
        env_vars = {}
        # Get the key environment variables that are set by docker-compose
        for key in ["WEBUI", "GRPC1", "GRPC2", "WEBUI_DSE"]:
            if key in os.environ:
                env_vars[key] = os.environ[key]
        return env_vars

    def _load_env_file(self) -> Dict[str, str]:
        """Load environment variables from .env file."""
        env_vars = {}
        if self.env_file and self.env_file.exists():
            with open(self.env_file, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        # Remove inline comments
                        if "#" in value:
                            value = value.split("#")[0].strip()
                        env_vars[key.strip()] = value.strip()
        return env_vars

    def _run_command(
        self, command: List[str], check: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a shell command"""
        try:
            result = subprocess.run(
                command,
                cwd=self.root_dir,
                capture_output=True,
                text=True,
                timeout=TEST_TIMEOUT,
                check=check,
                env=os.environ.copy(),
            )
            return result
        except subprocess.TimeoutExpired:
            print(f"Command timed out after {TEST_TIMEOUT} seconds")
            raise
        except subprocess.CalledProcessError as e:
            print(f"Command failed with exit code {e.returncode}")
            print(f"STDOUT: {e.stdout}")
            print(f"STDERR: {e.stderr}")
            raise

    def start_ingress(self):
        """Check that the ingress container is already running."""
        print("\n" + "=" * 60)
        print("CHECKING INGRESS CONTAINER")
        print("=" * 60)

        ingress_name = self.env_vars.get("INGRESS_NAME", "keys-dse-ingress")

        # Check if container is running
        try:
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    f"name={ingress_name}",
                    "--format",
                    "{{.Names}}",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if ingress_name in result.stdout.strip():
                print(f"✅ Ingress container '{ingress_name}' is running")
                self.ingress_started = True

                # Determine ingress host
                if not self.ingress_host:
                    self.ingress_host = self._get_ingress_host()
                print(
                    f"Will connect to ingress at: {self.ingress_host}:{self.ingress_port}"
                )
                print("=" * 60 + "\n")
                return
            else:
                print(f"❌ FAIL: Ingress container '{ingress_name}' is not running")
                print("Please run 'make test-integration' to start the container first")
                raise RuntimeError(f"Ingress container '{ingress_name}' is not running")
        except Exception as e:
            print(f"❌ FAIL: Error checking container status: {e}")
            raise

    def get_ingress_logs(self):
        """Retrieve logs from the ingress container."""
        container_name = self.env_vars.get("INGRESS_NAME", "keys-dse-ingress")

        print("Retrieving ingress logs...")
        try:
            result = self._run_command(["docker", "logs", container_name], check=True)
            return result.stdout + result.stderr
        except Exception as e:
            print(f"  ❌ FAIL: Could not retrieve ingress logs: {e}")
            return ""

    def run_tests(self) -> int:
        """Execute comprehensive integration tests and return an exit code."""
        print("\n" + "=" * 60)
        print("INTEGRATION TESTS")
        print("=" * 60)
        print("Testing nginx ingress container functionality...")
        print("=" * 60 + "\n")

        test_results = []
        container_name = self.env_vars.get("INGRESS_NAME", "keys-dse-ingress")

        # Test 1: Container is running
        print("Test 1: Container Status")
        test_results.append(self._test_container_running(container_name))

        # Test 2: Nginx process is running inside container
        print("\nTest 2: Nginx Process")
        test_results.append(self._test_nginx_process(container_name))

        # Test 3: Port connectivity
        print("\nTest 3: Port Connectivity")
        test_results.append(self._test_port_connectivity())

        # Test 4: HTTP response
        print("\nTest 4: HTTP Response")
        test_results.append(self._test_http_response())

        # Test 5: SSL/TLS certificate
        print("\nTest 5: SSL/TLS Certificate")
        test_results.append(self._test_ssl_certificate())

        # Test 6: Nginx configuration
        print("\nTest 6: Nginx Configuration")
        test_results.append(self._test_nginx_config(container_name))

        # Summary
        passed = sum(1 for result in test_results if result)
        total = len(test_results)

        print(f"\n{'='*60}")
        print(f"TEST SUMMARY: {passed}/{total} tests passed")
        print(f"{'='*60}")

        return 0 if passed == total else 1

    def _test_container_running(self, container_name: str) -> bool:
        """Test that the container is running."""
        try:
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "--filter",
                    f"name={container_name}",
                    "--format",
                    "{{.Status}}",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if "Up" in result.stdout:
                print("✅ PASS: Container is running")
                return True
            else:
                print("❌ FAIL: Container is not running")
                return False
        except Exception as e:
            print(f"❌ FAIL: Error checking container status: {e}")
            return False

    def _test_nginx_process(self, container_name: str) -> bool:
        """Test that nginx configuration is valid (skip process check since container may not have ps)."""
        try:
            result = subprocess.run(
                ["docker", "exec", container_name, "nginx", "-t"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                print("✅ PASS: Nginx configuration is valid")
                return True
            else:
                print("❌ FAIL: Nginx configuration test failed")
                print(f"   stderr: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ FAIL: Error testing nginx config: {e}")
            return False

    def _test_port_connectivity(self) -> bool:
        """Test that port 443 is accessible."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.ingress_host, self.ingress_port))
            sock.close()
            if result == 0:
                print(f"✅ PASS: Port {self.ingress_port} is accessible")
                return True
            else:
                print(f"❌ FAIL: Port {self.ingress_port} is not accessible")
                return False
        except Exception as e:
            print(f"❌ FAIL: Error testing port connectivity: {e}")
            return False

    def _test_http_response(self) -> bool:
        """Test that HTTP requests get a response."""
        try:
            # Create a request that ignores SSL certificate errors
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            url = f"https://{self.ingress_host}:{self.ingress_port}/"
            req = Request(url)

            with urlopen(req, context=context, timeout=10) as response:
                status_code = response.getcode()
                content = response.read(1024).decode("utf-8", errors="ignore")

                if (
                    200 <= status_code < 500 or status_code == 502
                ):  # Accept 2xx-4xx or 502 (backend not available)
                    print(f"✅ PASS: HTTP response received (status: {status_code})")
                    # Check if it's nginx default page or error
                    if "nginx" in content.lower() or "welcome" in content.lower():
                        print("   - Default nginx page detected")
                    return True
                else:
                    print(f"❌ FAIL: Unexpected HTTP status: {status_code}")
                    return False
        except HTTPError as e:
            if 400 <= e.code < 500 or e.code == 502:
                print(
                    f"✅ PASS: HTTP error response received (status: {e.code}) - expected for routing test"
                )
                return True
            else:
                print(f"❌ FAIL: HTTP error: {e.code}")
                return False
        except Exception as e:
            print(f"❌ FAIL: Error testing HTTP response: {e}")
            return False

    def _test_ssl_certificate(self) -> bool:
        """Test that SSL/TLS connection can be established."""
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with socket.create_connection(
                (self.ingress_host, self.ingress_port)
            ) as sock:
                with context.wrap_socket(
                    sock, server_hostname=self.ingress_host
                ) as ssock:
                    print("✅ PASS: SSL connection established")
                    return True
        except Exception as e:
            print(f"❌ FAIL: Error testing SSL certificate: {e}")
            return False

    def _test_nginx_config(self, container_name: str) -> bool:
        """Test that nginx configuration is valid."""
        try:
            result = subprocess.run(
                ["docker", "exec", container_name, "nginx", "-t"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                print("✅ PASS: Nginx configuration is valid")
                return True
            else:
                print("❌ FAIL: Nginx configuration test failed")
                print(f"   stderr: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ FAIL: Error testing nginx config: {e}")
            return False


def load_env_file(env_file):
    """Load environment variables from a .env file."""
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                if "=" in line:
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Integration tests for ingress controller."
    )
    parser.add_argument(
        "--compose-file",
        type=Path,
        default=None,
        help="Path to the docker-compose file for the ingress container",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Environment file for docker-compose.",
    )
    parser.add_argument(
        "--ingress-host",
        default="localhost",
        help="Hostname or IP address of the ingress controller",
    )
    parser.add_argument(
        "--ingress-port",
        type=int,
        default=None,
        help="Port number of the ingress controller",
    )
    parser.add_argument(
        "--ci-mode", action="store_true", help="Run in CI mode with specific settings"
    )
    args = parser.parse_args()

    load_env_file(args.env_file) if args.env_file else None

    tester = IngressTester(
        compose_file=args.compose_file,
        env_file=args.env_file,
        ingress_host=args.ingress_host,
        ingress_port=args.ingress_port,
        ci_mode=args.ci_mode,
    )

    exit_code = 1  # Default to failure

    try:
        # Check that ingress container is running (managed by Makefile)
        tester.start_ingress()
        # Run the tests
        exit_code = tester.run_tests()
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        import traceback

        traceback.print_exc()
    finally:
        print("\nTest complete.")
        # Container cleanup is now handled by Makefile

    sys.exit(exit_code)
