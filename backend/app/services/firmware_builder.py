import asyncio
import os
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Callable
import shutil
import logging


logger = logging.getLogger(__name__)


@dataclass
class FirmwareBuildResult:
    success: bool
    log: str
    binary_path: Optional[str] = None
    binary_filename: Optional[str] = None


class FirmwareBuilder:
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.compile_timeout = 600  # seconds
        self.builds_dir = self.workspace / "builds"
        self.builds_dir.mkdir(parents=True, exist_ok=True)

    async def compile_yaml(self, yaml_content: str) -> FirmwareBuildResult:
        """Compile the provided YAML and return the result."""
        temp_dir = Path(tempfile.mkdtemp(prefix="smartvenue-esphome-", dir=self.workspace))
        yaml_path = temp_dir / "firmware.yaml"
        yaml_path.write_text(yaml_content)

        binary_path: Optional[str] = None
        binary_filename: Optional[str] = None
        log_output = ""
        success = False

        env = os.environ.copy()
        env.setdefault("PYTHONUNBUFFERED", "1")
        env.setdefault("ESPHOME_VERSION_CACHE", str(self.workspace / "cache"))
        env.setdefault("PLATFORMIO_HOME_DIR", str(self.workspace / ".platformio"))
        env.setdefault("PLATFORMIO_CACHE_DIR", str(self.workspace / ".pio-cache"))

        process = await asyncio.create_subprocess_exec(
            "esphome",
            "compile",
            str(yaml_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )

        try:
            try:
                stdout, _ = await asyncio.wait_for(process.communicate(), timeout=self.compile_timeout)
                log_output = stdout.decode(errors="replace").replace("\r", "\n")
                success = process.returncode == 0

                if success:
                    build_dir = temp_dir / ".esphome" / "build"
                    if build_dir.exists():
                        binaries = list(build_dir.glob("**/*.bin"))
                        if binaries:
                            build_id = str(uuid.uuid4())
                            binary_filename = f"firmware_{build_id}.bin"
                            persistent_binary_path = self.builds_dir / binary_filename
                            shutil.copy2(binaries[0], persistent_binary_path)
                            binary_path = str(persistent_binary_path)
                        else:
                            logger.warning("ESPHome compile succeeded but produced no binary outputs")
                    else:
                        logger.warning("ESPHome compile succeeded but build directory was not created")
                else:
                    logger.error("ESPHome compile failed with return code %s", process.returncode)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                log_output = "Compilation timed out after 10 minutes."
                logger.error("ESPHome compile timed out after %s seconds", self.compile_timeout)
        finally:
            pass

        return FirmwareBuildResult(
            success=success,
            log=log_output,
            binary_path=binary_path,
            binary_filename=binary_filename
        )

    async def compile_yaml_streaming(
        self,
        yaml_content: str,
        output_callback: Callable[[str], None]
    ) -> FirmwareBuildResult:
        """Compile YAML with real-time output streaming."""
        temp_dir = Path(tempfile.mkdtemp(prefix="smartvenue-esphome-", dir=self.workspace))
        yaml_path = temp_dir / "firmware.yaml"
        yaml_path.write_text(yaml_content)

        binary_path: Optional[str] = None
        binary_filename: Optional[str] = None
        log_lines: list[str] = []
        success = False

        env = os.environ.copy()
        env.setdefault("PYTHONUNBUFFERED", "1")
        env.setdefault("ESPHOME_VERSION_CACHE", str(self.workspace / "cache"))
        env.setdefault("PLATFORMIO_HOME_DIR", str(self.workspace / ".platformio"))
        env.setdefault("PLATFORMIO_CACHE_DIR", str(self.workspace / ".pio-cache"))

        process = await asyncio.create_subprocess_exec(
            "esphome",
            "compile",
            str(yaml_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )

        async def read_output():
            buffer = ""
            while True:
                chunk = await process.stdout.read(128)
                if not chunk:
                    if buffer:
                        line_str = buffer.rstrip()
                        if line_str:
                            log_lines.append(line_str)
                            output_callback(line_str)
                        buffer = ""
                    break

                buffer += chunk.decode(errors="replace").replace("\r", "\n")

                while "\n" in buffer:
                    line_str, buffer = buffer.split("\n", 1)
                    line_str = line_str.rstrip()
                    if not line_str:
                        continue
                    log_lines.append(line_str)
                    output_callback(line_str)

        try:
            try:
                await asyncio.wait_for(
                    asyncio.gather(read_output(), process.wait()),
                    timeout=self.compile_timeout
                )
                success = process.returncode == 0

                if success:
                    build_dir = temp_dir / ".esphome" / "build"
                    if build_dir.exists():
                        binaries = list(build_dir.glob("**/*.bin"))
                        if binaries:
                            build_id = str(uuid.uuid4())
                            binary_filename = f"firmware_{build_id}.bin"
                            persistent_binary_path = self.builds_dir / binary_filename
                            shutil.copy2(binaries[0], persistent_binary_path)
                            binary_path = str(persistent_binary_path)
                            output_callback(f"SUCCESS: Binary saved as {binary_filename}")
                        else:
                            logger.warning("ESPHome compile succeeded but produced no binary outputs")
                    else:
                        logger.warning("ESPHome compile succeeded but build directory was not created")
                else:
                    logger.error("ESPHome compile failed with return code %s", process.returncode)
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                timeout_message = "ERROR: Compilation timed out after 10 minutes."
                log_lines.append(timeout_message)
                output_callback(timeout_message)
                logger.error("ESPHome compile timed out after %s seconds", self.compile_timeout)
        finally:
            pass

        return FirmwareBuildResult(
            success=success,
            log="\n".join(log_lines),
            binary_path=binary_path,
            binary_filename=binary_filename
        )


def get_firmware_builder() -> FirmwareBuilder:
    workspace = Path(tempfile.gettempdir()) / "smartvenue-esphome"
    workspace.mkdir(parents=True, exist_ok=True)
    return FirmwareBuilder(workspace)
