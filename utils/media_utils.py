from ctypes import cast, POINTER
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
import pyautogui


def sound_plus():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))

    current = volume.GetMasterVolumeLevelScalar()

    new_volume = min(current + 0.1, 1.0)

    volume.SetMasterVolumeLevelScalar(new_volume, None)


def sound_minus():
    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))

    current = volume.GetMasterVolumeLevelScalar()

    new_volume = max(current - 0.1, 0.0)

    volume.SetMasterVolumeLevelScalar(new_volume, None)


def play_pause():
    pyautogui.press('playpause')


def next_media():
    pyautogui.press("nexttrack")


def back_media():
    pyautogui.press("prevtrack")


def up():
    pyautogui.press("up")


def down():
    pyautogui.press("down")