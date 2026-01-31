#!/usr/bin/env python3
import os
import subprocess

from persona.config import env


def start_container(container_name: str, image_name: str, mnt_dir: str, skills_dir: str, env_file: str | None = None, no_mnt: bool = False) -> bool:
    """Start a Docker container with the specified parameters."""
    try:
        mnt_dir = os.path.abspath(os.path.expanduser(mnt_dir))
        skills_dir = os.path.abspath(os.path.expanduser(skills_dir))

        cmd = ["docker", "run", "-d", "--rm"]

        if env_file and os.path.isfile(env_file):
            cmd.extend(["--env-file", env_file])

        if not no_mnt and os.path.isdir(mnt_dir):
            cmd.extend(["-v", f"{mnt_dir}:/mnt"])
        if os.path.isdir(skills_dir):
            cmd.extend(["-v", f"{skills_dir}:/skills"])
        
        cmd.extend([
            "--name", container_name,
            image_name,
            "sleep", "infinity"
        ])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            if env.is_debug():
                print(f"Container {container_name} started successfully with ID: {result.stdout.strip()}")
            return True
        else:
            if env.is_debug():
                print(f"Failed to start container {container_name}: {result.stderr}")
            return False
    
    except subprocess.TimeoutExpired:
        if env.is_debug():
            print("Command timed out")
        return False
    except Exception as e:
        if env.is_debug():
            print(f"Error starting container: {str(e)}")
        return False


def stop_container(container_name: str) -> bool:
    """Stop a Docker container with the specified name."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-q", "-f", f"name={container_name}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and result.stdout.strip():
            stop_result = subprocess.run(
                ["docker", "stop", container_name],
                capture_output=True,
                text=True,
                timeout=20
            )
            
            if stop_result.returncode == 0:
                if env.is_debug():
                    print(f"Container {container_name} stopped successfully")
                return True
            else:
                if env.is_debug():
                    print(f"Failed to stop container {container_name}: {stop_result.stderr}")
                return False
        else:
            if env.is_debug():
                print(f"Container {container_name} not found or not running")
            return True
    
    except Exception as e:
        if env.is_debug():
            print(f"Error stopping container: {str(e)}")
        return False
