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

Large-print versions are generated in `qrs_large_print/`. Use these for distance
testing, posters, project demos, or display on a large screen.

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
python scan_camera.py --width 3840 --height 2160 --digital-zoom 2
```

Press `q` to close the scanner window.

## Long-distance scanning

For 10m scanning, software is only one part of the result. The camera must be able
to see enough QR pixels clearly. For best results:

- Use `qrs_large_print/` and print the QR as large as practical.
- Prefer a mobile camera or external webcam with autofocus over a low-resolution
  laptop webcam.
- Start with `--width 1920 --height 1080`; try `--width 3840 --height 2160` if
  the camera supports it.
- Keep the QR centered and use `--digital-zoom 2` or `--digital-zoom 3` when the
  QR is far away.
- Avoid glare, motion blur, and tilted angles. The QR should be flat and focused.

## Scan database

Every accepted QR scan is saved in `scan_database/` while the same information is
also printed in the terminal.

- `scan_database/scan_history.json` keeps the complete scan history.
- `scan_database/records/` stores one separate JSON file for each scan.
- Each record includes scan date, scan time, detection method, and the QR student
  information.
- JSON files are written atomically so an interrupted write is less likely to
  corrupt the scan history.
- The terminal shows the total number of saved scans after each accepted scan.

The scanner uses a 3-second cooldown for the same QR by default so one QR held in
front of the camera does not create many duplicate records. Change it with
`--scan-cooldown`.

## How the detection handles lighting

The scanner uses OpenCV's QR detector, then retries decoding on many enhanced
frames: center crops, grayscale, contrast normalization, gamma correction,
denoising, thresholding, sharpening, multi-QR decoding, and upscaled versions of
the camera frame. This is not a trained neural network; it is a practical
AI-style computer-vision pipeline for reliable QR decoding under changing
lighting and longer scanning distances.
