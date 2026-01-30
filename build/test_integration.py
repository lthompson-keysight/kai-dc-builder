#!/usr/bin/env python3
"""
Dummy integration test for the nginx ingress container.

This test script:
1. Checks if the ingress container is running
2. Runs basic integration tests

This is a placeholder that will be expanded later with actual routing tests.
Container lifecycle is managed by the Makefile.
"""

import os
import sys
import time
import signal
import argparse
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

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
        ci_mode: bool = False,
    ):
        self.root_dir = Path(__file__).parent
        self.compose_file = compose_file
        self.env_file = env_file
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
        self.ingress_port = int(self.env_vars.get("WEBUI", "443"))

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
        """Execute dummy integration tests and return an exit code."""
        print("\n" + "=" * 60)
        print("DUMMY INTEGRATION TESTS")
        print("=" * 60)
        print("This is a placeholder test that will be expanded later.")
        print("For now, it just checks if the ingress container is running.")
        print("=" * 60 + "\n")

        # Dummy test: just check if ingress container was created
        try:
            result = subprocess.run(
                [
                    "docker",
                    "ps",
                    "-a",
                    "--filter",
                    f"name={self.env_vars.get('INGRESS_NAME', 'keys-dse-ingress')}",
                    "--format",
                    "table",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if "keys-dse-ingress" in result.stdout:
                print("✅ PASS: Ingress container was created")
                return 0
            else:
                print("❌ FAIL: Ingress container not found")
                return 1
        except Exception as e:
            print(f"❌ FAIL: Error checking container: {e}")
            return 1


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
        "--ci-mode", action="store_true", help="Run in CI mode with specific settings"
    )
    args = parser.parse_args()

    load_env_file(args.env_file) if args.env_file else None

    tester = IngressTester(
        compose_file=args.compose_file,
        env_file=args.env_file,
        ingress_host=args.ingress_host,
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
