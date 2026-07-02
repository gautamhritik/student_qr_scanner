# Student QR Scanner

This project creates 10 random student QR codes and provides a camera scanner that
tries multiple lighting-aware image enhancement passes before decoding.

Maintainer: Hritik Gautam <gautamhritik@gmail.com>

## Setup

```powershell
cd C:\Users\gauta\Projects\student_qr_scanner
python -m pip install -r requirements.txt
```

## Tests

```powershell
python -m pytest
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
python scan_camera.py --camera 0 --backend dshow
python scan_camera.py --camera "http://PHONE_IP:8080/video"
python scan_camera.py --save-scans
python scan_camera.py --scan-cooldown 5
python scan_camera.py --width 3840 --height 2160 --digital-zoom 2
python scan_camera.py --database-dir C:\path\to\scan_database
python scan_camera.py --width 3840 --height 2160 --preview-scale 0.5
python scan_camera.py --max-scans 10
```

Press `q` to close the scanner window.

## Long-distance scanning

For 10m scanning, software is only one part of the result. The camera must be able
to see enough QR pixels clearly. For best results:

- Use `qrs_large_print/` and print the QR as large as practical.
- Prefer a mobile camera or external webcam with autofocus over a low-resolution
  laptop webcam.
- Try `--backend dshow` or `--backend msmf` on Windows if the camera opens slowly
  or does not open.
- Start with `--width 1920 --height 1080`; try `--width 3840 --height 2160` if
  the camera supports it.
- Use `--preview-scale 0.5` if a high-resolution preview window is too large for
  the screen.
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
`--scan-cooldown`. Store scan records somewhere else with `--database-dir`. Stop
after a fixed number of accepted scans with `--max-scans`.

## Export scan reports

Convert the JSON scan history into spreadsheet-friendly CSV, summary JSON, and
an HTML report:

```powershell
python export_scans.py
```

Useful options:

```powershell
python export_scans.py --database-dir scan_database --output-dir exports
python export_scans.py --date-from 2026-07-01 --date-to 2026-07-31
python export_scans.py --student-name "Aarav" --class-name 8A
```

The export creates:

- `exports/scan_history.csv`
- `exports/scan_summary.json`
- `exports/scan_report.html`

## How the detection handles lighting

The scanner uses OpenCV's QR detector, then retries decoding on many enhanced
frames: center crops, grayscale, contrast normalization, gamma correction,
thresholding, sharpening, and upscaled versions of the camera frame. It is a
practical computer-vision pipeline for reliable QR decoding under changing
lighting and longer scanning distances.
