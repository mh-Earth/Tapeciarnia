import subprocess
import logging
import platform
import os


# --- Constants for Windows-Specific Flags ---
# We use this to prevent the console window from showing up.
CREATE_NO_WINDOW = 0x08000000 


def run_blocking_silent_command(command_parts, cwd=None, timeout=None):
    """
    Executes a command on Windows silently, waits for it to complete, 
    and returns the result (blocking call).
    
    Args:
        command_parts (list): The command and its arguments as a list of strings.
        cwd (str, optional): The current working directory for the command.
        timeout (int, optional): The maximum time (in seconds) to wait for the command to finish.

    Returns:
        subprocess.CompletedProcess: An object containing the command result.
                                     Returns None if the platform is not Windows.
    """
    logging.debug(f"Starting blocking silent command: {command_parts}")
    logging.debug(f"Working directory: {cwd}, Timeout: {timeout}")
    
    if platform.system() != "Windows":
        logging.debug("Non-Windows platform, using standard subprocess.run")
        try:
            result = subprocess.run(command_parts, capture_output=True, text=True, cwd=cwd, timeout=timeout)
            logging.debug(f"Non-Windows command completed - returncode: {result.returncode}")
            return result
        except Exception as e:
            logging.error(f"Non-Windows command failed: {e}", exc_info=True)
            return None
    
    # --- Windows-Specific Execution (Blocking) ---
    logging.info(f"Executing Windows blocking command: {' '.join(command_parts)}")
    try:
        # Popen starts the process
        logging.debug("Creating subprocess with CREATE_NO_WINDOW flag")
        process = subprocess.Popen(
            command_parts,
            creationflags=CREATE_NO_WINDOW,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd,
            text=True
        )
        logging.debug(f"Process created with PID: {process.pid}")

        # CRITICAL: communicate() waits for the process to terminate.
        logging.debug(f"Waiting for process completion with timeout: {timeout}")
        stdout, stderr = process.communicate(timeout=timeout)
        
        logging.info(f"Blocking command completed - PID: {process.pid}, returncode: {process.returncode}")
        logging.debug(f"Command stdout length: {len(stdout)}, stderr length: {len(stderr)}")
        
        if process.returncode != 0:
            logging.warning(f"Command returned non-zero exit code: {process.returncode}")
            if stderr:
                logging.warning(f"Command stderr: {stderr.strip()}")
        
        return subprocess.CompletedProcess(
            args=command_parts,
            returncode=process.returncode,
            stdout=stdout,
            stderr=stderr
        )

    except FileNotFoundError as e:
        logging.error(f"Executable not found for command: {command_parts[0]}", exc_info=True)
        logging.error(f"Full command: {command_parts}")
        return None
    except subprocess.TimeoutExpired as e:
        logging.error(f"Command timed out after {timeout} seconds: {' '.join(command_parts)}")
        if 'process' in locals():
            logging.warning(f"Terminating timed out process: {process.pid}")
            process.kill()
            try:
                process.wait(timeout=5)
                logging.debug("Timed out process terminated successfully")
            except subprocess.TimeoutExpired:
                logging.error("Failed to terminate timed out process")
        return None
    except Exception as e:
        logging.error(f"Unexpected error executing blocking command: {e}", exc_info=True)
        logging.error(f"Command that failed: {' '.join(command_parts)}")
        return None


def run_and_forget_silent(command_parts, cwd=None):
    """
    *** This is the Python equivalent of non-blocking AutoIt 'Run'. ***
    Executes a command on Windows silently and immediately returns 
    without waiting for the command to finish. The process runs in the background.

    Args:
        command_parts (list): The command and its arguments as a list of strings.
        cwd (str, optional): The current working directory for the command.

    Returns:
        subprocess.Popen or None: The process object if successful, None otherwise.
    """
    logging.debug(f"Starting non-blocking silent command: {command_parts}")
    logging.debug(f"Working directory: {cwd}")
    
    if platform.system() != "Windows":
        logging.debug("Non-Windows platform, using standard subprocess.Popen")
        try:
            process = subprocess.Popen(command_parts, cwd=cwd)
            logging.info(f"Non-Windows background process started - PID: {process.pid}")
            return process
        except Exception as e:
            logging.error(f"Non-Windows background process failed: {e}", exc_info=True)
            return None

    # --- Windows-Specific Execution (Non-Blocking) ---
    logging.info(f"Starting Windows non-blocking command: {' '.join(command_parts)}")
    try:
        # CRITICAL: Popen is used without communicate/wait. The process runs independently.
        logging.debug("Creating non-blocking subprocess with CREATE_NO_WINDOW flag")
        process = subprocess.Popen(
            command_parts,
            creationflags=CREATE_NO_WINDOW,
            cwd=cwd
        )
        logging.debug(f"Background process started successfully - PID: {process.pid}")
        logging.debug(f"Process object created: {process}")
        return process
        
    except FileNotFoundError as e:
        logging.error(f"Executable not found for background command: {command_parts[0]}", exc_info=True)
        logging.error(f"Full background command: {command_parts}")
        return None
    except PermissionError as e:
        logging.error(f"Permission denied executing background command: {command_parts[0]}")
        logging.error(f"Full background command: {command_parts}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error starting background command: {e}", exc_info=True)
        logging.error(f"Command that failed: {' '.join(command_parts)}")
        return None


def terminate_process(process):
    """
    Safely terminate a process created by run_and_forget_silent
    
    Args:
        process: subprocess.Popen object to terminate
        
    Returns:
        bool: True if termination was successful, False otherwise
    """
    if process is None:
        logging.warning("Attempted to terminate None process")
        return False
        
    logging.info(f"Terminating process: {process.pid}")
    try:
        process.terminate()
        logging.debug(f"Terminate signal sent to process: {process.pid}")
        
        # Wait a bit for graceful termination
        try:
            process.wait(timeout=5)
            logging.info(f"Process terminated successfully: {process.pid}")
            return True
        except subprocess.TimeoutExpired:
            logging.warning(f"Process did not terminate gracefully, killing: {process.pid}")
            process.kill()
            process.wait()
            logging.info(f"Process killed: {process.pid}")
            return True
            
    except Exception as e:
        logging.error(f"Failed to terminate process {process.pid}: {e}", exc_info=True)
        return False


def check_process_running(process):
    """
    Check if a process is still running
    
    Args:
        process: subprocess.Popen object to check
        
    Returns:
        bool: True if process is running, False otherwise
    """
    if process is None:
        return False
        
    return_code = process.poll()
    is_running = return_code is None
    
    logging.debug(f"Process {process.pid} running: {is_running}, returncode: {return_code}")
    return is_running

