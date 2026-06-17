# Student QR Scanner

This project creates 10 random student QR codes and provides a camera scanner that
tries multiple lighting-aware image enhancement passes before decoding.

## Setup

```powershell
cd C:\Users\gauta\Projects\student_qr_scanner
python -m pip install -r requirements.txt
```

## Generate QR codes

The QR codes are already generated in `qrs/`, and the matching data is in
`data/students.csv` and `data/students.json`.

To regenerate them:

```powershell
python generate_qrs.py
```

## Scan with laptop or mobile camera

Use camera `0` for the default laptop webcam. If your phone is connected as an
IP/webcam device, use that camera index or URL.

```powershell
python scan_camera.py --camera 0
```

Useful options:

```powershell
python scan_camera.py --camera 1
python scan_camera.py --camera "http://PHONE_IP:8080/video"
python scan_camera.py --save-scans
python scan_camera.py --scan-cooldown 5
```

Press `q` to close the scanner window.

## Scan database

Every accepted QR scan is saved in `scan_database/` while the same information is
also printed in the terminal.

- `scan_database/scan_history.json` keeps the complete scan history.
- `scan_database/records/` stores one separate JSON file for each scan.
- Each record includes scan date, scan time, detection method, and the QR student
  information.

The scanner uses a 3-second cooldown for the same QR by default so one QR held in
front of the camera does not create many duplicate records. Change it with
`--scan-cooldown`.

## How the detection handles lighting

The scanner uses OpenCV's QR detector, then retries decoding on enhanced frames:
contrast normalization, gamma correction, adaptive thresholding, sharpening, and
upscaled versions of the camera frame. This is not a trained neural network; it is
a practical AI-style computer-vision pipeline for reliable QR decoding under
changing lighting.
