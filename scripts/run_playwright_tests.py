#!/usr/bin/env python3
"""
Simple test runner for Playwright integration tests.

This script helps run Playwright tests with proper setup and teardown.
"""

import subprocess
import sys
import time


class PlaywrightTestRunner:
    """Test runner for Playwright integration tests."""

    def __init__(self, server_port: int = 8000, headed: bool = False) -> None:
        self.server_port = server_port
        self.headed = headed
        self.server_process: subprocess.Popen[bytes] | None = None

    def start_server(self) -> bool:
        """Start the FastAPI development server."""
        print(f"🚀 Starting development server on port {self.server_port}...")

        try:
            # Use uvicorn to start the server
            self.server_process = subprocess.Popen(
                [
                    "uv",
                    "run",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    str(self.server_port),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait for server to start
            print("⏳ Waiting for server to be ready...")
            for _ in range(30):  # Wait up to 30 seconds
                time.sleep(1)
                try:
                    import requests

                    response = requests.get(f"http://localhost:{self.server_port}/health", timeout=2)
                    if response.status_code == 200:
                        print("✅ Server is ready!")
                        return True
                except (requests.RequestException, ImportError):
                    continue

            print("❌ Server failed to start within timeout")
            self.stop_server()
            return False

        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False

    def stop_server(self) -> None:
        """Stop the development server."""
        if self.server_process:
            print("🛑 Stopping development server...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
            self.server_process = None

    def run_tests(self) -> int:
        """Run the Playwright tests."""
        print("🎭 Running Playwright integration tests...")

        cmd = [
            "uv",
            "run",
            "pytest",
            "tests/test_integration_htmx_playwright.py",
            "-v",
            "--browser=chromium",
        ]

        if self.headed:
            cmd.append("--headed=true")
        else:
            cmd.append("--headed=false")

        try:
            result = subprocess.run(cmd, check=False)
            return result.returncode
        except Exception as e:
            print(f"❌ Failed to run tests: {e}")
            return 1

    def run(self) -> int:
        """Run the complete test workflow."""
        try:
            # Start server
            if not self.start_server():
                return 1

            # Run tests
            return_code = self.run_tests()

            if return_code == 0:
                print("✅ All Playwright tests passed!")
            else:
                print("❌ Some Playwright tests failed!")

            return return_code

        finally:
            # Always stop server
            self.stop_server()


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Run Playwright integration tests")
    parser.add_argument("--port", type=int, default=8000, help="Port for development server (default: 8000)")
    parser.add_argument("--headed", action="store_true", help="Run tests with visible browser (for debugging)")

    args = parser.parse_args()

    runner = PlaywrightTestRunner(server_port=args.port, headed=args.headed)
    return runner.run()


if __name__ == "__main__":
    sys.exit(main())
