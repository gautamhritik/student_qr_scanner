# Student QR Scanner

This project creates 10 random student QR codes and provides a camera scanner that
tries multiple lighting-aware image enhancement passes before decoding.

It also includes a Phase-1 mining identification prototype that reuses the same
QR scanner foundation for vehicle/equipment gate events, camera/checkpoint
metadata, rugged-condition testing, and future ANPR cross-validation.

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

Useful roster commands:

```powershell
python manage_students.py list
python manage_students.py add --name "New Student" --class-name 8A --roll-no 30 --age 13 --class-teacher "Mrs. Kavita Sharma"
python manage_students.py remove --class-name 8A --roll-no 30
python generate_qrs.py
```

`generate_qrs.py` reads `data/students.json`, refreshes `data/students.csv`, and
regenerates both `qrs/` and `qrs_large_print/`.

## Mining fleet QR prototype

The mining prototype uses `data/fleet.json` as a vehicle/equipment registry. Each
record includes vehicle/equipment ID, plate number, type, owner/operator, site,
assigned route/checkpoint, and status.

Useful fleet commands:

```powershell
python manage_fleet.py list
python manage_fleet.py add --vehicle-id TRUCK-100 --plate-number MH12AB1000 --vehicle-type haul_truck --owner-operator "Pit Ops" --site north-pit --assigned-route gate-to-crusher --checkpoint-id gate-1
python manage_fleet.py remove --vehicle-id TRUCK-100
python generate_vehicle_qrs.py
```

`generate_vehicle_qrs.py` writes standard QR images to `vehicle_qrs/`,
large-print QR images to `vehicle_qrs_large_print/`, and a spreadsheet-friendly
copy of the registry to `data/fleet.csv`.

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
python scan_camera.py --no-preview
```

Press `q` to close the scanner window. If preview is disabled or unavailable,
press `Ctrl+C` to stop scanning.

Mining checkpoint mode stores richer vehicle/equipment events:

```powershell
python scan_camera.py --mining-mode --camera 0 --checkpoint-id gate-1 --camera-id cam-1 --vote-window 5 --min-votes 3
python scan_camera.py --mining-mode --camera 0 --checkpoint-id gate-1 --camera-id cam-1 --no-preview
```

Optional ANPR comparison can be simulated until the actual ANPR layer is added:

```powershell
python scan_camera.py --mining-mode --checkpoint-id gate-1 --camera-id cam-1 --anpr-plate-number MH12MN4101
```

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
- Use `--no-preview` if OpenCV cannot open a camera preview window.
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

In mining mode, events are stored in `mining_scan_database/` by default. Each
event includes timestamp, date, time, camera ID, checkpoint ID, detection method,
vehicle/equipment fields, payload validation result, readiness note, and ANPR
match placeholder status. Duplicate suppression is scoped by QR payload and
checkpoint.

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

Mining event reports:

```powershell
python export_mining_scans.py
python export_mining_scans.py --checkpoint-id gate-1
python export_mining_scans.py --vehicle-id TRUCK-001 --date-from 2026-07-01 --date-to 2026-07-31
```

The mining export creates:

- `exports/mining_scan_events.csv`
- `exports/mining_scan_summary.json`
- `exports/mining_scan_report.html`

## Rugged-condition benchmark

Use the benchmark tool to test QR decoding under synthetic mining-style
conditions: dust, blur, glare, low light, crop, rotation, and distance scaling.

```powershell
python generate_vehicle_qrs.py
python benchmark_qr_conditions.py --input-dir vehicle_qrs --output-dir exports\qr_condition_benchmark
```

The benchmark creates CSV, JSON, HTML, and generated condition images under the
selected output folder.

## ANPR direction

ANPR is prepared as a parallel verification layer, not the primary identifier
yet. The registry already stores `plate_number`, mining scan events include
`anpr_plate_number` and `anpr_match_status`, and `--anpr-plate-number` can be
used to simulate QR-vs-plate matching during demos. The next step is to add an
ANPR detector and compare the detected plate against the QR payload.

## Export attendance reports

Compare the student roster with scan history to mark students present or absent:

```powershell
python attendance_report.py
```

Useful options:

```powershell
python attendance_report.py --date-from 2026-07-02 --date-to 2026-07-02
python attendance_report.py --class-name 8A
```

The attendance export creates:

- `exports/attendance.csv`
- `exports/attendance_summary.json`
- `exports/attendance_report.html`

## How the detection handles lighting

The scanner uses OpenCV's QR detector, then retries decoding on many enhanced
frames: center crops, grayscale, contrast normalization, gamma correction,
thresholding, sharpening, and upscaled versions of the camera frame. It is a
practical computer-vision pipeline for reliable QR decoding under changing
lighting and longer scanning distances.
