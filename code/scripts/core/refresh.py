import ctypes
import logging
import win32gui # type: ignore
import win32con # type: ignore

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32



# -----------------------------------------------------------------------------
# INTERNAL HELPERS
# -----------------------------------------------------------------------------

def _enum_windows():
    windows = []

    def callback(hwnd, _):
        windows.append(hwnd)
        return True

    try:
        win32gui.EnumWindows(callback, None)
    except Exception as e:
        logging.exception("EnumWindows failed")
        return []

    return windows


def _find_window_ex(parent, after, class_name, title=""):
    try:
        return win32gui.FindWindowEx(parent, after, class_name, title)
    except Exception:
        return 0


def _get_workerw_handle():
    """
    Find the WorkerW window that lives behind desktop icons.
    """
    logging.debug("Searching for WorkerW window")

    for hwnd in _enum_windows():
        try:
            shell_view = _find_window_ex(hwnd, 0, "SHELLDLL_DefView")
            if shell_view:
                workerw = _find_window_ex(0, hwnd, "WorkerW")
                if workerw:
                    logging.info("WorkerW found: 0x%X", workerw)
                    return workerw
        except Exception:
            continue

    # Fallback: Progman
    try:
        progman = win32gui.FindWindow("Progman", None)
        if progman:
            workerw = _find_window_ex(progman, 0, "WorkerW")
            if workerw:
                logging.info("WorkerW found via Progman fallback: 0x%X", workerw)
                return workerw
    except Exception:
        logging.exception("Progman fallback failed")

    logging.error("WorkerW window not found")
    return None


def _remove_window_borders(hwnd):
    try:
        style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
        exstyle = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)

        style &= ~win32con.WS_CAPTION
        style &= ~win32con.WS_THICKFRAME

        exstyle &= ~win32con.WS_EX_APPWINDOW
        exstyle |= win32con.WS_EX_TOOLWINDOW

        win32gui.SetWindowLong(hwnd, win32con.GWL_STYLE, style)
        win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, exstyle)

        win32gui.SetWindowPos(
            hwnd, 0, 0, 0, 0, 0,
            win32con.SWP_NOMOVE
            | win32con.SWP_NOSIZE
            | win32con.SWP_NOZORDER
            | win32con.SWP_FRAMECHANGED
        )

        logging.debug("Window styles updated for hwnd=0x%X", hwnd)

    except Exception:
        logging.exception("Failed to remove window borders for hwnd=0x%X", hwnd)
        raise


def _localize_to_workerw(hwnd, workerw):
    try:
        left, top, right, bottom = win32gui.GetWindowRect(workerw)

        win32gui.SetWindowPos(
            hwnd,
            0,
            left,
            top,
            right - left,
            bottom - top,
            win32con.SWP_NOZORDER
        )

        logging.debug(
            "Window positioned to WorkerW area (%d,%d %dx%d)",
            left, top, right - left, bottom - top
        )

    except Exception:
        logging.exception("Failed to resize/move hwnd=0x%X to WorkerW", hwnd)
        raise


def _shell_refresh():
    try:
        shell32.SHChangeNotify(
            0x08000000,  # SHCNE_ASSOCCHANGED
            0,
            None,
            None
        )
        logging.debug("Shell refresh triggered")
    except Exception:
        logging.exception("Shell refresh failed")


# -----------------------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------------------

def attach_window_to_desktop(hwnd) -> bool:
    """
    Attach a window behind desktop icons using WorkerW.

    Returns:
        True  -> success
        False -> failure
    """

    logging.info("Attaching hwnd=0x%X to desktop", hwnd)

    if not hwnd:
        logging.error("Invalid hwnd: 0")
        return False

    if not win32gui.IsWindow(hwnd):
        logging.error("Invalid or inaccessible window handle: 0x%X", hwnd)
        return False

    workerw = _get_workerw_handle()
    if not workerw:
        logging.error("Cannot attach window — WorkerW not found")
        return False

    try:
        user32.SetParent(hwnd, workerw)
        logging.debug("SetParent(hwnd=0x%X, workerw=0x%X)", hwnd, workerw)
    except Exception:
        logging.exception("SetParent failed for hwnd=0x%X", hwnd)
        return False

    try:
        _remove_window_borders(hwnd)
        _localize_to_workerw(hwnd, workerw)
        # _shell_refresh()
    except Exception:
        logging.error("Failed during post-parent configuration for hwnd=0x%X", hwnd)
        return False

    logging.info("Window 0x%X successfully attached to desktop", hwnd)
    return True

# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------
import sys
def main():
    if len(sys.argv) < 2:
        print("Usage: refresh.py <HWND>")
        sys.exit(1)

    try:
        hwnd = int(sys.argv[1], 16)
    except ValueError:
        print("Invalid window handle format")
        sys.exit(1)

    if not win32gui.IsWindow(hwnd):
        print("Invalid or inaccessible window handle")
        sys.exit(1)

    workerw = _get_workerw_handle()
    if not workerw:
        print("WorkerW not found")
        sys.exit(1)

    # Set parent
    user32.SetParent(hwnd, workerw)

    # Remove borders
    _remove_window_borders(hwnd)

    # Resize to desktop
    _localize_to_workerw(hwnd, workerw)

    # Refresh shell
    _shell_refresh()

    print(f"Window 0x{hwnd:08X} attached to WorkerW successfully")


if __name__ == "__main__":
    main()
    # windows = _enum_windows()
    # print(f"Enumerated {len(windows)} windows:")
    # for hwnd in windows:
    #     title = win32gui.GetWindowText(hwnd)
    #     print(f"  0x{hwnd:08X}: {title}")